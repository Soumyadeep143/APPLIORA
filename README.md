# Appliora — share jobs with friends

**Picking up development?** Start with [`PROMPT.md`](PROMPT.md) — it walks
you through `AGENT.md` (working rules) and `PRD.md` (the phased plan) and
tells you exactly what to do next.

Paste a job link, and Appliora automatically fetches the **job title, company,
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

Optional — enables AI-assisted extraction (see above). Create
`backend/.env` (gitignored) with:

```
GROQ_API_KEY=...
TAVILY_API_KEY=...
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
| POST   | `/api/extract`   | Fetch a job URL and return detected fields (no save) |
| GET    | `/api/jobs`      | List shared jobs, newest first (`?search=` filters) |
| POST   | `/api/jobs`      | Save a job to the shared board                      |
| GET    | `/api/jobs/{id}` | Fetch one job                                       |
| DELETE | `/api/jobs/{id}` | Remove a job                                        |
| GET    | `/health`        | Health check                                        |

## Tests

```bash
cd backend
python -m pytest tests/
```

## Deploy (same pattern as ProdIntel)

- **Backend → Render**: web service rooted at `backend`, build
  `pip install -r requirements.txt`, start
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `APPLIORA_DB_PATH`
  to a persistent-disk path if you attach one (otherwise the SQLite file
  resets on redeploy).
- **Frontend → Vercel**: project rooted at `frontend`, framework
  preset *Vite*, environment variable `VITE_API_URL` pointing at the Render
  backend URL (e.g. `https://appliora.onrender.com`).
