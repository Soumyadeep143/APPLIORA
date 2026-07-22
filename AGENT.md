# AGENT.md — working rules for DevCareer

This file is for whoever is doing the engineering work here — human or
agentic IDE. Read this once at the start of a session; it doesn't repeat
per task. `PROMPT.md` is the per-session entry point that tells you what to
actually do next; this file tells you *how* to do it.

## What this project is

DevCareer: paste a job link, get title/company/description/deadline
auto-filled, share it to a friend board. Backend: FastAPI + SQLite
(`backend/`). Frontend: React + Vite (`frontend/`). Full API surface and
run instructions are in `README.md` — don't duplicate that here, read it.

## Source of truth

`PRD.md` is the live plan: Phases → Tasks → Processes, each with a
`Status:`. Work the next non-`DONE` task in the earliest non-`DONE` phase,
top to bottom, unless told otherwise. Update `PRD.md`'s checkboxes and
`Status:` line in the *same* change that does the work — a task that's
actually done but still shows `NEXT` in the file is worse than no doc at
all, because the next person trusts it.

`BACKEND_VERIFICATION_ROADMAP.md` defines what "tested enough to call it
done" means for backend work specifically.

## Non-negotiables for this repo specifically

- **`backend/app/extractor.py` changes require a live check, not just a
  mocked fixture.** This codebase has already shipped extraction logic that
  passed every mocked unit test while being silently broken against real
  LinkedIn and Greenhouse pages (fixed 2026-07-15 — see PRD Task 1.5). A
  fixture proves your parsing logic works on the HTML you wrote by hand; it
  proves nothing about whether that HTML matches what the real site sends
  today. Before marking any extractor task done: fetch one real, currently
  live URL of that type and print the parsed result. Then add the fixture
  test for regression protection. Both steps, not one.
- **Site-specific extraction fixes go in dedicated functions, not generic
  heuristics.** `_apply_linkedin`, `_apply_greenhouse_embedded_json` are the
  pattern: detect the host, run a handler with hardcoded knowledge of that
  site's markup, and only fill fields still empty (so it composes with the
  JSON-LD/meta/heuristic fallback chain instead of fighting it). Don't try
  to make the generic heuristics smarter to special-case one more site —
  that's how `_company_from_domain` ended up silently blanking Workday's
  company field (the aggregator-name substring check was too broad).
- **`extract_job_metadata` must never raise.** It always returns a dict with
  every field present (empty string if unknown) plus `fetch_ok` and
  `notes`. Callers (the API layer, the frontend) depend on this — don't add
  a code path that can throw past `extract_job_metadata`'s own try/except.
- **A job posting URL that redirects to a login page (401/302→accounts...)
  cannot be fixed in this codebase.** That's a property of the source, not
  a bug in the extractor. Don't spend time trying to work around
  authentication walls; report it as expected behavior via `notes` (already
  handled) and move on.

## Running things

```bash
cd backend && python -m pytest tests/          # backend tests
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev                      # http://localhost:5173
```

If `pytest`/`httpx` aren't installed in the venv yet: `pip install -r
requirements.txt pytest httpx`.

## Code conventions already established — follow them, don't relitigate

- Backend: plain functions over classes, dict in/dict out for the
  extractor, Pydantic models only at the API boundary (`main.py`). No ORM —
  raw SQL in `database.py` is intentional for a table this small.
- Frontend: no state management library; `useState`/`useCallback` in
  `App.jsx` is deliberate for an app this size. Don't introduce Redux/Zustand
  etc. without discussing it first.
- Frontend pages (PRD.md Task 6.4): each distinct screen — `AddJobPage`,
  `BrowseJobsPage`, `LoginPage`, `SignupPage`, `AdminPage` — is its own
  `.jsx` + `.css` file, rendered by `main.jsx`'s `Root` based on
  `activeView`. `App.jsx` stays the state owner (fetch/share/delete/react
  handlers, the real `user` state); page components are presentational,
  receiving what they need as props rather than each managing their own
  copy of shared state. `Landing.jsx`'s header is the one persistent nav
  across every page. Follow this shape for any new page rather than adding
  another conditional section inside an existing one.
- Superadmin exists exactly once, seeded at startup from the
  `MASTER_SUPERADMIN_USERNAME` / `MASTER_SUPERADMIN_PASSWORD` env vars
  (`backend/.env`, gitignored — never hardcoded in source). There's no other
  way to become superadmin. Regular admin accounts can only be granted by
  logging in as that superadmin and promoting someone via `PATCH
  /api/admin/users/{id}/admin` — registration alone never grants either
  role. (The previous `ADMIN_NAMES`/`SUPERADMIN_NAMES` env-var mechanism,
  which matched a registering/logging-in account's display `name`, was
  removed — `name` isn't unique, so anyone could register an account with a
  matching name and get auto-promoted.)
- No comments explaining *what* code does. Comments here explain *why*
  something non-obvious is true (see the `refreshSeq` ref in `App.jsx`, or
  the aggregator-substring-check comment in `extractor.py`) — match that
  bar, don't add narration comments.
- Don't add authentication, feature flags, or config toggles for anything
  in `PRD.md` marked `PLANNED` — build what the current task needs.

## Before calling a task done

1. `cd backend && python -m pytest tests/` passes.
2. If you touched `extractor.py`: ran it against a real live URL (see
   Non-negotiables above) and the output looks right, not just "didn't
   crash."
3. If you touched the frontend: actually ran `npm run dev` and clicked
   through the flow you changed — don't rely on the backend tests alone to
   validate a UI change.
4. `PRD.md` updated: `Status:` flipped, processes checked off, in the same
   change.
5. If you hit a product decision that isn't yours to make (see PRD's "Open
   product decisions" section, or anything similar you discover), stop and
   ask — don't guess and build.
