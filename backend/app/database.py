"""SQLite storage for shared jobs."""

import os
import re
import secrets
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("DEVCAREER_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "devcareer.db"))

# Rank points (PRD.md Task 6.1): implementation defaults, not a product
# decision raised beforehand — same footing as REMINDER_WINDOW_DAYS in
# reminders.py. Referral weighted higher since it's the growth lever.
REFERRAL_POINTS = 20
JOB_SHARE_POINTS = 5

# Excludes visually-ambiguous characters (0/O, 1/I/L) since this code is
# meant to be read aloud or typed by hand when sharing with a friend.
_REFERRAL_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_REFERRAL_CODE_LENGTH = 7

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    url                  TEXT NOT NULL DEFAULT '',
    title                TEXT NOT NULL,
    company              TEXT NOT NULL DEFAULT '',
    description          TEXT NOT NULL DEFAULT '',
    deadline             TEXT NOT NULL DEFAULT '',
    location             TEXT NOT NULL DEFAULT '',
    source               TEXT NOT NULL DEFAULT '',
    shared_by            TEXT NOT NULL DEFAULT 'Anonymous',
    shared_by_user_id    INTEGER REFERENCES users(id),
    apply_email          TEXT NOT NULL DEFAULT '',
    apply_email_subject  TEXT NOT NULL DEFAULT '',
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS job_reactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id     INTEGER NOT NULL REFERENCES jobs(id),
    user_id    INTEGER NOT NULL REFERENCES users(id),
    emoji      TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (job_id, user_id, emoji)
);

