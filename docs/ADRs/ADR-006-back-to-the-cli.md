# ADR-006: Back to the CLI — drop the web front end

**Status:** Accepted, 2026-10-21
**Owner:** พี (project owner)

## Context

The CLI was retired on 2026-09-26 (`75d8573`) so every feature would be built
once, in the browser. Over the next four weeks the web front end grew into a
React + TypeScript app (`frontend/`, ~55 files) on a FastAPI + SSE server
(`app/web/`), with a character kit, a scene kit for all 80 scenarios, a
notebook theme, a Today page and a learner dashboard (#50–#59).

That work was real, but it is not what decides whether the app teaches. The
learner's experience is set by the three model calls — whether the coach
corrects a wrong sentence and leaves a right one alone, whether the judge
says "done" when the task was done, whether the NPC stays in character — and
every one of those runs on the same on-device 7B (ADR-001). A growing share
of each change was going into UI state, CSS, art parity tests and an npm
build in CI rather than into the model.

## Decision

1. **The terminal is the only front end again.** `app/cli/` is restored and
   `python3 main.py` (`make run`) starts it.
2. **The CLI is rebuilt on the current turn logic, not reverted.** Everything
   the model side gained while the web was the front end — mistake counting
   and retirement (#67, #74), vocabulary credit from use, the actor seeing its
   own cards (#60), the coach nets (#69–#73), explain mode, review sessions,
   the summary's next mastery rung — stays and is reachable from the CLI.
3. **The web is removed, not kept dormant:** `frontend/`, `app/web/`,
   `app/static/`, their tests, the web-only i18n strings, `fastapi`/`uvicorn`,
   the Dockerfile (it existed only to serve the web and could not run MLX
   anyway) and the npm steps in CI and `make check`. `docker-compose.yml`
   keeps its PostgreSQL service.
4. **MLX only.** No other runtime is reintroduced (ADR-001 stays as history).

## Consequences

- `make check` and CI are Python-only again: no Node toolchain, no front-end
  build, no art-kit parity tests.
- Lost with the web: the dashboard, the Today page, session resume after a
  reload, the visual theme. The data behind the dashboard is still collected
  (`spans`, `app/db/analytics.py`), so a text report can be built on it if it
  is wanted.
- Not restored from the old CLI: resuming an unfinished session (its db
  functions were removed in `7e597a1`) and the vocabulary warm-up quiz (using
  a word in conversation is what credits it now).
  *Update 2026-10-23:* both restored on the current APIs. Resume, because a
  killed process (the 7B has been OOM-killed here) left a session open and
  missing from `--stats` for a week; the quiz, as a direct recall check
  beside crediting a word used in conversation. The dashboard's data now
  feeds `--stats` (weekly activity, hardest scenarios, latency p50/p95).
- The web is recoverable from git (`2df28e9` is the last commit with it).
