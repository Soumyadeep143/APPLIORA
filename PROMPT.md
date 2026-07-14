# PROMPT.md — start here

Say "start with prompt.md" (or just point your agentic IDE at this file)
and follow these steps in order. Don't skip ahead to coding before step 3.

## 1. Orient

Read, in this order:

1. `README.md` — what Appliora is, how to run it, the API surface.
2. `AGENT.md` — how to work in this repo: conventions already established,
   non-negotiables, what "done" requires. Don't relitigate decisions it
   documents as already made.
3. `PRD.md` — the live plan. Phases → Tasks → Processes, each with a
   `Status:`.

## 2. Set up

```bash
cd backend
pip install -r requirements.txt pytest httpx
python -m pytest tests/        # should be all-green before you change anything
cd ../frontend
npm install
```

If tests aren't green at the start, stop and report that — don't build on
top of a broken baseline.

## 3. Find the next task

In `PRD.md`, find the earliest phase that isn't fully `DONE`, then the
first task in it that isn't `DONE`. That's your task. Read its `Why:` (if
present) and its `Processes:` checklist — that checklist is your plan,
already written. If a task's processes reference an "Open product
decision" (see the bottom of `PRD.md`), or you hit a genuine product
decision that isn't yours to make, stop and ask instead of guessing.

## 4. Do the task

Work through the task's `Processes:` checklist top to bottom. Follow
`AGENT.md`'s non-negotiables as you go — in particular, if this task
touches `backend/app/extractor.py`, you must check it against a real live
URL before calling it done, not just a mocked fixture (see
`BACKEND_VERIFICATION_ROADMAP.md` for why that rule exists).

## 5. Verify

Run through `AGENT.md`'s "Before calling a task done" checklist. All of it,
not the parts that are convenient.

## 6. Close the loop

In the same change: flip the task's `Status:` in `PRD.md` to `DONE`, check
off its processes, and update `BACKEND_VERIFICATION_ROADMAP.md` if the task
added new extraction coverage (Phase A's table there).

## 7. Stop and report

Summarize what changed, what you verified it against (which live URL, if
applicable), and what the next task in `PRD.md` will be. Don't
automatically continue to the next task — let whoever's driving decide
whether to keep going, unless they've told you up front to work through
multiple tasks unattended.
