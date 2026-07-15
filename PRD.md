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
Status: DONE — 2026-07-15
Why: user-requested — "might be a mail or something that is job related",
i.e. someone forwards a job description by email/Slack with no clean
scrapeable URL, or the URL is login-walled (see the Google Forms case
investigated 2026-07-15: a form requiring Google sign-in can never be
fetched by any client, bot or browser).

Open product decision resolved (user-directed): a URL stays mandatory at
*share* time even when the *fetch* step accepted freeform text — a board
entry with nothing to click through to is low value. `JobCreate.url`
stays required unchanged; the frontend draft form now has its own
required "Job link" field so a text-parsed draft can't be shared without
one.

Processes:
- [x] Backend: `POST /api/extract` (`ExtractRequest` in `main.py`) accepts
      either `url` or `text` (`url` is now optional, at least one of the
      two is required via a `model_validator`). `text` skips the network
      fetch entirely and runs `extract_job_metadata_from_text` (new,
      `extractor.py`), which reuses `_apply_text_heuristics`,
      `DEADLINE_TEXT_RE` and the existing title/company splitting —
      nothing that depends on fetched HTML (JSON-LD, meta tags,
      site-specific handlers) applies, since there's no page.
- [x] A live-shaped check (a realistic forwarded-email paste — "Fwd: ..."
      subject line followed by a "Role: ... at ..." line) surfaced a real
      bug: taking the literal first line as the title picked up the "Fwd:"
      subject instead of the actual role line. Fixed by scanning all lines
      for a `Role:`/`Position:`/`Job Title:` label first, falling back to
      the first non-blank line only if no such label exists
      (`LEADING_LABEL_RE` in `extractor.py`).
- [x] Frontend: the paste box (`frontend/src/App.jsx`) is now a
      `<textarea>` accepting a URL or freeform multi-line text. Button
      label switches between "Fetch details" and "Parse text" based on
      whether the trimmed input matches `^https?://\S+$`. The draft form
      gained a required "Job link" field (pre-filled from `meta.url` when
      fetched from a URL, empty when parsed from text) so sharing is
      blocked — via the input's own `required` — until a real apply link
      is supplied.
- [x] Tests: pasted-email-style fixtures in `test_extractor.py`
      (`test_extract_from_pasted_text`, and the "Fwd:" subject-line
      regression case) plus API-level tests in `test_api.py`
      (`test_extract_accepts_pasted_text`, `test_extract_requires_url_or_text`).
      23 tests pass (`python -m pytest tests/`, from `backend/`).
