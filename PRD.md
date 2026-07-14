# Appliora — Product Requirements Document

Spec-driven development doc. Work is organized as:

```
Phase  (a shippable slice of product value)
  Task   (one coherent unit of engineering work inside the phase)
    Process  (ordered steps to actually do the task)
```

Rules for whoever (human or agent) is executing this doc:

- Work phases **in order**. Within a phase, tasks may be done in any order
  unless a task says otherwise.
- A task is not "Done" until its Acceptance Criteria are all true AND
  `backend/tests` passes AND, if the task touches the extractor, it has been
  checked against at least one **live** URL of the relevant type (not just a
  mocked fixture) — see `BACKEND_VERIFICATION_ROADMAP.md`.
- When you finish a task, flip its `Status:` line and check off its
  processes in this file, in the same change that implements it. This file
  is the live source of truth, not a snapshot.
- If a task's premise turns out to be wrong once you're in the code, stop
  and say so rather than forcing the original plan.

Status legend: `DONE` · `IN PROGRESS` · `NEXT` · `PLANNED`

---

## Phase 1 — Foundation (DONE)

**Goal:** A friend can paste a job link, get an auto-filled, editable job
card, and share it to a board other friends can browse and search.

### Task 1.1 — Backend skeleton
Status: DONE
Processes:
- [x] FastAPI app (`backend/app/main.py`) with CORS open for the frontend origin.
- [x] SQLite storage (`backend/app/database.py`), single `jobs` table.
- [x] `/health` endpoint.

### Task 1.2 — Job board CRUD
Status: DONE
Processes:
- [x] `POST /api/jobs` — save a job (validated via Pydantic `JobCreate`).
- [x] `GET /api/jobs?search=` — list jobs, newest first, `LIKE`-search across
      title/company/description/shared_by/location.
- [x] `GET /api/jobs/{id}` — fetch one.
- [x] `DELETE /api/jobs/{id}` — remove one.

### Task 1.3 — Auto-fetch extraction engine
Status: DONE
Processes:
- [x] `POST /api/extract` fetches a URL and returns best-effort fields;
      never raises on a bad/unreachable page — falls back to "fill in
      manually" with a note explaining why.
- [x] Extraction priority, field by field: schema.org `JobPosting` JSON-LD →
      OpenGraph/Twitter meta → plain `<title>`/`<h1>` → text heuristics
      (title-splitting, "apply by ..." deadline regex, domain-based company).
- [x] `backend/app/extractor.py` is the single source of truth for this
      logic; `backend/tests/test_extractor.py` covers it with mocked HTML.

### Task 1.4 — Share UI
Status: DONE
Processes:
- [x] React/Vite frontend (`frontend/src/App.jsx`): paste-link box → "Fetch
      details" → editable draft form (title required, company/deadline/
      location/description optional) → "Share job".
- [x] Feed of shared jobs with search, relative timestamps, deadline
      urgency badges (`ok`/`soon`/`expired`), delete.
- [x] "Applio" mascot gives state-based feedback (searching/found/sad/happy).

### Task 1.5 — Extraction hardening: LinkedIn, Greenhouse, Workday
Status: DONE — 2026-07-15
Why: live-tested against real URLs and found three real gaps beyond what the
mocked fixtures caught: (1) LinkedIn's `og:title` is a mangled "Company
hiring Title in Place" SEO string and `og:description` is truncated
boilerplate, not a JD; (2) Greenhouse's newer `job-boards.greenhouse.io`
Remix-based template ships no JSON-LD and no `og:site_name`, and its
`og:description` is the *location*, not the description; (3) Workday's
per-tenant subdomain (`acme.wd5.myworkdayjobs.com`) was being blanked to ""
because "myworkdayjobs" also matches the aggregator-name filter meant for
shared multi-tenant hosts.
Processes:
- [x] Add `_apply_linkedin` — reads `topcard__title`, `topcard__org-name-link`,
      `topcard__flavor--bullet`, `show-more-less-html__markup` directly.
- [x] Add `_apply_greenhouse_embedded_json` — regex-extracts
      `company_name` / `title` / `job_post_location` / `content` out of the
      embedded `window.__remixContext` JSON blob.
- [x] Fix `_company_from_domain`: add `PATH_BASED_ATS_HOSTS` (Greenhouse,
      Lever, AshbyHQ — employer is a URL path segment) and
      `SUBDOMAIN_BASED_ATS_SUFFIXES` (Workday — employer IS the subdomain
      despite the platform name also appearing in the host).
