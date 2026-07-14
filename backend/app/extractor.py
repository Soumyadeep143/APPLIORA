"""Job metadata extraction from a shared job URL.

Extraction strategy (best source wins, field by field):
1. schema.org JobPosting JSON-LD  — used by Microsoft Careers, LinkedIn,
   Greenhouse, Lever, Workday, Naukri and most serious job boards.
   Gives title, hiringOrganization.name, description and validThrough
   (the last date to apply).
2. OpenGraph / Twitter meta tags   — og:title, og:description, og:site_name.
3. Plain HTML                      — <title>, meta description, <h1>.
4. Heuristics                      — company from the domain or from
   "Role at Company" / "Role - Company | Careers" title patterns,
   deadline from "apply by ..." phrases in the page text.

Every field is returned even when empty so the frontend can let the
user fill in whatever we could not detect.
"""

import html as html_lib
import json
import re
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

FETCH_TIMEOUT = 15
MAX_DESCRIPTION_CHARS = 5000

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Well-known career domains -> company names.
KNOWN_COMPANY_DOMAINS = {
    "microsoft.com": "Microsoft",
    "google.com": "Google",
    "amazon.jobs": "Amazon",
    "amazon.com": "Amazon",
    "apple.com": "Apple",
    "meta.com": "Meta",
    "metacareers.com": "Meta",
    "netflix.com": "Netflix",
    "nvidia.com": "NVIDIA",
    "ibm.com": "IBM",
    "oracle.com": "Oracle",
    "salesforce.com": "Salesforce",
    "adobe.com": "Adobe",
    "intel.com": "Intel",
    "uber.com": "Uber",
    "airbnb.com": "Airbnb",
    "stripe.com": "Stripe",
    "atlassian.com": "Atlassian",
    "flipkart.com": "Flipkart",
    "tcs.com": "TCS",
    "infosys.com": "Infosys",
    "wipro.com": "Wipro",
    "accenture.com": "Accenture",
    "deloitte.com": "Deloitte",
    "goldmansachs.com": "Goldman Sachs",
    "jpmorganchase.com": "JPMorgan Chase",
    "morganstanley.com": "Morgan Stanley",
}

# Job-board hosts whose name should never be reported as the company.
AGGREGATOR_HOSTS = (
    "linkedin.com",
    "indeed.com",
    "naukri.com",
    "glassdoor.com",
    "monster.com",
    "ziprecruiter.com",
    "wellfound.com",
    "instahyre.com",
    "foundit.in",
    "greenhouse.io",
    "lever.co",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "ashbyhq.com",
)


def extract_job_metadata(url: str) -> dict:
    """Fetch *url* and pull out job fields. Never raises on parse issues —
    returns whatever could be found plus a note about the sources used."""
    result = {
        "url": url,
        "title": "",
        "company": "",
        "description": "",
        "deadline": "",
        "location": "",
        "source": urlparse(url).netloc,
        "fetch_ok": False,
        "notes": [],
    }

    try:
        response = requests.get(
            url, headers=BROWSER_HEADERS, timeout=FETCH_TIMEOUT, allow_redirects=True
        )
        response.raise_for_status()
        page_html = response.text
        result["fetch_ok"] = True
    except requests.RequestException as exc:
        result["notes"].append(f"Could not fetch the page ({type(exc).__name__}).")
        _apply_fallbacks(result)
        return result

    soup = BeautifulSoup(page_html, "html.parser")

    posting = _find_job_posting_jsonld(soup)
    if posting:
        _apply_jsonld(result, posting)
        result["notes"].append("Structured JobPosting data found on the page.")

    _apply_meta_tags(result, soup)
    _apply_plain_html(result, soup)
    _apply_text_heuristics(result, soup)
    _apply_fallbacks(result)
    return result


# --------------------------------------------------------------------------
# JSON-LD (schema.org JobPosting)
# --------------------------------------------------------------------------

def _find_job_posting_jsonld(soup: BeautifulSoup) -> dict | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, TypeError):
            continue
        posting = _pick_job_posting(data)
        if posting:
            return posting
    return None


def _pick_job_posting(data) -> dict | None:
    """JSON-LD can be a dict, a list, or nested under @graph."""
    if isinstance(data, list):
        for item in data:
            found = _pick_job_posting(item)
            if found:
                return found
        return None
    if isinstance(data, dict):
        types = data.get("@type", "")
        if isinstance(types, list):
            is_posting = "JobPosting" in types
        else:
            is_posting = types == "JobPosting"
        if is_posting:
            return data
        if "@graph" in data:
            return _pick_job_posting(data["@graph"])
    return None


def _apply_jsonld(result: dict, posting: dict) -> None:
    if posting.get("title"):
        result["title"] = _clean_text(str(posting["title"]))

    org = posting.get("hiringOrganization")
    if isinstance(org, dict) and org.get("name"):
        result["company"] = _clean_text(str(org["name"]))
    elif isinstance(org, str):
        result["company"] = _clean_text(org)

    if posting.get("description"):
        result["description"] = _html_to_text(str(posting["description"]))

    valid_through = posting.get("validThrough") or posting.get("applicationDeadline")
    if valid_through:
        result["deadline"] = _normalise_date(str(valid_through))

    location = posting.get("jobLocation")
    loc_text = _jsonld_location(location)
    if loc_text:
        result["location"] = loc_text


