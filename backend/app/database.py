"""SQLite storage for shared jobs."""

import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("APPLIORA_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "appliora.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT NOT NULL,
    title       TEXT NOT NULL,
    company     TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    deadline    TEXT NOT NULL DEFAULT '',
    location    TEXT NOT NULL DEFAULT '',
    source      TEXT NOT NULL DEFAULT '',
    shared_by   TEXT NOT NULL DEFAULT 'Anonymous',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)


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
                                 location, source, shared_by)
               VALUES (:url, :title, :company, :description, :deadline,
                       :location, :source, :shared_by)""",
            job,
        )
        return get_job(cursor.lastrowid, conn)


def get_job(job_id: int, conn=None) -> dict | None:
    if conn is not None:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_jobs(search: str = "") -> list[dict]:
    query = "SELECT * FROM jobs"
    params: tuple = ()
    if search:
        query += (
            " WHERE title LIKE ? OR company LIKE ? OR description LIKE ?"
            " OR shared_by LIKE ? OR location LIKE ?"
        )
        like = f"%{search}%"
        params = (like, like, like, like, like)
    query += " ORDER BY id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def delete_job(job_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return cursor.rowcount > 0
