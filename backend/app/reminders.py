"""Daily notification scan — deadline reminders (PRD.md Task 4.1) and the
"what friends shared" digest (Task 4.2). One opt-in, one combined email per
recipient per run, per user direction, rather than two separate features.

Deliberately *not* an in-process scheduler (no APScheduler, no background
thread started from main.py): this app's every test run and every `uvicorn
--reload` restart imports app.main, so an in-process scheduler would spin
up (and double-fire under --reload) on every one of those, and a Render
web dyno can restart/scale independently of when a once-a-day scan should
run. Instead this is a standalone entry point meant to be triggered by an
external scheduler — a Render Cron Job pointed at this module (see
README.md's Deploy section), or `python -m app.reminders` from cron/Task
Scheduler locally.

Deadline side: jobs whose deadline falls within REMINDER_WINDOW_DAYS are
marked reminded (job_reminders_sent — see database.py) so the next run
doesn't re-notify about the same job every day it stays in the window. A
user who opts in after a job's reminder already fired simply won't get
notified about that already-fired job; acceptable for a small friend
board, same "known, honest limitation" tradeoff as the AshbyHQ extraction
gap in BACKEND_VERIFICATION_ROADMAP.md.

Only jobs with a clean ISO yyyy-mm-dd deadline are considered for the
deadline side — free-text deadlines ("Rolling basis", a mis-parsed page
string) can't be reliably compared to "N days from now", and guessing
would risk a confidently wrong reminder. extractor.py already normalises
to this format when it can (see _normalise_date); anything else is left
alone rather than guessed at.

Digest side: each recipient has their own last_digest_job_id cursor (set
to the current max job id the moment they opt in, so a fresh opt-in
doesn't dump the board's entire history on them — see
update_user_notifications). Every run, every recipient's cursor advances
regardless of whether there was anything new to report, so the window is
always "since the last run," not growing unboundedly. The cursor is a job
id, not a timestamp, deliberately — see update_user_notifications for why.
"""

from datetime import date, datetime, timedelta

from dotenv import load_dotenv

# Must run before `from . import database` — database.py reads
# DEVCAREER_DB_PATH from the environment at *import time* (module-level
# assignment), so loading backend/.env after that import is already too
# late and silently locks in the default DB path. main.py gets this order
# right (load_dotenv() before importing database); this mirrors it rather
# than gating it behind `if __name__ == "__main__"`, since anything that
# imports this module — not just running it as a script — needs the same
# ordering guarantee. load_dotenv() never overrides an already-set env var,
# so this is a no-op under pytest, which sets DEVCAREER_DB_PATH itself
# before importing this module.
load_dotenv()

from . import database
from .notifier import send_digest_email

REMINDER_WINDOW_DAYS = 3


def _parse_iso_deadline(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def jobs_needing_reminder(today: date | None = None) -> list[dict]:
    today = today or date.today()
    horizon = today + timedelta(days=REMINDER_WINDOW_DAYS)
    due = []
    for job in database.list_jobs():
        deadline = _parse_iso_deadline(job["deadline"])
        if deadline is None or not (today <= deadline <= horizon):
            continue
        if database.reminder_already_sent(job["id"]):
            continue
        due.append(job)
    return due


def run() -> dict:
    """Returns a small summary dict for logging — never raises past here
    regardless of what the email provider does (see notifier.py)."""
    due_jobs = jobs_needing_reminder()
    recipients = database.list_reminder_recipients()
    emails_sent = 0
    total_new_jobs = 0
    for user in recipients:
        new_jobs = (
            database.list_jobs_after_id(user["last_digest_job_id"])
            if user["last_digest_job_id"] is not None
            else []
        )
        total_new_jobs += len(new_jobs)
        if send_digest_email(user["email"], due_jobs, new_jobs):
            emails_sent += 1
        database.mark_digest_sent(user["id"])
    for job in due_jobs:
        database.mark_reminder_sent(job["id"])
    return {
        "due_jobs": len(due_jobs),
        "recipients": len(recipients),
        "new_jobs_total": total_new_jobs,
        "emails_sent": emails_sent,
    }


if __name__ == "__main__":
    database.init_db()
    print(run())