- [x] Manually clicked through both flows in a real browser (Playwright,
      since `chromium-cli` wasn't available in this environment): pasted a
      live `boards.greenhouse.io/stripe/jobs/7954688` URL → fetched,
      shared, appears in feed; pasted the forwarded-email text → parsed to
      title "Product Manager" / company "Notion" / deadline "2026-09-30",
      blocked from sharing with an empty Job link (native browser
      validation), shared successfully once a link was filled in. No
      console errors either time.

### Task 2.3 — Surface extraction confidence in the UI
Status: DONE — 2026-07-15
Why: right now `notes` is the only signal a field was guessed vs. found
authoritatively; users can't tell "we're confident" from "we guessed this
from the URL."

Implementation note: the processes below ask to "expose that per-field" —
implemented as a 3-tier `field_confidence` dict (`high`/`medium`/`low`)
rather than raw strategy names (`jsonld`/`meta`/`heuristic`/...). Reasoning:
the frontend's actual need (per the second process) is just "flag
low-confidence fields," and a pre-computed tier keeps that a one-line
frontend check instead of the frontend needing its own strategy-name → UI
mapping, and avoids leaking `extractor.py`'s internal function names as a
de facto API contract that then can't be refactored freely. This was a
judgment call within the task, not a product decision — noted here for
visibility, not raised beforehand.

Processes:
- [x] Backend (`backend/app/extractor.py`): every field-write across every
      strategy (JSON-LD, `_apply_linkedin`, `_apply_greenhouse_embedded_json`,
      meta tags, plain HTML, text heuristics, domain-fallback, both AI
      paths, and the pasted-text pipeline) now goes through a new `_set()`
      helper that fills the field *and* stamps `result["field_confidence"][field]`
      with a tier:
      - `high` — JSON-LD, a site-specific handler, or AI-assisted extraction
        when it's the deliberately chosen primary source (`AI_PREFERRED_HOSTS`).
      - `medium` — OpenGraph/meta tags, a page's `<h1>`, AI extraction used
        to fill a gap on a non-preferred host, or a pasted-text title found
        via an explicit "Role:"/"Position:" label.
      - `low` — domain/path-based company fallback, title/company text
        splitting, the free-text deadline regex, or a pasted-text title
        with no explicit label (bare first line).
      Title-trimming/splitting (mutating an already-filled title) and
      description truncation deliberately bypass `_set` — they modify an
      existing value rather than filling an empty one, so the original
      tier stands.
- [x] Frontend (`frontend/src/App.jsx`): the draft form now carries
      `draftConfidence` (from `meta.field_confidence`) alongside the
      existing `draftNotes`. Job title/Company/Last date to apply/Location
      labels show a small "GUESSED" badge when that field's tier is `low`
      (`.confidence-flag` in `index.css`) — medium/high fields show nothing,
      keeping the flag meaningful rather than noisy.
- [x] Tests: `test_extractor.py` gained tier-specific coverage (JSON-LD →
      all high; meta-tag fallback → medium, free-text deadline → low;
      title-splitting company → low; domain-fallback company → low;
      AI-preferred-host primary → high; AI-supplement → medium; both
      pasted-text title tiers). 27 tests pass (`python -m pytest tests/`,
      from `backend/`).
- [x] Live-verified: a real `boards.greenhouse.io/stripe/...` posting
      (title/description via meta tags → medium, company via path-fallback
      → low) and a real `jobs.smartrecruiters.com` posting via the AI path
      (title → high). Then clicked through both in a real browser
      (Playwright) — confirmed the "GUESSED" badge renders on Company (and,
      for a pasted-text draft, also on Last date to apply) while Job title
      shows no badge on the same draft, and no console errors.

---

## Phase 3 — Accounts & Collaboration

**Goal:** Move from "type your name each time" to real identity and
friend-scoped sharing, without over-building an auth system this product
doesn't need yet.

### Task 3.1 — Replace free-text name with real identity
Status: DONE — 2026-07-15
Why: `shared_by` was a free-text field with a client-side `localStorage`
default — anyone could type any name, and it wasn't tied to any real,
persistent record, so "who shared this" was just a label, not an identity.

Open product decision resolved (user-directed): **simple invite code**, not
magic-link email or OAuth. No passwords, no email-sending service, no OAuth
app registration — a single shared secret (`APPLIORA_INVITE_CODE` in
`backend/.env`) plus a display name is treated as proof of being a member
of the friend group. Accepted trade-off, stated up front: anyone who knows
the invite code can claim any name. Right-sized for a small trusted friend
board; revisit if this ever needs to resist a dishonest member of the
group itself, not just outsiders.

Processes:
- [x] New `users` table (`backend/app/database.py`): `id`, `name` (`UNIQUE
      COLLATE NOCASE` — case-insensitive, so "Alex" and "alex" are the same
      person), `created_at`.
- [x] `POST /api/auth/login` (`backend/app/main.py`): `{name, invite_code}`
      → validates the invite code (`hmac.compare_digest`, both sides
      UTF-8-encoded) against `APPLIORA_INVITE_CODE`, then
      `get_or_create_user(name)` — logging in with an existing name
      re-identifies that person rather than creating a duplicate. Returns
      503 if the server has no invite code configured, 401 if it doesn't
      match. No session/token: the frontend just remembers `{id, name}`.
- [x] `shared_by` becomes a foreign key: `jobs.shared_by_user_id INTEGER
      REFERENCES users(id)`. `JobCreate.shared_by` (free text) replaced by
      `JobCreate.user_id` (must reference a real user — 400 if not).
      `list_jobs`/`get_job` resolve the display name via `COALESCE(users.name,
      jobs.shared_by)` over a `LEFT JOIN`, so the API's `shared_by` field
      shape is unchanged for callers (including the frontend) even though
      its source changed.
- [x] Migration: existing `jobs` tables (created before this shipped) get
      `shared_by_user_id` added via `ALTER TABLE ... ADD COLUMN` in
      `init_db()` (no ORM/migration framework, per AGENT.md's conventions —
      the same "raw SQL, by hand" pattern already used for this table).
      Verified against the real local `appliora.db`: existing rows come back
      with `shared_by_user_id = NULL` and keep displaying their original
      free-text `shared_by` value unchanged (there's no `users` row yet to
      best-effort-match them to, since that table only starts getting
      populated once login exists — the "leave as a legacy display name"
      option, not a fuzzy-match import).
- [x] Frontend (`frontend/src/App.jsx`): the always-editable "Your name"
      input is replaced by a sign-in form (name + invite code) shown until
      `POST /api/auth/login` succeeds; the result is remembered in
      `localStorage` (`appliora_user`) and used as `user_id` on
      `POST /api/jobs`. A "Switch" button clears it so someone else can
      sign in on the same device/browser. Sharing is blocked with an
      inline error if no one is signed in.
- [x] Tests: `test_api.py` gained login tests (create-and-reuse by
      case-insensitive name, wrong invite code, blank name) and
      `test_create_job_rejects_unknown_user_id`; the old
      `test_create_job_blank_name_becomes_anonymous` (free-text-specific)
      was removed since that behavior no longer exists. 30 tests pass
      (`python -m pytest tests/`, from `backend/`).
- [x] Manually clicked through in a real browser (Playwright): wrong
      invite code shows an error and no identity is set; correct code
      signs in and persists across a page reload (`localStorage`); shared a
      job as one user, hit "Switch", signed in as a second user, shared
      another job — the feed correctly attributed each job to the right
      person alongside the pre-existing legacy (pre-migration) job's
      original free-text name. No console errors.

### Task 3.2 — Friend groups / private boards
Status: PLANNED
Why: right now every signed-in person sees and shares to the same single
board — there's no way to keep a college-friends board separate from a
work-friends board.

Attempted and reverted same day (2026-07-15): built multiple
private-per-group boards (`groups`/`group_memberships` tables, `jobs.group_id`,
group-scoped `GET`/`POST /api/jobs` with 403/404 membership checks, a
board-switcher UI) after two product decisions (multi-group membership;
auto-create a group on an unseen invite code). User then decided against
group separation entirely — reverted to Task 3.1's single shared board
before this task's Status was ever flipped to DONE. `APPLIORA_INVITE_CODE`
(Task 3.1's single server-configured invite code) is back in place — a
group invite code is required once to establish identity, never asked
again afterward since the browser remembers `{id, name}` in localStorage.
If groups are revisited later, re-litigate the two decisions above rather
than assuming they still hold.

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

- Notification delivery channel for Phase 4 (Task 4.1).
