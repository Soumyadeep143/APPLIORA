import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.extractor import (  # noqa: E402
    _company_from_domain,
    _normalise_date,
    extract_job_metadata,
    extract_job_metadata_from_text,
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


def test_field_confidence_high_for_jsonld():
    """Task 2.3: every field sourced from structured JobPosting JSON-LD is
    'high' confidence — nothing here is a guess."""
    result = _extract_from_html(JSONLD_PAGE, "https://jobs.careers.microsoft.com/job/1")
    for field in ("title", "company", "description", "deadline", "location"):
        assert result["field_confidence"][field] == "high"


def test_field_confidence_medium_for_meta_tags_low_for_text_deadline():
    result = _extract_from_html(OG_ONLY_PAGE, "https://careers.acme.com/jobs/9")
    assert result["field_confidence"]["title"] == "medium"
    assert result["field_confidence"]["description"] == "medium"
    assert result["field_confidence"]["company"] == "medium"
    # Deadline comes from a free-text regex match, not a structured field.
    assert result["field_confidence"]["deadline"] == "low"


TITLE_SPLIT_COMPANY_PAGE = """
<html><head>
<title>Backend Developer - Zeta Corp</title>
<meta property="og:title" content="Backend Developer - Zeta Corp" />
<meta property="og:description" content="Build APIs." />
</head><body>Apply by 2026-10-01</body></html>
"""


def test_field_confidence_low_for_title_split_company():
    """When company isn't in any meta tag and has to be split off the title
    string itself ("Role - Company"), that's a guess, not a found field."""
    result = _extract_from_html(TITLE_SPLIT_COMPANY_PAGE, "https://jobs.example.com/1")
    assert result["title"] == "Backend Developer"
    assert result["company"] == "Zeta Corp"
    assert result["field_confidence"]["company"] == "low"


COMPOUND_HYPHENATED_TITLE_PAGE = """
<html><head>
<title>Technology & Transformation - Engineering - Senior Consultant - Python Data Engineer - Bangalore</title>
<meta property="og:title" content="Technology & Transformation - Engineering - Senior Consultant - Python Data Engineer - Bangalore" />
<meta property="og:description" content="Join our Technology & Transformation practice." />
</head><body>No deadline text here.</body></html>
"""


def test_multi_segment_title_not_mistaken_for_title_dash_company():
    """Real bug (found live against southasiacareers.deloitte.com, 2026-07-16):
    a title with several meaningful hyphen-separated segments — department,
    level, specialisation, location — isn't the "Role - Company" shape the
    text-split heuristic targets. Blindly taking the last segment as company
    picked up "Bangalore" (a location); blindly taking the first segment as
    the whole title threw away the rest of the real title. Splitting should
    only fire on an exact two-part shape; here it should leave both fields
    alone and let the domain-based fallback (deloitte.com -> "Deloitte")
    supply the company instead."""
    result = _extract_from_html(
        COMPOUND_HYPHENATED_TITLE_PAGE,
        "https://southasiacareers.deloitte.com/job/Bengaluru-Technology-1/1",
    )
    assert result["title"] == (
        "Technology & Transformation - Engineering - Senior Consultant - "
        "Python Data Engineer - Bangalore"
    )
    assert result["company"] == "Deloitte"


def test_field_confidence_low_for_domain_fallback_company():
    import requests as requests_lib

    with patch(
        "app.extractor.requests.get",
        side_effect=requests_lib.ConnectionError("boom"),
    ):
        result = extract_job_metadata("https://careers.microsoft.com/job/5")
    assert result["company"] == "Microsoft"
    assert result["field_confidence"]["company"] == "low"


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
    # AI is the deliberately chosen primary source for these hosts — high confidence.
    assert result["field_confidence"]["title"] == "high"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/jobs/view/999",
        "https://www.naukri.com/job-listings-staff-engineer-123",
        "https://www.indeed.com/viewjob?jk=abc123",
        "https://in.indeed.com/viewjob?jk=abc123",
        "https://jobs.lever.co/notion/abc-123",
        "https://jobs.ashbyhq.com/acme/def-456",
        "https://www.smartrecruiters.com/Acme/789-staff-engineer",
        "https://jobs.smartrecruiters.com/Acme/789-staff-engineer",
    ],
)
def test_ai_preferred_hosts_all_route_through_ai_extraction(url):
    """BACKEND_VERIFICATION_ROADMAP.md flagged these five hosts (LinkedIn
    already had a dedicated test) as having zero regression coverage for the
    prefer_ai routing decision itself — a typo'd or accidentally-removed
    entry in AI_PREFERRED_HOSTS would silently revert that host to the local
    pipeline, which Task 2.1 found to be either robots.txt-violating
    (Naukri/Indeed) or confidently wrong/empty (Lever/AshbyHQ/SmartRecruiters),
    with nothing catching it. This asserts every host (plus a couple of
    realistic www./subdomain variants) still takes the AI-first path and
    never even attempts the local requests.get fetch."""
    ai_fields = {
        "title": "Staff Engineer",
        "company": "Acme",
        "description": "Build the core platform.",
        "deadline": "",
        "location": "",
    }
    with patch(
        "app.extractor.ai_extractor.ai_extract_job_metadata", return_value=ai_fields
    ), patch("app.extractor.requests.get") as mock_get:
        result = extract_job_metadata(url)

    mock_get.assert_not_called()
    assert result["title"] == "Staff Engineer"
    assert result["fetch_ok"] is True
    assert result["field_confidence"]["title"] == "high"


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
    # Local <h1> title keeps its own (medium) confidence; AI-supplemented
    # description is a gap-fill, not the primary source, so medium too.
    assert result["field_confidence"]["title"] == "medium"
    assert result["field_confidence"]["description"] == "medium"


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