CREATE TABLE IF NOT EXISTS job_comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id     INTEGER NOT NULL REFERENCES jobs(id),
    user_id    INTEGER NOT NULL REFERENCES users(id),
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS job_reminders_sent (
    job_id  INTEGER PRIMARY KEY REFERENCES jobs(id),
    sent_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# jobs.shared_by is preserved as a *legacy* display name for rows created
# before Task 3.1 (real identity via `users`) shipped. New rows are always
# linked via shared_by_user_id; JOB_SELECT_COLUMNS below prefers the live
# users.name over it via COALESCE, so a legacy row with no matching user
# still displays whatever free-text name it was shared under.
JOB_SELECT_COLUMNS = """
    jobs.id, jobs.url, jobs.title, jobs.company, jobs.description,
    jobs.deadline, jobs.location, jobs.source, jobs.shared_by_user_id,
    jobs.apply_email, jobs.apply_email_subject,
    jobs.created_at,
    COALESCE(users.name, jobs.shared_by) AS shared_by,
    (SELECT COUNT(*) FROM job_comments WHERE job_comments.job_id = jobs.id) AS comment_count
"""
JOB_SELECT_FROM = "FROM jobs LEFT JOIN users ON users.id = jobs.shared_by_user_id"


def _migrate_jobs_table(conn) -> None:
    """`jobs` may already exist from before Task 3.1 shipped — CREATE TABLE
    IF NOT EXISTS above won't add the new column to an existing table, so
    add it by hand if missing. Existing rows are left with
    shared_by_user_id = NULL; there's no `users` row to match them against
    since that table only starts getting populated once login exists, so
    they keep displaying their original free-text shared_by (see JOB_SELECT
    columns' COALESCE above) rather than a fabricated match."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    if "shared_by_user_id" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN shared_by_user_id INTEGER REFERENCES users(id)")
    if "apply_email" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN apply_email TEXT NOT NULL DEFAULT ''")
    if "apply_email_subject" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN apply_email_subject TEXT NOT NULL DEFAULT ''")


def _drop_users_name_unique_constraint(conn) -> None:
    """`name` (the display name) started life as the account's only
    identifier and was UNIQUE COLLATE NOCASE from the very first schema.
    PRD.md Task 6.7 split off `username` as the real unique login handle
    and `name` was meant to become a free-form display name — but SQLite
    can't drop a column constraint via ALTER TABLE, so this leftover
    constraint kept silently rejecting two different accounts that just
    happen to share a display name. Detected via the auto-index SQLite
    creates for an inline UNIQUE column constraint; if found, the table is
    rebuilt without it (one-time — a fresh or already-fixed database has no
    such index, so this is a no-op on every later start).

    Rebuilds from the table's own live CREATE TABLE text (sqlite_master),
    not a hand-written column list — a long-lived real database can carry
    columns from schema iterations this codebase has since moved past (e.g.
    an old `last_digest_at`, superseded by `last_digest_job_id`), and a
    hardcoded rebuild would silently drop that data instead of preserving
    it as-is."""
    for idx in conn.execute("PRAGMA index_list(users)").fetchall():
        if not idx["unique"]:
            continue
        info = conn.execute(f"PRAGMA index_info({idx['name']})").fetchall()
        if [c["name"] for c in info] == ["name"]:
            break
    else:
        return

    old_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()["sql"]
    new_sql = old_sql.replace("UNIQUE COLLATE NOCASE", "COLLATE NOCASE", 1)
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    col_list = ", ".join(columns)
    conn.execute("ALTER TABLE users RENAME TO users_old")
    conn.execute(new_sql)
    conn.execute(f"INSERT INTO users ({col_list}) SELECT {col_list} FROM users_old")
    conn.execute("DROP TABLE users_old")


def _migrate_users_table(conn) -> None:
    """`users` may already exist from the earlier simple-invite-code scheme
    (no password), which had no `password_hash` column. Existing accounts
    from that era (empty-string hash, the column's default) simply can't
    log in under the new password-based scheme — there's no password to
    migrate from, since none was ever collected. They'd need to register
    again under a new username; display names no longer have to be unique
    (see _drop_users_name_unique_constraint below) — only username does —
    in practice this only matters for the handful of test accounts created
    during development, not real users."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "password_hash" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
    if "email" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    if "reminders_opt_in" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN reminders_opt_in INTEGER NOT NULL DEFAULT 0")
    if "last_digest_job_id" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN last_digest_job_id INTEGER")
    if "is_admin" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    if "is_superadmin" not in columns:
        # PRD.md Task 6.9: a tier above admin — admins moderate jobs
        # (Task 6.2's admin-gated delete) and can promote/demote other
        # admins; superadmins can additionally remove user accounts
        # entirely. Every superadmin is implicitly treated as an admin too
        # (checked in main.py's _require_admin), not a separate flag to
        # keep in sync by hand.
        conn.execute("ALTER TABLE users ADD COLUMN is_superadmin INTEGER NOT NULL DEFAULT 0")
    if "referral_code" not in columns:
        # No UNIQUE constraint at the SQL level — SQLite can't add one via
        # ALTER TABLE ADD COLUMN without a full table rebuild. Uniqueness is
        # enforced the same way it's checked: _generate_referral_code loops
        # until it finds a code with no existing row, both at creation time
        # and in the backfill below.
        conn.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")
    if "referred_by_user_id" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN referred_by_user_id INTEGER REFERENCES users(id)")
    if "rank_points" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN rank_points INTEGER NOT NULL DEFAULT 0")
    if "username" not in columns:
        # PRD.md Task 6.7: name (display name) and username (the actual
        # unique login handle) split apart — previously `name` did both
        # jobs. No SQL UNIQUE constraint here for the same reason as
        # referral_code above (ALTER TABLE can't add one); enforced at the
        # application layer in create_user instead.
        conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "linkedin_url" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN linkedin_url TEXT NOT NULL DEFAULT ''")
    if "github_url" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN github_url TEXT NOT NULL DEFAULT ''")
    if "x_url" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN x_url TEXT NOT NULL DEFAULT ''")
    if "bio" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN bio TEXT NOT NULL DEFAULT ''")
    if "skills" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN skills TEXT NOT NULL DEFAULT ''")
    if "target_role" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN target_role TEXT NOT NULL DEFAULT ''")
    # Backfill: any row that predates the referral_code column (or was
    # somehow inserted without one) gets a freshly generated code so every
    # existing account can start referring people immediately.
    for row in conn.execute("SELECT id FROM users WHERE referral_code IS NULL").fetchall():
        conn.execute(
            "UPDATE users SET referral_code = ? WHERE id = ?",
            (_generate_referral_code(conn), row["id"]),
        )
    # Backfill: any row from before `username` existed gets one derived
    # from its display name, so existing accounts (including real ones —
    # not just test data) can still log in after this migration runs.
    for row in conn.execute(
        "SELECT id, name FROM users WHERE username IS NULL OR username = ''"
    ).fetchall():
        conn.execute(
            "UPDATE users SET username = ? WHERE id = ?",
            (_generate_username_from_name(conn, row["name"]), row["id"]),
        )
    _drop_users_name_unique_constraint(conn)


def _generate_referral_code(conn) -> str:
    while True:
        code = "".join(secrets.choice(_REFERRAL_CODE_ALPHABET) for _ in range(_REFERRAL_CODE_LENGTH))
        if conn.execute("SELECT 1 FROM users WHERE referral_code = ?", (code,)).fetchone() is None:
            return code


def _generate_username_from_name(conn, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "", name.lower()) or "user"
    candidate = base
    suffix = 1
    while conn.execute(
        "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (candidate,)
    ).fetchone():
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrate_jobs_table(conn)
        _migrate_users_table(conn)


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_job(job: dict) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO jobs (url, title, company, description, deadline,
                                 location, source, shared_by, shared_by_user_id,
                                 apply_email, apply_email_subject)
               VALUES (:url, :title, :company, :description, :deadline,
                       :location, :source, :shared_by, :shared_by_user_id,
                       :apply_email, :apply_email_subject)""",
            job,
        )
        if job.get("shared_by_user_id"):
            conn.execute(
                "UPDATE users SET rank_points = rank_points + ? WHERE id = ?",
                (JOB_SHARE_POINTS, job["shared_by_user_id"]),
            )
        return get_job(cursor.lastrowid, conn)


def update_job(job_id: int, fields: dict) -> dict | None:
    """PRD.md Task 6.10 — admin/superadmin editing. Doesn't touch
    shared_by/shared_by_user_id/source/created_at — an edit corrects the
    job's own details, not who shared it or when."""
    with get_connection() as conn:
        conn.execute(
            """UPDATE jobs SET url = :url, title = :title, company = :company,
                   description = :description, deadline = :deadline,
                   location = :location, apply_email = :apply_email,
                   apply_email_subject = :apply_email_subject
               WHERE id = :id""",
            {**fields, "id": job_id},
        )
        return get_job(job_id, conn)


def get_job(job_id: int, conn=None) -> dict | None:
    query = f"SELECT {JOB_SELECT_COLUMNS} {JOB_SELECT_FROM} WHERE jobs.id = ?"
    if conn is not None:
        row = conn.execute(query, (job_id,)).fetchone()
        if row is None:
            return None
        job = dict(row)
        job["reactions"] = list_reactions(job_id, conn)
        return job
    with get_connection() as conn:
        row = conn.execute(query, (job_id,)).fetchone()
        if row is None:
            return None
        job = dict(row)
        job["reactions"] = list_reactions(job_id, conn)
        return job


def list_jobs(search: str = "") -> list[dict]:
    query = f"SELECT {JOB_SELECT_COLUMNS} {JOB_SELECT_FROM}"
    params: tuple = ()
    if search:
        query += (
            " WHERE jobs.title LIKE ? OR jobs.company LIKE ? OR jobs.description LIKE ?"
            " OR COALESCE(users.name, jobs.shared_by) LIKE ? OR jobs.location LIKE ?"
        )
        like = f"%{search}%"
        params = (like, like, like, like, like)
    query += " ORDER BY jobs.id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        jobs = [dict(row) for row in rows]
        for job in jobs:
            job["reactions"] = list_reactions(job["id"], conn)
        return jobs


def delete_job(job_id: int) -> bool:
    """No FK cascade configured (SQLite requires PRAGMA foreign_keys = ON,
    not set here — see users.shared_by_user_id above for the same
    intentional non-cascading choice), so reactions/comments are cleaned up
    by hand to avoid orphan rows."""
    with get_connection() as conn:
        conn.execute("DELETE FROM job_reactions WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM job_comments WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM job_reminders_sent WHERE job_id = ?", (job_id,))
        cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return cursor.rowcount > 0


def create_user(
    username: str, name: str, email: str, password_hash: str, referred_by_code: str = ""
) -> dict:
    """Raises ValueError (caller turns this into a 409) if username or
    email is already taken (PRD.md Task 6.7 — checked at the application
    layer since ALTER TABLE couldn't add real UNIQUE constraints for these
    two after the fact; see _migrate_users_table). `name` (the display
    name) is deliberately NOT checked for uniqueness — only `username` is
    the account's unique handle; two people can both be "Alex". A real
    account, not an auto-created one: the password is the only way back in
    (see PRD.md Task 3.1).

    `referred_by_code` (PRD.md Task 6.1) is looked up leniently: an unknown
    or blank code just registers the account with no referral credit rather
    than rejecting the signup — a typo'd code shouldn't block someone from
    joining, matching this codebase's "empty over confidently wrong"
    principle elsewhere (extractor.py)."""
    username = username.strip()
    name = name.strip()
    email = email.strip()
    with get_connection() as conn:
        if conn.execute(
            "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone():
            raise ValueError("That username is already taken.")
        if email and conn.execute(
            "SELECT 1 FROM users WHERE email = ? COLLATE NOCASE", (email,)
        ).fetchone():
            raise ValueError("That email is already registered.")
        referred_by_user_id = None
        if referred_by_code.strip():
            referrer = conn.execute(
                "SELECT id FROM users WHERE referral_code = ?", (referred_by_code.strip(),)
            ).fetchone()
            if referrer:
                referred_by_user_id = referrer["id"]
        code = _generate_referral_code(conn)
        cursor = conn.execute(
            """INSERT INTO users (username, name, email, password_hash,
                                  referral_code, referred_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, name, email, password_hash, code, referred_by_user_id),
        )
        if referred_by_user_id is not None:
            conn.execute(
                "UPDATE users SET rank_points = rank_points + ? WHERE id = ?",
                (REFERRAL_POINTS, referred_by_user_id),
            )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)


def get_user_by_username(username: str) -> dict | None:
    username = username.strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()
        return dict(row) if row else None


def get_user(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def list_reactions(job_id: int, conn=None) -> list[dict]:
    query = """SELECT job_reactions.emoji, job_reactions.user_id, users.name AS user_name
               FROM job_reactions JOIN users ON users.id = job_reactions.user_id
               WHERE job_reactions.job_id = ?
               ORDER BY job_reactions.id"""
    if conn is not None:
        return [dict(row) for row in conn.execute(query, (job_id,)).fetchall()]
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query, (job_id,)).fetchall()]


def toggle_reaction(job_id: int, user_id: int, emoji: str) -> bool:
    """Adds the reaction if this user hasn't already reacted with this exact
    emoji on this job, else removes it. Returns True if added, False if
    removed."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM job_reactions WHERE job_id = ? AND user_id = ? AND emoji = ?",
            (job_id, user_id, emoji),
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM job_reactions WHERE id = ?", (existing["id"],))
            return False
        conn.execute(
            "INSERT INTO job_reactions (job_id, user_id, emoji) VALUES (?, ?, ?)",
            (job_id, user_id, emoji),
        )
        return True


_COMMENT_SELECT = """SELECT job_comments.id, job_comments.job_id, job_comments.user_id,
                             users.name AS user_name, job_comments.body, job_comments.created_at
                      FROM job_comments JOIN users ON users.id = job_comments.user_id"""


def list_comments(job_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            f"{_COMMENT_SELECT} WHERE job_comments.job_id = ? ORDER BY job_comments.id",
            (job_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def add_comment(job_id: int, user_id: int, body: str) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO job_comments (job_id, user_id, body) VALUES (?, ?, ?)",
            (job_id, user_id, body),
        )
        row = conn.execute(
            f"{_COMMENT_SELECT} WHERE job_comments.id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)


def delete_comment(job_id: int, comment_id: int, user_id: int) -> str:
    """Returns 'deleted', 'not_found', or 'forbidden' so the caller
    (main.py) can map straight to an HTTP status without a second query."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id FROM job_comments WHERE id = ? AND job_id = ?",
            (comment_id, job_id),
        ).fetchone()
        if row is None:
            return "not_found"
        if row["user_id"] != user_id:
            return "forbidden"
        conn.execute("DELETE FROM job_comments WHERE id = ?", (comment_id,))
        return "deleted"


def update_user_notifications(user_id: int, email: str, opt_in: bool) -> dict | None:
    """Turning opt_in on (from off, or for the first time ever) resets the
    digest cursor (last_digest_job_id) to the current max job id — Task
    4.2's sharing digest reads jobs newer than that cursor, and a fresh
    opt-in shouldn't dump the board's entire history into someone's first
    email. Re-saving other fields (e.g. just editing the email) while
    already opted in leaves the cursor untouched, so no pending digest
    content gets skipped.

    The cursor is a job id, not a timestamp: jobs.created_at and this
    column would both come from SQLite's second-granularity datetime('now'),
    so an opt-in and a job share landing in the same wall-clock second could
    tie and the job would be silently dropped from the digest. Ids are
    strictly monotonic and can't collide."""
    with get_connection() as conn:
        current = conn.execute(
            "SELECT reminders_opt_in, last_digest_job_id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if current is None:
            return None
        fresh_opt_in = opt_in and (
            not current["reminders_opt_in"] or current["last_digest_job_id"] is None
        )
        if fresh_opt_in:
            conn.execute(
                """UPDATE users SET email = ?, reminders_opt_in = ?,
                       last_digest_job_id = (SELECT COALESCE(MAX(id), 0) FROM jobs)
                   WHERE id = ?""",
                (email, 1 if opt_in else 0, user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET email = ?, reminders_opt_in = ? WHERE id = ?",
                (email, 1 if opt_in else 0, user_id),
            )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def update_user_profile_details(
    user_id: int,
    linkedin_url: str,
    github_url: str,
    x_url: str,
    bio: str,
    skills: str,
    target_role: str,
) -> dict | None:
    """Every field here is independently optional — leaving one blank just
    clears it, same as update_user_notifications' email field above. Saved
    (and re-editable) any number of times; there's no "locked after first
    save" state."""
    with get_connection() as conn:
        cursor = conn.execute(
            """UPDATE users SET linkedin_url = ?, github_url = ?, x_url = ?,
                   bio = ?, skills = ?, target_role = ?
               WHERE id = ?""",
            (linkedin_url, github_url, x_url, bio, skills, target_role, user_id),
        )
        if cursor.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row)


def list_reminder_recipients() -> list[dict]:
    """Opted-in users with a real email on file — everything reminders.py
    needs to send a combined deadline + sharing-digest email (Tasks 4.1 and
    4.2 share one opt-in, per PRD.md)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, email, last_digest_job_id FROM users"
            " WHERE reminders_opt_in = 1 AND email != ''"
        ).fetchall()
        return [dict(row) for row in rows]


def list_jobs_after_id(since_id: int) -> list[dict]:
    query = f"SELECT {JOB_SELECT_COLUMNS} {JOB_SELECT_FROM} WHERE jobs.id > ? ORDER BY jobs.id"
    with get_connection() as conn:
        rows = conn.execute(query, (since_id,)).fetchall()
        jobs = [dict(row) for row in rows]
        for job in jobs:
            job["reactions"] = list_reactions(job["id"], conn)
        return jobs


def mark_digest_sent(user_id: int) -> None:
    """Advances this user's digest cursor to the current max job id —
    called once per daily run for every recipient, regardless of whether
    there was anything to report or whether delivery succeeded, so the
    window is always "since the last run" rather than growing unboundedly."""
    with get_connection() as conn:
        conn.execute(
            """UPDATE users SET last_digest_job_id = (SELECT COALESCE(MAX(id), 0) FROM jobs)
               WHERE id = ?""",
            (user_id,),
        )


def reminder_already_sent(job_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM job_reminders_sent WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None


def mark_reminder_sent(job_id: int) -> None:
    """Fires once per job, not once per day it stays in the reminder
    window — see reminders.py."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO job_reminders_sent (job_id) VALUES (?)", (job_id,)
        )


def is_admin(user_id: int) -> bool:
    """Superadmins count as admins too (PRD.md Task 6.9) — one flag isn't
    downgraded by the other, so a superadmin never loses ordinary admin
    capabilities (job deletion, the Task 6.2 Admin page)."""
    user = get_user(user_id)
    return bool(user and (user["is_admin"] or user["is_superadmin"]))


def is_superadmin(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user["is_superadmin"])


def ensure_master_superadmin(username: str, name: str, password_hash: str) -> None:
    """Seeds the one hardcoded bootstrap superadmin account (main.py's
    _MASTER_SUPERADMIN_USERNAME) on first startup — the only way a
    superadmin can ever exist, since ordinary registration never sets
    is_superadmin and regular admin promotion (set_user_admin below) is
    superadmin-gated but never grants superadmin itself.

    Idempotent: a no-op on every later startup once the account exists,
    and deliberately never overwrites its stored password_hash on those
    later runs — only the is_superadmin flag is re-asserted, so the
    account can't quietly lose superadmin without this reinstating it, but
    also can't have its password reset out from under it by a restart."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET is_superadmin = 1 WHERE id = ? AND is_superadmin = 0",
                (existing["id"],),
            )
            return
        code = _generate_referral_code(conn)
        conn.execute(
            """INSERT INTO users (username, name, email, password_hash,
                                  referral_code, is_superadmin)
               VALUES (?, ?, '', ?, ?, 1)""",
            (username, name, password_hash, code),
        )


def list_all_users() -> list[dict]:
    """Admin user-management list (PRD.md Task 6.2) — every account's
    public-safe fields plus is_admin/is_superadmin, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, name, username, email, is_admin, is_superadmin,
                      referral_code, rank_points, created_at
               FROM users ORDER BY id DESC"""
        ).fetchall()
        return [dict(row) for row in rows]


def set_user_admin(user_id: int, is_admin_flag: bool) -> dict | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET is_admin = ? WHERE id = ?", (1 if is_admin_flag else 0, user_id)
        )
        if cursor.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row)


def delete_user(user_id: int) -> bool:
    """Superadmin-only (PRD.md Task 6.9). Jobs the user shared are kept —
    the board is shared community content, not exclusively theirs — but
    orphaned to shared_by_user_id = NULL, the same "legacy display name"
    state pre-Task-3.1 rows already use (see JOB_SELECT_COLUMNS' COALESCE).
    Their own reactions/comments are removed outright (tied to identity,
    a "ghost" reaction from a deleted account doesn't mean anything), and
    anyone who used this account's referral code has referred_by_user_id
    cleared rather than left dangling."""
    with get_connection() as conn:
        conn.execute("UPDATE jobs SET shared_by_user_id = NULL WHERE shared_by_user_id = ?", (user_id,))
        conn.execute("UPDATE users SET referred_by_user_id = NULL WHERE referred_by_user_id = ?", (user_id,))
        conn.execute("DELETE FROM job_reactions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM job_comments WHERE user_id = ?", (user_id,))
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return cursor.rowcount > 0


def list_leaderboard(limit: int = 20) -> list[dict]:
    """Top users by rank_points (PRD.md Task 6.1) — referrals plus jobs
    shared. Ties broken by earliest account (lower id) rather than
    arbitrarily, so the ordering is stable across calls."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, rank_points FROM users ORDER BY rank_points DESC, id ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_stats() -> dict:
    """Landing-page headline numbers, computed live instead of hardcoded.
    "friend circles" has no dedicated table — it's approximated as the
    count of users who have successfully brought in at least one referral
    (each is the center of one circle)."""
    with get_connection() as conn:
        jobs_shared = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        friend_circles = conn.execute(
            "SELECT COUNT(DISTINCT referred_by_user_id) FROM users WHERE referred_by_user_id IS NOT NULL"
        ).fetchone()[0]
        companies_posted = conn.execute(
            "SELECT COUNT(DISTINCT company) FROM jobs WHERE TRIM(company) != ''"
        ).fetchone()[0]
        return {
            "jobs_shared": jobs_shared,
            "friend_circles": friend_circles,
            "companies_posted": companies_posted,
        }
