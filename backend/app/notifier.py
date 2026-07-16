"""Digest email delivery via Resend — deadline reminders (PRD.md Task 4.1)
and "what friends shared" (Task 4.2) share one opt-in and one daily email,
per user direction, rather than two separate messages/toggles.

Same graceful-degrade shape as ai_extractor.py: returns False and never
raises when RESEND_API_KEY is missing or the API call fails, so
reminders.py can still do its bookkeeping (advancing cursors) even when
delivery didn't happen — a bad key or a Resend outage shouldn't turn into a
daily retry-storm.

Uses a plain requests.post call rather than the `resend` SDK — Tavily is
integrated the same way elsewhere in this codebase; no need for a new
dependency to POST one JSON body.
"""

import os

import requests

RESEND_API_URL = "https://api.resend.com/emails"
REQUEST_TIMEOUT = 15

# Resend's shared sandbox sender — works without verifying your own domain
# (see README.md's Deploy section). Swap for a verified `from` address once
# you have one.
DEFAULT_FROM = "DevCareer <onboarding@resend.dev>"


def _job_line(job: dict) -> str:
    line = f"- {job['title']}"
    if job.get("company"):
        line += f" at {job['company']}"
    if job.get("deadline"):
        line += f" — apply by {job['deadline']}"
    return line


def _format_email(due_jobs: list[dict], new_jobs: list[dict]) -> tuple[str, str]:
    subject_parts = []
    body_sections = []
    if due_jobs:
        subject_parts.append(f"{len(due_jobs)} closing soon")
        body_sections.append(
            "Closing soon:\n" + "\n".join(_job_line(job) for job in due_jobs)
        )
    if new_jobs:
        subject_parts.append(f"{len(new_jobs)} new")
        body_sections.append(
            "New jobs your friends shared:\n" + "\n".join(_job_line(job) for job in new_jobs)
        )
    subject = "DevCareer: " + ", ".join(subject_parts)
    body = "\n\n".join(body_sections)
    return subject, body


def send_digest_email(to_email: str, due_jobs: list[dict], new_jobs: list[dict]) -> bool:
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key or not to_email or not (due_jobs or new_jobs):
        return False
    subject, body = _format_email(due_jobs, new_jobs)
    try:
        response = requests.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"from": DEFAULT_FROM, "to": [to_email], "subject": subject, "text": body},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException:
        return False
    return True
