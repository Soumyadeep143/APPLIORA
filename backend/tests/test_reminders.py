import os
import re
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Only takes effect if this file is the first to import app.database in the
# process (e.g. run standalone) — when run alongside test_api.py, that
# file's import wins first and this test suite shares its temp DB instead
# (harmless: every assertion here checks specific job ids, never table-wide
# counts, so it's safe regardless of what else is in that DB).
os.environ.setdefault("DEVCAREER_DB_PATH", os.path.join(tempfile.mkdtemp(), "reminders_test.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import database, notifier, reminders  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _register(name: str, password: str = "hunter22"):
    # PRD.md Task 6.7: register now also needs username + email — see
    # test_api.py's _username_for for why this derives rather than takes
    # them as separate params (keeps every existing call site unchanged).
    username = re.sub(r"[^A-Za-z0-9._-]", "", name).lower()
    return client.post(
        "/api/auth/register",
        json={
            "username": username,
            "name": name,
            "email": f"{username}@example.com",
            "password": password,
        },
    ).json()


def _opted_in_user(email: str):
    user = _register("Digest" + os.urandom(4).hex())
    patched = client.patch(
        f"/api/users/{user['id']}/notifications", json={"email": email, "opt_in": True}
    ).json()
    return patched


def _create_job(deadline: str = "", title: str = "Reminder Test Job"):
    user = _register("Reminders" + os.urandom(4).hex())
    payload = {
        "url": "https://example.com/jobs/reminder-test",
        "title": title,
        "deadline": deadline,
        "user_id": user["id"],
    }
    return client.post("/api/jobs", json=payload).json()


@pytest.fixture(autouse=True)
def _no_real_emails(monkeypatch):
    """Same reasoning as test_extractor.py's _no_real_ai_calls fixture: a
    real RESEND_API_KEY loaded into the process env by app.main's
    load_dotenv() must never let these tests hit the real network."""
    monkeypatch.setattr("app.reminders.send_digest_email", lambda *a, **k: False)


def test_job_within_window_is_due():
    deadline = (date.today() + timedelta(days=2)).isoformat()
    job = _create_job(deadline)
    assert job["id"] in {j["id"] for j in reminders.jobs_needing_reminder()}


def test_job_outside_window_is_not_due():
    deadline = (date.today() + timedelta(days=30)).isoformat()
    job = _create_job(deadline)
    assert job["id"] not in {j["id"] for j in reminders.jobs_needing_reminder()}


def test_past_deadline_is_not_due():
    deadline = (date.today() - timedelta(days=1)).isoformat()
    job = _create_job(deadline)
    assert job["id"] not in {j["id"] for j in reminders.jobs_needing_reminder()}


def test_freeform_deadline_is_skipped_not_guessed():
    job = _create_job("Rolling basis")
    assert job["id"] not in {j["id"] for j in reminders.jobs_needing_reminder()}


def test_already_reminded_job_is_not_due_again():
    deadline = (date.today() + timedelta(days=1)).isoformat()
    job = _create_job(deadline)
    assert job["id"] in {j["id"] for j in reminders.jobs_needing_reminder()}
    database.mark_reminder_sent(job["id"])
    assert job["id"] not in {j["id"] for j in reminders.jobs_needing_reminder()}


def test_opting_in_sets_digest_cursor_to_current_max_job_id():
    _create_job()  # ensure at least one job exists to be "caught up to"
    user = _opted_in_user("cursor@example.com")
    row = database.get_user(user["id"])
    assert row["last_digest_job_id"] is not None


def test_editing_email_while_opted_in_does_not_reset_cursor():
    user = _opted_in_user("keep-cursor@example.com")
    _create_job()  # would move the cursor if opt-in were (wrongly) re-triggered
    original_cursor = database.get_user(user["id"])["last_digest_job_id"]
    client.patch(
        f"/api/users/{user['id']}/notifications",
        json={"email": "keep-cursor-2@example.com", "opt_in": True},
    )
    assert database.get_user(user["id"])["last_digest_job_id"] == original_cursor


def test_job_created_after_cursor_is_a_new_job_for_digest():
    user = _opted_in_user("newjobs@example.com")
    job = _create_job()
    cursor = database.get_user(user["id"])["last_digest_job_id"]
    new_jobs = database.list_jobs_after_id(cursor)
    assert job["id"] in {j["id"] for j in new_jobs}


def test_run_sends_combined_digest_and_advances_cursor(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.reminders.send_digest_email",
        lambda email, due, new: calls.append((email, [j["id"] for j in due], [j["id"] for j in new]))
        or True,
    )
    user = _opted_in_user("combined@example.com")
    cursor_before = database.get_user(user["id"])["last_digest_job_id"]

    deadline = (date.today() + timedelta(days=1)).isoformat()
    due_job = _create_job(deadline)
    new_job = _create_job()  # no deadline — only qualifies as a "new share", not a reminder

    summary = reminders.run()

    assert summary["due_jobs"] >= 1
    assert summary["new_jobs_total"] >= 1
    assert summary["emails_sent"] >= 1
    match = next(c for c in calls if c[0] == "combined@example.com")
    _, due_ids, new_ids = match
    assert due_job["id"] in due_ids
    assert new_job["id"] in new_ids

    cursor_after = database.get_user(user["id"])["last_digest_job_id"]
    assert cursor_after > cursor_before

    # Second run: due job deduped, and no jobs created since the advanced
    # cursor, so this recipient's digest is empty on both fronts.
    calls.clear()
    reminders.run()
    match = next((c for c in calls if c[0] == "combined@example.com"), None)
    if match:
        _, due_ids, new_ids = match
        assert due_job["id"] not in due_ids
        assert new_job["id"] not in new_ids


def test_run_sends_nothing_when_no_recipients_opted_in(monkeypatch):
    monkeypatch.setattr("app.reminders.database.list_reminder_recipients", lambda: [])
    calls = []
    monkeypatch.setattr(
        "app.reminders.send_digest_email",
        lambda *a, **k: calls.append(1) or True,
    )
    deadline = (date.today() + timedelta(days=1)).isoformat()
    _create_job(deadline)
    reminders.run()
    assert calls == []


def test_notifier_noops_without_api_key(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    assert notifier.send_digest_email("a@example.com", [{"title": "X"}], []) is False


def test_notifier_noops_with_no_recipient_or_no_content(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "fake-key-for-test")
    assert notifier.send_digest_email("", [{"title": "X"}], []) is False
    assert notifier.send_digest_email("a@example.com", [], []) is False


def test_notifier_formats_combined_email_with_both_sections():
    due = [{"title": "Closing Job", "company": "Acme", "deadline": "2026-08-01"}]
    new = [{"title": "New Job", "company": "Globex", "deadline": ""}]
    subject, body = notifier._format_email(due, new)
    assert "Closing Job" in body and "closing soon" in body.lower()
    assert "New Job" in body and "new jobs" in body.lower()
