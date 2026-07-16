"""DevCareer API — share job links with friends, with auto-fetched details."""

import os
import re
import sqlite3
from urllib.parse import urlparse

import bcrypt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator

load_dotenv()  # backend/.env — GROQ_API_KEY / TAVILY_API_KEY for ai_extractor.py

from . import database
from .extractor import extract_job_metadata, extract_job_metadata_from_text

app = FastAPI(
    title="DevCareer API",
    description="Share job links with friends — titles, companies, "
    "descriptions and deadlines are fetched automatically.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init_db()


class ExtractRequest(BaseModel):
    """Either `url` (fetch and parse a page) or `text` (parse pasted job
    text directly, no fetch) must be given — see Task 2.2 in PRD.md."""

    url: str = Field(default="", max_length=2000)
    text: str = Field(default="", max_length=20000)

    @field_validator("url")
    @classmethod
    def must_be_http_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Please provide a valid http(s) job link.")
        return value

    @field_validator("text")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def require_url_or_text(self) -> "ExtractRequest":
        if not self.url and not self.text:
            raise ValueError("Provide a job link or paste the job text.")
        return self


class JobCreate(BaseModel):
    """`shared_by` is a real users.id (Task 3.1) rather than a free-text
    name — the frontend gets that id from POST /api/auth/register or
    POST /api/auth/login.

    url and apply_email (Task 2.4) are each independently optional — a
    pasted post might give a real apply link, an apply-by-email address, or
    both — but require_link_or_email below rejects a job with neither, per
    Task 2.2's original decision that an entry with nothing to act on is
    low value."""

    url: str = Field(default="", max_length=2000)
    title: str = Field(..., min_length=1, max_length=300)
    company: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=6000)
    deadline: str = Field(default="", max_length=60)
    location: str = Field(default="", max_length=200)
    source: str = Field(default="", max_length=200)
    user_id: int = Field(...)
    apply_email: str = Field(default="", max_length=200)
    apply_email_subject: str = Field(default="", max_length=200)

    @field_validator("url")
    @classmethod
    def must_be_http_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Please provide a valid http(s) job link.")
        return value

    @field_validator("apply_email")
    @classmethod
    def valid_email_or_blank(cls, value: str) -> str:
        value = value.strip()
        if value and not EMAIL_RE.match(value):
            raise ValueError("Please provide a valid apply email, or leave it blank.")
        return value

    @model_validator(mode="after")
    def require_link_or_email(self) -> "JobCreate":
        if not self.url and not self.apply_email:
            raise ValueError("Provide a job link, an apply email, or both.")
        return self


# Fixed vocabulary, not a free-form emoji picker — mirrors the deadline
# badge's small-fixed-tone pattern rather than open-ended input (Task 3.3).
ALLOWED_REACTIONS = ("👍", "🔥", "🎯", "🎉")


class ReactionRequest(BaseModel):
    user_id: int = Field(...)
    emoji: str = Field(..., min_length=1, max_length=8)

    @field_validator("emoji")
    @classmethod
    def must_be_allowed(cls, value: str) -> str:
        if value not in ALLOWED_REACTIONS:
            raise ValueError("Unsupported reaction.")
        return value


class CommentCreate(BaseModel):
    user_id: int = Field(...)
    body: str = Field(..., min_length=1, max_length=1000)

    @field_validator("body")
    @classmethod
    def trim_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Comment can't be empty.")
        return value


# Deliberately a plain sanity-check regex, not pydantic's EmailStr — that
# needs the extra `email-validator` dependency for one field; matches the
# lightweight-validation style already used for `url` (urlparse, not a URL
# library) elsewhere in this file.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Login handle (PRD.md Task 6.7) — deliberately narrower than the display
# name field: no spaces/emoji, so it's safe to use in URLs later if needed
# and unambiguous to type back in at login.
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class NotificationSettings(BaseModel):
    """PATCH /api/users/{id}/notifications (Task 4.1). Users have no email
    on file by default (Task 3.1's identity is name + password only) — this
    is how one gets added, opt-in, whenever a user wants deadline reminders,
    not collected at registration."""

    email: str = Field(default="", max_length=200)
    opt_in: bool = Field(default=False)

    @field_validator("email")
    @classmethod
    def valid_email_or_blank(cls, value: str) -> str:
        value = value.strip()
        if value and not EMAIL_RE.match(value):
            raise ValueError("Please enter a valid email address.")
        return value

    @model_validator(mode="after")
    def opt_in_requires_email(self) -> "NotificationSettings":
        if self.opt_in and not self.email:
            raise ValueError("Add an email address before turning reminders on.")
        return self


class RegisterRequest(BaseModel):
    """A real account (PRD.md Task 3.1, extended in Task 6.7): username,
    display name, email and password. `username` is the unique login
    handle (not `name` — a friendly display name, shown on shared jobs and
    comments, that doesn't have to be unique); `email` must be both present
    and unique at registration, unlike Task 4.1's original optional/
    added-later design for reminders — the same field now does double
    duty as a real registration field. Registration fails (409) if
    username or email is already taken.

    referral_code (PRD.md Task 6.1) is optional and looked up leniently —
    an unknown or blank code just registers the account with no referral
    credit rather than rejecting the signup."""

    username: str = Field(..., min_length=3, max_length=32)
    name: str = Field(..., min_length=1, max_length=80)
    email: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=6, max_length=200)
    referral_code: str = Field(default="", max_length=20)

    @field_validator("username")
    @classmethod
    def valid_username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_RE.match(value):
            raise ValueError(
                "Username can only use letters, numbers, dots, underscores and hyphens."
            )
        return value

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Please enter a display name.")
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip()
        if not EMAIL_RE.match(value):
            raise ValueError("Please enter a valid email address.")
        return value


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=200)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "devcareer"}


def _public_user(user: dict) -> dict:
    """Never return password_hash to a client."""
    return {
        "id": user["id"],
        "username": user.get("username", ""),
        "name": user["name"],
        "created_at": user["created_at"],
        "email": user.get("email", ""),
        "reminders_opt_in": bool(user.get("reminders_opt_in", 0)),
        "is_admin": bool(user.get("is_admin", 0)) or bool(user.get("is_superadmin", 0)),
        "is_superadmin": bool(user.get("is_superadmin", 0)),
        "referral_code": user.get("referral_code", ""),
        "rank_points": user.get("rank_points", 0),
    }


def _names_from_env(var_name: str) -> set[str]:
    """PRD.md Task 6.2/6.9: comma-separated env vars (ADMIN_NAMES,
    SUPERADMIN_NAMES), not a DB seed script — re-read per call (cheap, and
    avoids caching a stale value at import time the way DB_PATH
    intentionally isn't for this)."""
    raw = os.environ.get(var_name, "")
    return {name.strip().lower() for name in raw.split(",") if name.strip()}


def _maybe_promote_admin(name: str) -> None:
    """Called at register/login so ADMIN_NAMES/SUPERADMIN_NAMES take effect
    immediately — for a brand-new account matching either list, or one
    that already existed before the env var was set. Idempotent
    (database.ensure_*_by_name no-ops once already set)."""
    lowered = name.strip().lower()
    if lowered in _names_from_env("ADMIN_NAMES"):
        database.ensure_admin_by_name(name)
    if lowered in _names_from_env("SUPERADMIN_NAMES"):
        database.ensure_superadmin_by_name(name)


def _require_admin(admin_user_id: int) -> None:
    if not database.is_admin(admin_user_id):
        raise HTTPException(status_code=403, detail="Admin access required.")


def _require_superadmin(superadmin_user_id: int) -> None:
    if not database.is_superadmin(superadmin_user_id):
        raise HTTPException(status_code=403, detail="Super admin access required.")


@app.post("/api/auth/register", status_code=201)
def register(request: RegisterRequest) -> dict:
    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    try:
        user = database.create_user(
            request.username, request.name, request.email, password_hash, request.referral_code
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="That name is already taken.")
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err))
    _maybe_promote_admin(user["name"])
    return _public_user(database.get_user(user["id"]))


@app.post("/api/auth/login")
def login(request: LoginRequest) -> dict:
    """No session/token — the frontend just remembers the returned public
    user object and sends `user_id` back on future job creates. Login is
    by username (PRD.md Task 6.7), not the display name. A generic error
    message for both an unknown username and a wrong password (standard
    practice — don't reveal which one was wrong)."""
    user = database.get_user_by_username(request.username)
    invalid = HTTPException(status_code=401, detail="Invalid username or password.")
    if user is None or not user["password_hash"]:
        raise invalid
    if not bcrypt.checkpw(request.password.encode(), user["password_hash"].encode()):
        raise invalid
    _maybe_promote_admin(user["name"])
    return _public_user(database.get_user(user["id"]))


