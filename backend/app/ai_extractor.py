"""AI-assisted job extraction fallback.

Used when the fast local pipeline in extractor.py either can't be trusted
to fetch a page itself (some job boards' robots.txt now explicitly
disallows AI-agent user-agents — see PRD.md Task 2.1) or has empirically
been shown to return wrong-not-just-missing data (Lever/SmartRecruiters
picking up boilerplate text; AshbyHQ rendering nothing server-side).

Tavily does the actual page fetch — it's a third-party extraction service
consumers call by design, not our backend spoofing a browser UA against a
site that has asked AI agents not to crawl it. Groq then reads the
extracted content and pulls out structured fields, which handles messy
pages (wrong JSON-LD block, boilerplate mixed with the real JD) far better
than brittle selectors.

Returns None — never raises — when keys are missing or either API call
fails, so callers in extractor.py can fall back to the local pipeline.
"""

import json
import os

import requests

TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"
GROQ_MODEL = "llama-3.3-70b-versatile"
REQUEST_TIMEOUT = 30
MAX_CONTENT_CHARS = 15000

FIELDS = ("title", "company", "description", "deadline", "location")

EXTRACTION_PROMPT = """You are extracting structured job posting fields from a web page's content.

Return ONLY a JSON object with exactly these keys: title, company, description, deadline, location.

Rules:
- title: the job's title (e.g. "Senior Software Engineer"). Not a page title like "Jobs" or a company tagline.
- company: the hiring company's name only (e.g. "Acme"), not a legal-entity code or "Careers" suffix.
- description: the actual role description / responsibilities / requirements text. Never company
  boilerplate ("we are a mission-driven company..."), EEO/legal disclaimers, cookie notices, or
  navigation text. If the real job description isn't present in the content, return "".
- deadline: the last date to apply, in YYYY-MM-DD format if a specific date is stated. Otherwise "".
- location: the job's location (e.g. "Bangalore, India" or "Remote"). Otherwise "".

If a field genuinely cannot be determined from the content, use "" for it — never guess or fabricate.

Page content:
---
{content}
---

JSON:"""


def _tavily_extract(url: str, api_key: str) -> str | None:
    try:
        response = requests.post(
            TAVILY_EXTRACT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"urls": url, "extract_depth": "advanced", "format": "markdown"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None
    data = response.json()
    results = data.get("results") or []
    if not results:
        return None
    return results[0].get("raw_content") or None


def _groq_extract_fields(content: str, api_key: str) -> dict | None:
    from groq import Groq

    client = Groq(api_key=api_key)
    prompt = EXTRACTION_PROMPT.format(content=content[:MAX_CONTENT_CHARS])
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=2000,
        )
    except Exception:
        return None
    try:
        parsed = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, AttributeError, IndexError):
        return None
    return {field: str(parsed.get(field) or "").strip() for field in FIELDS}


def ai_extract_job_metadata(url: str) -> dict | None:
    tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not tavily_key or not groq_key:
        return None

    content = _tavily_extract(url, tavily_key)
    if not content:
        return None

    return _groq_extract_fields(content, groq_key)