PASTED_EMAIL_TEXT = """Role: Senior Backend Engineer at Acme Corp

Hey team, forwarding this along, looks like a good fit.

We're looking for a Senior Backend Engineer to join our platform team.
You'll work on distributed systems at scale.

Apply by: 15 September 2026
"""


def test_extract_from_pasted_text():
    """Task 2.2: no URL at all, e.g. an email/Slack forward — must reuse
    the same title/company splitting and deadline heuristics as the HTML
    path, without ever touching the network."""
    result = extract_job_metadata_from_text(PASTED_EMAIL_TEXT)
    assert result["url"] == ""
    assert result["fetch_ok"] is True
    assert result["title"] == "Senior Backend Engineer"
    assert result["company"] == "Acme Corp"
    assert result["deadline"] == "2026-09-15"
    assert "distributed systems" in result["description"]
    # Labeled "Role:" line is a stronger signal than a blind first-line
    # guess -> medium; company/deadline are still guessed off free text -> low.
    assert result["field_confidence"]["title"] == "medium"
    assert result["field_confidence"]["company"] == "low"
    assert result["field_confidence"]["deadline"] == "low"


def test_extract_from_pasted_text_skips_forwarded_subject_line():
    """Real forwarded emails lead with 'Fwd: ...' or other preamble before
    the actual role line — found via live-checking this exact scenario
    with a real forwarded-email-shaped paste. The labeled 'Role:' line
    must win over the literal first line."""
    text = (
        "Fwd: Job opportunity\n\n"
        "Role: Product Manager at Notion\n\n"
        "We are hiring a Product Manager to lead our growth team.\n\n"
        "Last date to apply: 30 September 2026"
    )
    result = extract_job_metadata_from_text(text)
    assert result["title"] == "Product Manager"
    assert result["company"] == "Notion"
    assert result["deadline"] == "2026-09-30"