def _jsonld_location(location) -> str:
    if isinstance(location, list):
        parts = [_jsonld_location(item) for item in location]
        parts = [p for p in parts if p]
        return "; ".join(dict.fromkeys(parts))[:200]
    if isinstance(location, dict):
        address = location.get("address")
        if isinstance(address, dict):
            bits = [
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]
            bits = [str(b) for b in bits if b and isinstance(b, (str, int))]
            return ", ".join(bits)
        if isinstance(address, str):
            return address
        if location.get("name"):
            return str(location["name"])
    if isinstance(location, str):
        return location
    return ""


# --------------------------------------------------------------------------
# Meta tags / plain HTML
# --------------------------------------------------------------------------

def _meta_content(soup: BeautifulSoup, **attrs) -> str:
    tag = soup.find("meta", attrs=attrs)
    if tag and tag.get("content"):
        return _clean_text(tag["content"])
    return ""


def _apply_meta_tags(result: dict, soup: BeautifulSoup) -> None:
    if not result["title"]:
        result["title"] = _meta_content(soup, property="og:title") or _meta_content(
            soup, name="twitter:title"
        )
    if not result["description"]:
        result["description"] = (
            _meta_content(soup, property="og:description")
            or _meta_content(soup, name="twitter:description")
            or _meta_content(soup, name="description")
        )
    if not result["company"]:
        site_name = _meta_content(soup, property="og:site_name")
        if site_name and not _is_aggregator_name(site_name):
            result["company"] = _strip_careers_suffix(site_name)


def _apply_plain_html(result: dict, soup: BeautifulSoup) -> None:
    if not result["title"]:
        h1 = soup.find("h1")
        if h1:
            result["title"] = _clean_text(h1.get_text())
    if not result["title"] and soup.title:
        result["title"] = _clean_text(soup.title.get_text())


# --------------------------------------------------------------------------
# Heuristics
# --------------------------------------------------------------------------

TITLE_SPLIT_RE = re.compile(r"\s+[|–—-]\s+| at | @ ", re.IGNORECASE)
DEADLINE_TEXT_RE = re.compile(
    r"(?:apply(?:\s+on\s+or)?\s+by|last\s+date(?:\s+to\s+apply)?|"
    r"application\s+deadline|closing\s+date|applications?\s+close[sd]?(?:\s+on)?)"
    r"\s*:?\s*([A-Za-z0-9,\s/.-]{4,40}?\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.IGNORECASE,
)


def _apply_text_heuristics(result: dict, soup: BeautifulSoup) -> None:
    # Company already known: trim "Role at Acme | Careers" down to "Role".
    if result["title"] and result["company"]:
        company = re.escape(result["company"])
        result["title"] = re.sub(
            rf"(\s+[|–—-]\s+|\s+at\s+|\s+@\s+){company}"
            rf"(\s*(\s+[|–—-]\s+)?(careers?|jobs?))?\s*$",
            "",
            result["title"],
            flags=re.IGNORECASE,
        ).strip() or result["title"]

    # "Senior Engineer - Microsoft | Careers" style titles.
    if result["title"] and not result["company"]:
        parts = [p.strip() for p in TITLE_SPLIT_RE.split(result["title"]) if p.strip()]
        if len(parts) >= 2:
            candidate = parts[-1]
            if (
                len(candidate) <= 40
                and not _is_aggregator_name(candidate)
                and candidate.lower() not in ("careers", "jobs", "job details")
            ):
                result["company"] = _strip_careers_suffix(candidate)
            result["title"] = parts[0]

    if not result["deadline"]:
        text = soup.get_text(" ", strip=True)[:20000]
        match = DEADLINE_TEXT_RE.search(text)
        if match:
            result["deadline"] = _normalise_date(match.group(1).strip())


def _apply_fallbacks(result: dict) -> None:
    if not result["company"]:
        result["company"] = _company_from_domain(result["url"])
    if result["description"]:
        result["description"] = result["description"][:MAX_DESCRIPTION_CHARS]
    if not result["fetch_ok"] and not result["notes"]:
        result["notes"].append("Fill in the details manually.")
    if result["fetch_ok"] and not (result["title"] or result["description"]):
        result["notes"].append(
            "The page did not expose readable job data (it may load via "
            "JavaScript or block bots) — please fill the fields in manually."
        )


def _company_from_domain(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    for domain, name in KNOWN_COMPANY_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return name
    if _is_aggregator_name(host):
        return ""
    # careers.acme.com / acme.wd5.myworkdayjobs.com -> Acme
    parts = host.split(".")
    for part in parts:
        if part not in ("careers", "jobs", "apply", "www", "co", "com", "in", "io"):
            return part.capitalize()
    return ""


def _is_aggregator_name(name: str) -> bool:
    lowered = name.lower()
    return any(host.split(".")[0] in lowered for host in AGGREGATOR_HOSTS)


def _strip_careers_suffix(name: str) -> str:
    return re.sub(
        r"\s*(careers?|jobs?|hiring|talent)\s*$", "", name, flags=re.IGNORECASE
    ).strip() or name


# --------------------------------------------------------------------------
# Text utilities
# --------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


def _html_to_text(fragment: str) -> str:
    """JobPosting descriptions are usually HTML — flatten to readable text."""
    soup = BeautifulSoup(html_lib.unescape(fragment), "html.parser")
    for br in soup.find_all(["br", "p", "li", "div"]):
        br.append("\n")
    text = soup.get_text()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d %Y",
)


def _normalise_date(raw: str) -> str:
    """Return ISO yyyy-mm-dd when parseable, else the raw string."""
    raw = raw.strip().rstrip(".")
    iso_match = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if iso_match:
        return iso_match.group(1)
    cleaned = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", raw, flags=re.IGNORECASE)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw
