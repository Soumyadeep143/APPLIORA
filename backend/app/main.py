"""Appliora API — share job links with friends, with auto-fetched details."""

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
    title="Appliora API",
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
    POST /api/auth/login."""

    url: str = Field(..., min_length=8, max_length=2000)
    title: str = Field(..., min_length=1, max_length=300)
    company: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=6000)
    deadline: str = Field(default="", max_length=60)
    location: str = Field(default="", max_length=200)
    source: str = Field(default="", max_length=200)
    user_id: int = Field(...)

    @field_validator("url")
    @classmethod
    def must_be_http_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Please provide a valid http(s) job link.")
        return value


class _NameAndPassword(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=6, max_length=200)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Please enter a display name.")
        return value


class RegisterRequest(_NameAndPassword):
    """A real account (PRD.md Task 3.1): a name + password, hashed with
    bcrypt — no third-party identity provider, no external service.
    Registration fails if the name is already taken (case-insensitive)."""


class LoginRequest(_NameAndPassword):
    pass


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "appliora"}


def _public_user(user: dict) -> dict:
    """Never return password_hash to a client."""
    return {"id": user["id"], "name": user["name"], "created_at": user["created_at"]}


@app.post("/api/auth/register", status_code=201)
def register(request: RegisterRequest) -> dict:
    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    try:
        user = database.create_user(request.name, password_hash)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="That name is already taken.")
    return _public_user(user)


@app.post("/api/auth/login")
def login(request: LoginRequest) -> dict:
    """No session/token — the frontend just remembers the returned
    {id, name} (localStorage) and sends `user_id` back on future job
    creates. A generic error message for both an unknown name and a wrong
    password (standard practice — don't reveal which one was wrong)."""
    user = database.get_user_by_name(request.name)
    invalid = HTTPException(status_code=401, detail="Invalid name or password.")
    if user is None or not user["password_hash"]:
        raise invalid
    if not bcrypt.checkpw(request.password.encode(), user["password_hash"].encode()):
        raise invalid
    return _public_user(user)


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
def remove_job(job_id: int) -> None:
    if not database.delete_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
