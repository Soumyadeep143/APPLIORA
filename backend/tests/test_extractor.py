import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.extractor import (  # noqa: E402
    _company_from_domain,
    _normalise_date,
    extract_job_metadata,
)


@pytest.fixture(autouse=True)
def _no_real_ai_calls(monkeypatch):
    """These are unit tests for the local parsing pipeline specifically.
    Without this, a real GROQ_API_KEY/TAVILY_API_KEY loaded into the process
    env by anything else in the test run (e.g. test_api.py importing
    app.main, which calls load_dotenv()) would make AI_PREFERRED_HOSTS tests
    (LinkedIn) silently skip the local pipeline they're meant to exercise
    and hit the real network instead — slow, flaky, and testing the wrong
    code path."""
    monkeypatch.setattr("app.extractor.ai_extractor.ai_extract_job_metadata", lambda url: None)

JSONLD_PAGE = """
<html><head>
<title>Software Engineer II | Microsoft Careers</title>
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "JobPosting",
  "title": "Software Engineer II",
  "hiringOrganization": {"@type": "Organization", "name": "Microsoft"},
  "description": "<p>Join Azure.</p><ul><li>Build services</li><li>Ship code</li></ul>",
  "validThrough": "2026-08-15T23:59:59Z",
  "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress",
    "addressLocality": "Bangalore", "addressCountry": "India"}}
}
</script></head><body><h1>ignored</h1></body></html>
"""

OG_ONLY_PAGE = """
<html><head>
<title>Frontend Developer at Acme | Careers</title>
<meta property="og:title" content="Frontend Developer at Acme" />
<meta property="og:description" content="We need a React developer." />
<meta property="og:site_name" content="Acme Careers" />
</head><body>Last date to apply: 31 August 2026</body></html>
"""


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def _extract_from_html(html, url):
    with patch("app.extractor.requests.get", return_value=FakeResponse(html)):
        return extract_job_metadata(url)


def test_jsonld_extraction():
    result = _extract_from_html(JSONLD_PAGE, "https://jobs.careers.microsoft.com/job/1")
    assert result["title"] == "Software Engineer II"
    assert result["company"] == "Microsoft"
    assert result["deadline"] == "2026-08-15"
    assert "Join Azure." in result["description"]
    assert "Build services" in result["description"]
    assert result["location"] == "Bangalore, India"
    assert result["fetch_ok"] is True


def test_og_fallback_with_text_deadline():
    result = _extract_from_html(OG_ONLY_PAGE, "https://careers.acme.com/jobs/9")
    assert result["title"] == "Frontend Developer"
    assert result["company"] == "Acme"
    assert result["description"] == "We need a React developer."
    assert result["deadline"] == "2026-08-31"


LINKEDIN_PAGE = """
<html><head>
<title>Acme in India hiring Backend Engineer in Pune, India | LinkedIn</title>
<meta property="og:title" content="Acme in India hiring Backend Engineer in Pune, India" />
<meta property="og:description" content="Posted 2 days ago. See this and similar jobs on LinkedIn." />
</head><body>
<h1 class="top-card-layout__title topcard__title">Backend Engineer</h1>
<a class="topcard__org-name-link topcard__flavor--black-link" href="https://in.linkedin.com/company/acme">
  Acme in India
</a>
<span class="topcard__flavor topcard__flavor--bullet">Pune, India</span>
<div class="show-more-less-html__markup">
  <p>Build backend services.</p><p>5+ years experience.</p>
</div>
</body></html>
"""

GREENHOUSE_REMIX_PAGE = """
<html><head>
<title>Job Application for Backend Engineer at Acme</title>
<meta property="og:title" content="Backend Engineer" />
<meta property="og:description" content="Remote - India" />
</head><body>
<h1 class="section-header section-header--large font-primary">Backend Engineer</h1>
<script>
window.__remixContext = {"state":{"loaderData":{"job":{"title":"Backend Engineer",
"company_name":"Acme","job_post_location":"Remote - India",
"content":"<p>Build backend services.</p><p>5+ years experience.</p>"}}}};
</script>
</body></html>
"""


def test_linkedin_topcard_extraction():
    result = _extract_from_html(LINKEDIN_PAGE, "https://www.linkedin.com/jobs/view/123")
    assert result["title"] == "Backend Engineer"
    assert result["company"] == "Acme in India"
    assert result["location"] == "Pune, India"
    assert "Build backend services." in result["description"]
    assert "See this and similar jobs on LinkedIn" not in result["description"]


def test_greenhouse_remix_extraction():
    result = _extract_from_html(
        GREENHOUSE_REMIX_PAGE, "https://job-boards.greenhouse.io/acme/jobs/1"
    )
    assert result["title"] == "Backend Engineer"
    assert result["company"] == "Acme"
    assert result["location"] == "Remote - India"
    assert "Build backend services." in result["description"]
    # og:description ("Remote - India") must not leak into the JD field.
    assert result["description"] != "Remote - India"