- [x] Regression + new-case tests in `test_extractor.py`; verified live
      against a real `job-boards.greenhouse.io` posting and a real
      `linkedin.com/jobs/view/...` posting.

---

## Phase 2 — Extraction Coverage (NEXT)

**Goal:** "Paste basically any job-related link or text and get a usable
title + company at minimum" — the bar the product promises on the tin.

### Task 2.1 — Verify + fix remaining major ATS/job-board sources live
Status: DONE — 2026-07-15
Why: Phase 1 only live-tested LinkedIn and Greenhouse. Indeed, Naukri,
SmartRecruiters and AshbyHQ are named in `AGGREGATOR_HOSTS` /
`KNOWN_COMPANY_DOMAINS` but had never been checked against a real page.

Live-testing turned up a real policy question, not just parsing bugs:
Naukri's and Indeed's `robots.txt` explicitly disallow AI-agent
user-agents (`Claude-User`, `claudebot`, `GPTBot`, etc.) site-wide —
LinkedIn disallows `ClaudeBot` specifically. Fetching those pages with our
backend's own generic-browser-UA `requests.get`, even for a single
user-pasted URL, means *we* are the one crawling a site that has named
AI agents as unwelcome. Resolution (user-directed): route those hosts
through Tavily (a third-party extraction API — Tavily does the actual
fetch, not our backend) instead of fetching them ourselves.

That same investigation found jobs.lever.co and smartrecruiters.com
returning confidently-wrong data locally (boilerplate/CTA text picked up
instead of the real JD — worse than Task 1.5's bugs, since these aren't
empty fields a human would notice need filling in), and jobs.ashbyhq.com
returning nothing (client-rendered, no content in the raw HTML at all).

Processes:
- [x] Live-tested Lever, AshbyHQ, SmartRecruiters, LinkedIn, Indeed,
      Naukri, and Workday (a user-provided real Agilent posting) against
      the live pipeline.
- [x] Built `backend/app/ai_extractor.py`: Tavily `/extract` fetches the
      page, Groq (`llama-3.3-70b-versatile`, JSON mode) reads it for
      structured title/company/description/deadline/location — handles
      messy content (wrong JSON-LD block, boilerplate mixed with real JD)
      far better than brittle selectors. Returns `None` on any failure or
      missing API keys; never raises.
- [x] Added `AI_PREFERRED_HOSTS` in `extractor.py`: linkedin.com,
      naukri.com, indeed.com (robots.txt-restricted), jobs.lever.co,
      jobs.ashbyhq.com, smartrecruiters.com (empirically unreliable
      locally). These try AI extraction *first*; if AI is unavailable or
      returns nothing usable, they degrade to the local pipeline rather
      than failing outright.
- [x] For all other hosts, AI extraction runs as a *fallback* only when
      local title/description come back empty — never overwrites fields
      the local pipeline already found (see
      `test_ai_supplements_missing_fields_without_clobbering_local_data`).
- [x] Fixed a real bug found along the way: `_apply_plain_html`'s
      `<title>` fallback was reporting AshbyHQ's static pre-hydration
      shell title ("Jobs") as the job title. Added
      `GENERIC_PLACEHOLDER_TITLES` to reject known-generic shell titles —
      empty is better than confidently wrong.
- [x] `GROQ_API_KEY` / `TAVILY_API_KEY` in `backend/.env` (gitignored,
      loaded via `load_dotenv()` in `main.py`). Not present → AI paths
      silently no-op, local pipeline still works exactly as before.
- [x] Fixture-based regression tests added (not just live verification)
      for: AI-preferred-host success path (local fetch never attempted),
      AI-preferred-host degrading to local when AI unusable, AI
      supplementing without clobbering local data, and the placeholder-
      title fix. All hermetic — an autouse fixture in `test_extractor.py`
      blocks real AI calls regardless of what's in the process env, after
      a real bug where `test_api.py` importing `app.main` leaked real API
      keys into `test_extractor.py`'s tests via shared process env,
      making a "unit" test silently hit the real network.
- [x] Updated the extraction-order docstring in `extractor.py` (now lists
      AI-assisted extraction as strategy 5).