@app.post("/api/extract")
def extract(request: ExtractRequest) -> dict:
    """Fetch a job link, or parse pasted job text, and return whatever
    details could be detected.

    Nothing is saved — the frontend shows an editable preview first.
    """
    if request.url:
        return extract_job_metadata(request.url)
    return extract_job_metadata_from_text(request.text)


@app.get("/api/jobs")
def get_jobs(search: str = Query(default="", max_length=200)) -> list[dict]:
    return database.list_jobs(search.strip())


@app.post("/api/jobs", status_code=201)
def create_job(job: JobCreate) -> dict:
    user = database.get_user(job.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Unknown user — please sign in again.")
    payload = job.model_dump()
    payload.pop("user_id")
    payload["shared_by_user_id"] = user["id"]
    payload["shared_by"] = ""  # legacy column; display name now comes from users via the join
    if not payload["source"]:
        payload["source"] = urlparse(payload["url"]).netloc
    return database.insert_job(payload)


@app.get("/api/jobs/{job_id}")
def get_single_job(job_id: int) -> dict:
    job = database.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.delete("/api/jobs/{job_id}", status_code=204)
def remove_job(job_id: int, admin_user_id: int = Query(...)) -> None:
    """PRD.md Task 6.2: previously open to anyone, signed in or not — this
    now requires an admin. Query param (not a body) to match this file's
    existing pattern for DELETE .../comments/{comment_id}?user_id= above."""
    _require_admin(admin_user_id)
    if not database.delete_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")


@app.post("/api/jobs/{job_id}/reactions")
def react_to_job(job_id: int, request: ReactionRequest) -> list[dict]:
    """Toggles: reacting again with the same emoji removes it. Returns the
    job's full updated reaction list so the frontend can replace its local
    state without a separate refetch."""
    if database.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if database.get_user(request.user_id) is None:
        raise HTTPException(status_code=400, detail="Unknown user — please sign in again.")
    database.toggle_reaction(job_id, request.user_id, request.emoji)
    return database.list_reactions(job_id)


@app.get("/api/jobs/{job_id}/comments")
def get_comments(job_id: int) -> list[dict]:
    if database.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return database.list_comments(job_id)


@app.post("/api/jobs/{job_id}/comments", status_code=201)
def post_comment(job_id: int, request: CommentCreate) -> dict:
    if database.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if database.get_user(request.user_id) is None:
        raise HTTPException(status_code=400, detail="Unknown user — please sign in again.")
    return database.add_comment(job_id, request.user_id, request.body)


@app.delete("/api/jobs/{job_id}/comments/{comment_id}", status_code=204)
def remove_comment(job_id: int, comment_id: int, user_id: int = Query(...)) -> None:
    outcome = database.delete_comment(job_id, comment_id, user_id)
    if outcome == "not_found":
        raise HTTPException(status_code=404, detail="Comment not found")
    if outcome == "forbidden":
        raise HTTPException(status_code=403, detail="You can only delete your own comments.")


@app.patch("/api/users/{user_id}/notifications")
def update_notifications(user_id: int, request: NotificationSettings) -> dict:
    if database.get_user(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    user = database.update_user_notifications(user_id, request.email, request.opt_in)
    return _public_user(user)


@app.get("/api/leaderboard")
def leaderboard() -> list[dict]:
    """PRD.md Task 6.1 — public, not admin-gated: seeing the board is the
    point of a ranking system, and it carries no private data (name +
    points only)."""
    return database.list_leaderboard()


class AdminRoleUpdate(BaseModel):
    is_admin: bool = Field(...)


@app.get("/api/admin/users")
def admin_list_users(admin_user_id: int = Query(...)) -> list[dict]:
    _require_admin(admin_user_id)
    return database.list_all_users()


@app.patch("/api/admin/users/{user_id}/admin")
def admin_set_role(user_id: int, request: AdminRoleUpdate, admin_user_id: int = Query(...)) -> dict:
    _require_admin(admin_user_id)
    user = database.set_user_admin(user_id, request.is_admin)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _public_user(user)


@app.delete("/api/superadmin/users/{user_id}", status_code=204)
def superadmin_remove_user(user_id: int, superadmin_user_id: int = Query(...)) -> None:
    """PRD.md Task 6.9 — removes a user account entirely (not just their
    admin flag); superadmin-only, one tier above the Task 6.2 admin
    endpoints above. See database.delete_user for what happens to their
    jobs/reactions/comments/referrals."""
    _require_superadmin(superadmin_user_id)
    if user_id == superadmin_user_id:
        raise HTTPException(status_code=400, detail="You can't remove your own account.")
    if not database.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
