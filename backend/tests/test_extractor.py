import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.extractor import (  # noqa: E402
    _company_from_domain,
    _normalise_date,
    extract_job_metadata,
)

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