Known unfixable limitation: jobs.ashbyhq.com fails for *both* the local
fetch and Tavily (`"error": "Failed to fetch url"` from Tavily on two
different companies' postings) — Ashby's bot-detection blocks Tavily's
crawler too. No further fix without a full headless-browser fetch
(Playwright/Puppeteer in production), which is out of scope. Degrades
gracefully to an empty, honestly-blank result rather than wrong data.

### Task 2.2 — Accept pasted text, not just a URL
Status: PLANNED
Why: user-requested — "might be a mail or something that is job related",
i.e. someone forwards a job description by email/Slack with no clean
scrapeable URL, or the URL is login-walled (see the Google Forms case
investigated 2026-07-15: a form requiring Google sign-in can never be
fetched by any client, bot or browser).
Processes:
- [ ] Backend: `POST /api/extract` accepts either `url` or `text`. If
      `text`, skip the network fetch and run the existing heuristics
      (`_apply_text_heuristics`, `DEADLINE_TEXT_RE`, title/company
      splitting) directly against the pasted text.
- [ ] Frontend: the paste box accepts non-URL input; only show "Fetch
      details" as a network fetch when the input parses as `http(s)://...`,
      otherwise show "Parse text" and skip the URL-format validator that
      currently rejects non-URLs outright (`frontend/src/App.jsx` uses
      `type="url" required`; `ExtractRequest`/`JobCreate` in `main.py` both
      hard-require an `http(s)` URL for `url` — needs a schema change, e.g.
      `url` becomes optional but at least one of `url`/`text` is required).
- [ ] `JobCreate.url` either becomes optional (job saved without a source
      link) or the UI requires the user to also paste the real apply link
      before sharing — decide which; a shared job with no link to apply to
      is low value, so leaning toward requiring a URL at *share* time even
      if the *fetch* step accepted freeform text.
- [ ] Tests: pasted-email-style fixture with no HTML, just plain text
      containing "Role: ... at ... Apply by ...".

### Task 2.3 — Surface extraction confidence in the UI
Status: PLANNED
Why: right now `notes` is the only signal a field was guessed vs. found
authoritatively; users can't tell "we're confident" from "we guessed this
from the URL."
Processes:
- [ ] Backend: extractor already knows *which* strategy filled each field
      internally (JSON-LD vs. meta vs. heuristic vs. domain-fallback) —
      expose that per-field, not just as a flat `notes` list.
- [ ] Frontend: lightly flag low-confidence fields (e.g. company guessed
      from domain) in the draft form so the user knows to double check.

---

## Phase 3 — Accounts & Collaboration

**Goal:** Move from "type your name each time" to real identity and
friend-scoped sharing, without over-building an auth system this product
doesn't need yet.

### Task 3.1 — Replace free-text name with real identity
Status: PLANNED
Processes:
- [ ] Decide auth approach (magic link vs. OAuth vs. simple invite code) —
      this is a product decision, raise it before building.
- [ ] `shared_by` becomes a foreign key to a `users` table instead of a
      free-text field with a client-side `localStorage` default.
- [ ] Migrate existing `jobs.shared_by` text values (best-effort match, or
      leave as a legacy display name for pre-migration rows).

### Task 3.2 — Friend groups / private boards
Status: PLANNED
Processes:
- [ ] `groups` table + membership; a job belongs to a group instead of one
      global board.
- [ ] `GET /api/jobs` scoped by group membership.
- [ ] Invite flow (link or code) to join a group.

### Task 3.3 — Reactions / comments on a shared job
Status: PLANNED
Processes:
- [ ] `job_reactions` and/or `job_comments` tables.
- [ ] Minimal UI: emoji reaction row + optional comment thread per job card.

---

## Phase 4 — Notifications & Reminders

**Goal:** Appliora proactively reminds people about deadlines instead of
relying on them to re-check the board.

### Task 4.1 — Deadline reminders
Status: PLANNED
Processes:
- [ ] Background job (cron or scheduled task) that scans `jobs.deadline`
      daily and finds jobs closing in N days.
- [ ] Delivery channel decision (email vs. push vs. in-app only) — product
      decision, raise before building.
- [ ] Respect per-user opt-in/out.

### Task 4.2 — "What friends shared" digest
Status: PLANNED
Processes:
- [ ] Periodic digest (e.g. daily/weekly) of jobs shared into a user's
      group(s) since their last visit.
- [ ] Unsubscribe/frequency control.

---

## Open product decisions (not yet made — flag to the user, don't guess)

- Auth approach for Phase 3 (Task 3.1).
- Notification delivery channel for Phase 4 (Task 4.1).
- Whether `JobCreate.url` should become optional for text-only shares
  (Task 2.2) or a URL should stay mandatory at share time.