def test_fetch_failure_still_returns_domain_company():
    import requests as requests_lib

    with patch(
        "app.extractor.requests.get",
        side_effect=requests_lib.ConnectionError("boom"),
    ):
        result = extract_job_metadata("https://careers.microsoft.com/job/5")
    assert result["fetch_ok"] is False
    assert result["company"] == "Microsoft"
    assert result["notes"]


def test_ai_preferred_host_skips_local_fetch_when_ai_succeeds():
    """For AI_PREFERRED_HOSTS (robots.txt-restricted or empirically unreliable
    sources), a usable AI result must be used as-is and the local
    requests.get fetch must never even be attempted."""
    ai_fields = {
        "title": "Staff Engineer",
        "company": "Acme",
        "description": "Build the core platform.",
        "deadline": "2026-09-01",
        "location": "Remote",
    }
    with patch(
        "app.extractor.ai_extractor.ai_extract_job_metadata", return_value=ai_fields
    ), patch("app.extractor.requests.get") as mock_get:
        result = extract_job_metadata("https://www.linkedin.com/jobs/view/999")

    mock_get.assert_not_called()
    assert result["title"] == "Staff Engineer"
    assert result["company"] == "Acme"
    assert result["deadline"] == "2026-09-01"
    assert result["fetch_ok"] is True
    assert any("AI-assisted" in note for note in result["notes"])


def test_ai_preferred_host_falls_back_to_local_pipeline_when_ai_unusable():
    """If AI extraction is unavailable/fails (returns None, or a dict with
    neither title nor description), a prefer_ai host must still degrade to
    the local pipeline rather than returning nothing."""
    result = _extract_from_html(LINKEDIN_PAGE, "https://www.linkedin.com/jobs/view/123")
    # _no_real_ai_calls autouse fixture makes ai_extract_job_metadata return
    # None, so this must be the local topcard parser, same as
    # test_linkedin_topcard_extraction.
    assert result["title"] == "Backend Engineer"
    assert result["company"] == "Acme in India"


NO_DESCRIPTION_PAGE = """
<html><head><title>Ignored Title</title></head>
<body><h1>Data Engineer</h1></body></html>
"""


def test_ai_supplements_missing_fields_without_clobbering_local_data():
    """For a non-AI_PREFERRED_HOSTS source, AI extraction should only fill in
    fields the local pipeline left empty — never overwrite what local
    parsing already found."""
    ai_fields = {
        "title": "Wrong Title From AI",
        "company": "",
        "description": "The real job description text.",
        "deadline": "",
        "location": "",
    }
    with patch(
        "app.extractor.ai_extractor.ai_extract_job_metadata", return_value=ai_fields
    ), patch("app.extractor.requests.get", return_value=FakeResponse(NO_DESCRIPTION_PAGE)):
        result = extract_job_metadata("https://careers.example.com/job/1")

    # Local <h1> title must win — AI must not clobber a field local already found.
    assert result["title"] == "Data Engineer"
    # Description was empty locally, so AI's is used to fill the gap.
    assert result["description"] == "The real job description text."
    assert any("supplemented" in note for note in result["notes"])


PLACEHOLDER_TITLE_PAGE = """
<html><head><title>Jobs</title></head><body>No h1 here.</body></html>
"""


def test_generic_placeholder_title_not_reported_as_real():
    """Some JS-rendered ATS pages (e.g. AshbyHQ) ship a static <title>Jobs</title>
    shell before client-side hydration. That's worse than no title — it must
    not be reported as the job title."""
    result = _extract_from_html(PLACEHOLDER_TITLE_PAGE, "https://careers.example.com/job/2")
    assert result["title"] == ""


def test_company_from_domain():
    assert _company_from_domain("https://jobs.careers.microsoft.com/x") == "Microsoft"
    assert _company_from_domain("https://careers.zomato.com/openings") == "Zomato"
    # Path-based ATS: employer is a URL segment, not part of the host.
    assert _company_from_domain("https://boards.greenhouse.io/acme/jobs/1") == "Acme"
    assert _company_from_domain("https://job-boards.greenhouse.io/acme-labs/jobs/1") == "Acme Labs"
    assert _company_from_domain("https://jobs.lever.co/notion/abc-123") == "Notion"
    # Subdomain-based ATS: employer IS the subdomain even though the
    # platform's own name ("myworkdayjobs") also appears in the host.
    assert (
        _company_from_domain("https://acme.wd5.myworkdayjobs.com/en-US/External/job/1")
        == "Acme"
    )


def test_normalise_date():
    assert _normalise_date("2026-08-15T23:59:59Z") == "2026-08-15"
    assert _normalise_date("August 15, 2026") == "2026-08-15"
    assert _normalise_date("15 Aug 2026") == "2026-08-15"
    assert _normalise_date("15th August 2026") == "2026-08-15"
    assert _normalise_date("someday soon") == "someday soon"
