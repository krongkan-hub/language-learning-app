# ADR-003: Formalize AI Playtester into the QA Standing Toolset

**Status:** Accepted  
**Owner:** `architect_agent` & `qa_agent`  

## Context
During initial scenario generation, `scripts/ai_playtester.py` was created as an experimental script to simulate multi-turn learner-actor dialogue using an LLM-driven learner persona (`LEARNER_SYS`). The script checks whether task goals are winnable against the task judge (`evaluate_task`). 

However, the script remained unwired from automated test execution and lacked formal standing within the multi-agent harness (`ADR-002`), leaving it uncertain whether to discard or integrate it.

## Decision
Formalize and wire `scripts/ai_playtester.py` into the development and testing workflow:
1. **Tool Integration & Execution Wiring:** `scripts/ai_playtester.py` is wired via `make playtest` in [Makefile](file:///Users/pk/language-learning-app/Makefile) and unit-tested in [tests/test_playtester.py](file:///Users/pk/language-learning-app/tests/test_playtester.py).
2. **Acceptance Gate:** Before any new scenario or task redesign is merged into `app/scenarios/builtins.py`, developers or `qa_agent` execute `make playtest` to confirm that tasks within the scenario can be completed within 3 turns by a simulated learner.
3. **Execution Safety:** The script uses `HF_HUB_OFFLINE=1` and standard MLX options to execute locally without external API dependencies.

## Consequences
- Preserves automated multi-turn playtesting capability for continuous quality assurance.
- Wires `make playtest` and pytest unit integration tests into the repository automation pipeline.
- Prevents unwinnable tasks (`BUG-026`) and missing reactive premises (`BUG-029`) from being merged into production scenario lists.
- BL-19 is resolved and closed in `BACKLOG.md`.

## Amendment, 2026-09-06

The Decision above still holds, but point 2 names a file that no longer holds
any scenarios. `app/scenarios/builtins.py` is a 56-line JSON loader; the
catalog moved to the 80 files in `app/scenarios/data/`. An acceptance gate
keyed to a file nobody edits is a gate that never fires, and that is what
happened: the four task goals rewritten on 2026-09-06 to clear the
cross-scenario duplicates changed scenario content without anyone running
`make playtest`.

Point 2 should be read as: **before merging a change to any file under
`app/scenarios/data/`, run `make playtest` over the affected scenarios.**

It stays manual, and deliberately so. `scripts/ai_playtester.py` drives the
7B model through multi-turn dialogue, so it costs minutes per scenario and
cannot join `scripts/check_all.sh`, which the project keeps under six seconds
so that it is run without thinking. This is the same reasoning OPEN-08 used to
keep `check_evals.sh` out of the deterministic gate. The honest position is
that this is a checklist item enforced by people, not a gate enforced by
machinery — writing it into CI would either slow the gate by orders of
magnitude or produce a job that is disabled within a week.

Two hazards worth knowing before running it:

- `scripts/playtest_sample.py` resumes from its `--out` file by design, so
  re-running against an existing results file replays the old numbers without
  touching the model. Use a fresh `--out` path when verifying a change.
- The playtest measures *task winnability* — whether a simulated learner can
  reach the goal, graded by the judge. It is blind to the coach by
  construction, so a 99.5% playtest and a coach that misses most Japanese
  errors are both true at once. It is not evidence about teaching quality.
