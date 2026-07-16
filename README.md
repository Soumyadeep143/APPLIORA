# DevCareer — share jobs with friends

**Picking up development?** Start with [`PROMPT.md`](PROMPT.md) — it walks
you through `AGENT.md` (working rules) and `PRD.md` (the phased plan) and
tells you exactly what to do next.

Paste a job link, and DevCareer automatically fetches the **job title, company,
description and last date to apply**, then posts it to a shared board that you
and your friends can browse and search.

## How the auto-fetch works

When you paste a link (e.g. a Microsoft Careers job), the backend downloads the
page and extracts details in this order:

1. **schema.org JobPosting JSON-LD** — used by Microsoft Careers, LinkedIn,
   Greenhouse, Lever, Workday, Naukri and most job boards. Gives the exact
   title, hiring company, full description and `validThrough` (last date to
   apply).
2. **OpenGraph / Twitter meta tags** — `og:title`, `og:description`,
   `og:site_name`.
3. **Plain HTML** — `<title>`, `<h1>`, meta description.
4. **Heuristics** — company from the domain (`careers.microsoft.com` →
   Microsoft) or from "Role at Company" title patterns, deadline from
   "last date to apply …" phrases in the page text.
5. **AI-assisted extraction** (`backend/app/ai_extractor.py`) — Tavily
   fetches the page and Groq reads it for structured fields. This is the
   *first* attempt for LinkedIn, Naukri, Indeed (their `robots.txt`
   disallows AI-agent user-agents, so Tavily does the fetch instead of our
   backend), Lever, AshbyHQ, and SmartRecruiters (found via live-testing to
   return wrong-not-just-missing data from steps 1-4). For every other
   source it's a *fallback* when title/description come back empty.
   Requires `GROQ_API_KEY` and `TAVILY_API_KEY` in `backend/.env` (see
   below) — without them this step silently no-ops and steps 1-4 still
   work exactly as before.

Whatever is found is shown in an **editable preview** before sharing, so you
can fix or fill in anything the page didn't expose (some sites render jobs
with JavaScript or block bots — the preview tells you when that happens).

## How sharing identity works

Real accounts: register with a name + password (bcrypt-hashed) once, then
log in with the same credentials on any device — the same name
(case-insensitive) always maps back to the same identity. No email
required, no third-party identity provider.

## How reactions & comments work

Any signed-in friend can react to a shared job with one of four emoji (👍 🔥
🎯 🎉 — reacting again with the same one removes it) and leave comments in
a collapsible thread on the job card. Everyone can see who reacted/commented
(no anonymity within the board); only the comment's author can delete it.

## How deadline reminders & the sharing digest work

Opt in from "🔔 Reminders" (top right, once signed in) by adding an email
address and checking the box — this single opt-in covers two things in one
daily email:

1. **Deadline reminders** — jobs whose deadline falls within the next 3
   days, sent once per job (not once per day it stays in that window).
2. **"What friends shared"** — jobs shared to the board since your last
   digest. Each person has their own cursor, reset to "now" the moment
   they opt in (so opting in doesn't dump the board's whole history on
   you), and advanced daily regardless of whether there was anything new.

Requires `RESEND_API_KEY` in `backend/.env`; without it the scan still
runs (and still records what it "would have" sent) but delivers nothing.

The scan (`backend/app/reminders.py`) is **not** an in-process scheduler —
it's a standalone script meant to be triggered once a day by an external
scheduler (a Render Cron Job, or local cron/Task Scheduler):

```bash
cd backend
python -m app.reminders
```

## Project layout

```
.
├── backend/    FastAPI + SQLite  (extraction API + job board API)
└── frontend/   React + Vite      (share form, editable preview, job feed)
```

## Run locally

Backend (port 8000):

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Create `backend/.env` (gitignored):

```
# Optional — enables AI-assisted extraction (see above). Without these,
# that step silently no-ops and steps 1-4 still work exactly as before.
GROQ_API_KEY=...
TAVILY_API_KEY=...

# Optional — enables deadline-reminder emails (see "How deadline reminders
# work" below). Without it, the daily scan still runs and still records
# which jobs it would have reminded about, but sends nothing. Resend's free
# tier (100 emails/day) is enough for a friend board; sign up at
# resend.com. The unverified sandbox sender can only deliver to the email
# address registered on your own Resend account — verify a domain at
# resend.com/domains to send to your friends' real addresses.
RESEND_API_KEY=...
```

Frontend (port 5173, proxies API calls to the backend):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — done. Swagger docs live at
http://localhost:8000/docs.

## API

| Method | Path             | Purpose                                            |
| ------ | ---------------- | -------------------------------------------------- |
| POST   | `/api/auth/register` | Create an account (name + password), get `{id, name, email, reminders_opt_in}` |
| POST   | `/api/auth/login`| Sign in with name + password, get the same shape as register |
| POST   | `/api/extract`   | Fetch a job URL (or parse pasted text) and return detected fields (no save) |
| GET    | `/api/jobs`      | List shared jobs, newest first (`?search=` filters) |
| POST   | `/api/jobs`      | Save a job to the shared board (`user_id` required) |
| GET    | `/api/jobs/{id}` | Fetch one job                                       |
| DELETE | `/api/jobs/{id}` | Remove a job                                        |
| POST   | `/api/jobs/{id}/reactions` | Toggle an emoji reaction (`user_id`, `emoji`) |
| GET    | `/api/jobs/{id}/comments`  | List a job's comments |
| POST   | `/api/jobs/{id}/comments`  | Add a comment (`user_id`, `body`) |
| DELETE | `/api/jobs/{id}/comments/{comment_id}` | Delete your own comment (`?user_id=`) |
| PATCH  | `/api/users/{id}/notifications` | Set reminder email + opt-in (`email`, `opt_in`) |
| GET    | `/health`        | Health check                                        |

## Tests

```bash
cd backend
python -m pytest tests/
```

## Deploy (same pattern as ProdIntel)

- **Backend → Render**: web service rooted at `backend`, build
  `pip install -r requirements.txt`, start
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `DEVCAREER_DB_PATH`
  to a persistent-disk path if you attach one (otherwise the SQLite file
  resets on redeploy). Optionally set `GROQ_API_KEY`/`TAVILY_API_KEY`
  (AI-assisted extraction) and `RESEND_API_KEY` (deadline reminders) —
  each feature silently no-ops without its key.
- **Reminders + sharing digest → Render Cron Job**: separate Cron Job
  resource (same repo, rooted at `backend`), same build command as the web
  service, schedule `0 9 * * *` (or whenever), command
  `python -m app.reminders`. Needs the same `DEVCAREER_DB_PATH` (pointed at
  the *same* persistent disk as the web service — it reads the same
  jobs/users tables) and `RESEND_API_KEY`.
- **Frontend → Vercel**: project rooted at `frontend`, framework
  preset *Vite*, environment variable `VITE_API_URL` pointing at the Render
  backend URL (e.g. `https://devcareer.onrender.com`).
