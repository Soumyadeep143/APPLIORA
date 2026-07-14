# Backend Verification Roadmap

What "properly tested" means for the Appliora backend, where it stands
today, and the phased plan to close the gap. This is scoped to
`backend/` only — frontend verification is covered by AGENT.md's
"actually run `npm run dev` and click through it" rule, not by this doc.

## Why this doc exists

`backend/app/extractor.py` had 100% passing mocked unit tests
(`test_extractor.py`) while being silently broken against real LinkedIn and
Greenhouse pages — the mocks encoded the *bug* as the expected behavior,
so they couldn't catch it. Mocked tests prove parsing logic is internally
consistent; they cannot prove it matches what a real external site
actually sends. This codebase now requires both, for exactly this reason.

## Current state (as of 2026-07-15)

| Layer | Coverage | File |
|---|---|---|
| Extraction parsing logic | Unit tests against hand-written HTML fixtures | `backend/tests/test_extractor.py` |
| API contract | `TestClient`-based request/response tests | `backend/tests/test_api.py` |
| Live-site behavior | Ad hoc, manual, not automated | none — done by hand during Task 1.5 |
| CI | None | — |
| Coverage measurement | None | — |

18 tests pass today (`python -m pytest tests/`, from `backend/`).

## Phase A — Fixture coverage for every source we claim to support (mostly DONE)

Goal: every branch in `extractor.py`'s field-by-field priority chain
(JSON-LD → site-specific handler → meta tags → plain HTML → heuristics →
domain fallback → AI-assisted extraction) has at least one fixture test
that would fail if that branch broke.

- [x] JSON-LD JobPosting (`test_jsonld_extraction`)
- [x] OpenGraph fallback + text-deadline heuristic (`test_og_fallback_with_text_deadline`)
- [x] Fetch failure → domain-based company fallback (`test_fetch_failure_still_returns_domain_company`)
- [x] `_company_from_domain` incl. path-based (Greenhouse/Lever) and
      subdomain-based (Workday) ATS hosts (`test_company_from_domain`)
- [x] `_normalise_date` format coverage
- [x] LinkedIn topcard handler (`test_linkedin_topcard_extraction`)
- [x] Greenhouse embedded-JSON handler (`test_greenhouse_remix_extraction`)
- [x] AI-preferred-host success path skips local fetch entirely
      (`test_ai_preferred_host_skips_local_fetch_when_ai_succeeds`)
- [x] AI-preferred-host degrades to local pipeline when AI unusable
      (`test_ai_preferred_host_falls_back_to_local_pipeline_when_ai_unusable`)
- [x] AI supplements only empty fields, never clobbers local data
      (`test_ai_supplements_missing_fields_without_clobbering_local_data`)
- [x] Generic placeholder `<title>` (e.g. AshbyHQ's pre-hydration shell)
      rejected rather than reported as the job title
      (`test_generic_placeholder_title_not_reported_as_real`)

`ai_extractor.py`'s own Tavily/Groq call logic (HTTP request shape, JSON
parsing, error handling) has **no fixture tests yet** — only live
verification during Task 2.1. It's a thin, mostly-I/O module; worth a
follow-up if it grows more logic than "call API, parse JSON, return None
on any failure."
- [ ] Indeed / Naukri / SmartRecruiters / AshbyHQ / Lever — no fixture yet;
      blocked on Task 2.1 in `PRD.md` (need to see real markup first before
      writing a fixture that means anything).

## Phase B — Live smoke checks (manual today, automate next)

Goal: catch the "mocks encode the bug" failure mode Task 1.5 found, before
it ships, not after a user reports it.

- [ ] Write `backend/tests/live_smoke.py` (or similar), **excluded from the
      default `pytest` run** (network + third-party sites are flaky by
      nature — this must never block a normal test run or CI on a
      transient 429/timeout from LinkedIn). Gate it behind an env var,
      e.g. `RUN_LIVE_EXTRACTOR_TESTS=1 pytest tests/live_smoke.py`.
- [ ] One real URL per supported source (LinkedIn, Greenhouse, and whatever
      Task 2.1 adds), asserting only the cheap, stable invariants: `title`
      and `company` are non-empty, `fetch_ok` is `True`. Don't assert exact
      text — job postings get taken down and titles get edited; assert
      *shape*, not content.
- [ ] Run this manually before marking any extractor task in `PRD.md` done
      (per AGENT.md's non-negotiable). Automating the *running* of it is
      Phase C's job — the check itself needs to exist first.

## Phase C — CI

Goal: `test_extractor.py` and `test_api.py` run on every push/PR
automatically; nobody has to remember to run `pytest` locally before
merging.

- [ ] Add a CI workflow (GitHub Actions, since the deploy target in
      `README.md` is GitHub-hosted-friendly: Render + Vercel both deploy
      from a GitHub push) that runs `pip install -r requirements.txt
      pytest httpx` then `pytest tests/` on every PR touching `backend/`.
- [ ] Explicitly do **not** run Phase B's live smoke tests in CI — network
      flakiness would make CI red for reasons unrelated to the actual
      change. Live smoke stays a pre-merge manual step for extractor
      changes specifically (see AGENT.md).
- [ ] Fail the PR check on any `pytest` failure. No skip/xfail without a
      linked follow-up.

## Phase D — Coverage measurement (once Phase C exists)

Goal: know what's *not* tested, not just what is.

- [ ] Add `pytest-cov`, wire `--cov=app --cov-report=term-missing` into the
      CI job from Phase C.
- [ ] No hard coverage-percentage gate yet — read the missing-lines report
      after each PR and use judgment. A number-chasing gate on a codebase
      this size would just encourage low-value tests.

## Non-goals

- End-to-end browser testing (Playwright/Cypress) against the frontend —
  not worth it at this size; AGENT.md's "run it and click through it"
  manual check covers the frontend for now. Revisit if Phase 3/4 of
  `PRD.md` (auth, notifications) land and the UI gets complex enough that
  manual regression checking stops being reliable.
- Load/performance testing — not a bottleneck at current scale (single
  SQLite file, a friend board, not a public job aggregator).
