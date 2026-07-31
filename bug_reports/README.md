# Bug Reports — Index & Conventions

Owned by `qa_agent`. This directory is the only place `qa_agent` writes to besides
`eval/coach_cases.json`. Other agents may read it; only `qa_agent` edits it.

## ID scheme
Global, sequential, never reused: `BUG-001`, `BUG-002`, ... Referenced from
`BACKLOG.md` and from `eval/*.json` regression cases where applicable.

## Status values
- **OPEN** — confirmed present in the current working tree, not yet fixed.
- **FIXED-UNCOMMITTED** — a fix exists in the working tree (`git status` shows
  the file modified) but hasn't been committed, and — for anything touching
  LLM output (coach/judge/actor) — hasn't been re-verified against a live
  model run. Code-reading confirms the *logic* changed; it does not confirm
  the *behavior* is now correct. Don't downgrade to FIXED until a live
  playtest or eval run confirms it.
- **NEEDS-VERIFICATION** — the file that contained the bug has since changed
  substantially (e.g. `app/cli.py`, `app/scenarios/builtins.py`) and the
  original repro hasn't been re-run against current code.
- **WONT-FIX** — accepted as inherent model behavior or out of scope, with
  reasoning recorded.

## Files
| File | Component |
| :--- | :--- |
| `coach.md` | `app/coach.py` — grammar feedback |
| `judge.md` | `app/judge.py` — task-completion grading |
| `actor.md` | `app/llm.py` — NPC dialogue generation, validation |
| `task-data.md` | `app/scenarios/builtins.py` — scenario/task content |
| `infra.md` | packaging, setup, error handling, repo hygiene |

## Provenance
BUG-001 through BUG-034 were filed from a 10-run manual playtest
(non-native-learner persona, mixed pass/fail coverage across 10 scenarios)
conducted before this harness existed. Status fields below reflect a
diff against the working tree as of the scaffolding date, **not** a fresh
live re-run — several fixes landed in the working tree between the playtest
and this filing. `qa_agent`'s first job should be to run its own playthrough
batch to confirm/refute every FIXED-UNCOMMITTED and NEEDS-VERIFICATION entry
and turn confirmed-fixed ones into `eval/coach_cases.json` regression cases
(a few have already been seeded — see that file).
