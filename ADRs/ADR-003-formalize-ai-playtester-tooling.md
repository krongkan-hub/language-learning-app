# ADR-003: Formalize AI Playtester into the QA Standing Toolset

**Status:** Accepted  
**Owner:** `architect_agent` & `qa_agent`  

## Context
During initial scenario generation, `scripts/ai_playtester.py` was created as an experimental script to simulate multi-turn learner-actor dialogue using an LLM-driven learner persona (`LEARNER_SYS`). The script checks whether task goals are winnable against the task judge (`evaluate_task`). 

However, the script remained unwired from automated test execution and lacked formal standing within the multi-agent harness (`ADR-002`), leaving it uncertain whether to discard or integrate it.

## Decision
Formalize `scripts/ai_playtester.py` into the standing toolset of `qa_agent`:
1. **Tool Integration:** `scripts/ai_playtester.py` is maintained as a core QA evaluation tool for automated, non-interactive playtesting of new and modified scenarios in `app/scenarios/builtins.py`.
2. **Acceptance Gate:** Before any new scenario or task redesign is marked as `done`, `qa_agent` must run `scripts/ai_playtester.py` to confirm that all tasks within the scenario can be completed within 3 turns by a simulated learner.
3. **Execution Safety:** The script uses `HF_HUB_OFFLINE=1` and standard MLX options to execute locally without external API dependencies.

## Consequences
- Preserves automated multi-turn playtesting capability for continuous quality assurance.
- Prevents unwinnable tasks (`BUG-026`) and missing reactive premises (`BUG-029`) from being merged into production scenario lists.
- BL-19 is resolved and closed in `BACKLOG.md`.