def test_extract_from_pasted_text_without_structure_degrades_gracefully():
    result = extract_job_metadata_from_text(
        "just some random forwarded text with no clear job info"
    )
    assert result["fetch_ok"] is True
    assert result["title"]  # best-effort: first line, not empty/crashed
    assert result["company"] == ""
    # No "Role:" label found -> bare first-line guess, lowest confidence tier.
    assert result["field_confidence"]["title"] == "low"


CRED_HIRING_POST = """🚀 CRED Mass Hiring | Agentic Engineer Interns

🏢 Company: CRED
💼 Role: Agentic Engineer Interns
📍 Location: Bangalore,India

🔥 Mass Hiring for students passionate about AI Agents, LLMs, and Agentic AI.

💰 Competitive Stipend
🎯 PPO Offer after successful internship based on performance.

📩 How to Apply: Send your Resume + GitHub Project Links
📝 Email Subject: Intern
📧 Send Email: Prakash.Iyer@cred.club
"""


def test_extract_from_pasted_text_detects_apply_email_separately_from_url():
    """Real user-provided example: a forwarded hiring post with no
    application URL at all, only an email address to send a resume to.
    Task 2.4: url and apply_email are independent fields — a post can have
    a link, an email, or both — so this fills apply_email (plus the post's
    own 'Email Subject:' line) and leaves url genuinely empty rather than
    smuggling a mailto: into the url field."""
    result = extract_job_metadata_from_text(CRED_HIRING_POST)
    assert result["url"] == ""
    assert result["apply_email"] == "Prakash.Iyer@cred.club"
    assert result["apply_email_subject"] == "Intern"
    # Also regression-covers the emoji-bulleted "💼 Role: ..." / "🏢 Company: ..."
    # / "📍 Location: ..." label format itself, found via this same real
    # example — LEADING_LABEL_RE previously required the label at position 0,
    # so a leading emoji made it fall through to the pipe-split fallback and
    # mis-parse "Agentic Engineer Interns" as the *company*, not the title.
    assert result["title"] == "Agentic Engineer Interns"
    assert result["company"] == "CRED"
    assert result["location"] == "Bangalore,India"
    assert any("apply-by-email" in note for note in result["notes"])


def test_pasted_text_apply_email_without_subject_line():
    text = (
        "Role: Data Analyst at Acme\n\n"
        "Interested candidates can email their resume to jobs@acme.com to apply.\n"
    )
    result = extract_job_metadata_from_text(text)
    assert result["apply_email"] == "jobs@acme.com"
    assert result["apply_email_subject"] == ""
    assert result["url"] == ""


def test_pasted_text_incidental_email_without_apply_keyword_is_ignored():
    """An email mentioned for an unrelated reason (no apply/send/resume/
    contact keyword on that line) must not be mistaken for the application
    address — avoids a false positive misreporting apply_email."""
    text = (
        "Role: Data Analyst at Acme\n\n"
        "Reference ID: analyst-2026@internal-tracking.acme.com\n"
        "We are hiring a data analyst for our platform team."
    )
    result = extract_job_metadata_from_text(text)
    assert result["apply_email"] == ""


def test_pasted_text_can_have_both_a_real_url_and_an_apply_email():
    """"Or both" (Task 2.4): a post naming a real link AND an email address
    should surface both independently, not force a choice between them."""
    text = (
        "Role: Data Analyst at Acme\n\n"
        "Apply here: https://acme.com/careers/data-analyst\n"
        "Or send your resume by email to hr@acme.com\n"
    )
    result = extract_job_metadata_from_text(text)
    assert result["url"] == "https://acme.com/careers/data-analyst"
    assert result["apply_email"] == "hr@acme.com"


def test_normalise_date():
    assert _normalise_date("2026-08-15T23:59:59Z") == "2026-08-15"
    assert _normalise_date("August 15, 2026") == "2026-08-15"
    assert _normalise_date("15 Aug 2026") == "2026-08-15"
    assert _normalise_date("15th August 2026") == "2026-08-15"
    assert _normalise_date("someday soon") == "someday soon"
