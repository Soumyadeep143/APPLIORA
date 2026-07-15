"""SQLite storage for shared jobs."""

import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("APPLIORA_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "appliora.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    url               TEXT NOT NULL,
    title             TEXT NOT NULL,
    company           TEXT NOT NULL DEFAULT '',
    description       TEXT NOT NULL DEFAULT '',
    deadline          TEXT NOT NULL DEFAULT '',
    location          TEXT NOT NULL DEFAULT '',
    source            TEXT NOT NULL DEFAULT '',
    shared_by         TEXT NOT NULL DEFAULT 'Anonymous',
    shared_by_user_id INTEGER REFERENCES users(id),
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
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
    jobs.created_at,
    COALESCE(users.name, jobs.shared_by) AS shared_by
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


def _migrate_users_table(conn) -> None:
    """`users` may already exist from the earlier simple-invite-code scheme
    (no password), which had no `password_hash` column. Existing accounts
    from that era (empty-string hash, the column's default) simply can't
    log in under the new password-based scheme — there's no password to
    migrate from, since none was ever collected. They'd need to register
    again under the same name, which will fail on the UNIQUE constraint;
    in practice this only matters for the handful of test accounts created
    during development, not real users."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "password_hash" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")


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
                                 location, source, shared_by, shared_by_user_id)
               VALUES (:url, :title, :company, :description, :deadline,
                       :location, :source, :shared_by, :shared_by_user_id)""",
            job,
        )
        return get_job(cursor.lastrowid, conn)


def get_job(job_id: int, conn=None) -> dict | None:
    query = f"SELECT {JOB_SELECT_COLUMNS} {JOB_SELECT_FROM} WHERE jobs.id = ?"
    if conn is not None:
        row = conn.execute(query, (job_id,)).fetchone()
        return dict(row) if row else None
    with get_connection() as conn:
        row = conn.execute(query, (job_id,)).fetchone()
        return dict(row) if row else None


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
        return [dict(row) for row in rows]


def delete_job(job_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return cursor.rowcount > 0


def create_user(name: str, password_hash: str) -> dict:
    """Raises sqlite3.IntegrityError (caller turns this into a 409) if the
    name is already taken — case-insensitive, see the users.name UNIQUE
    COLLATE NOCASE constraint. A real account, not an auto-created one:
    the password is the only way back in (see PRD.md Task 3.1)."""
    name = name.strip()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (name, password_hash) VALUES (?, ?)", (name, password_hash)
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)


def get_user_by_name(name: str) -> dict | None:
    name = name.strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        return dict(row) if row else None


def get_user(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
