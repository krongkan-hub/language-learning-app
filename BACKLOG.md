# Backlog

Owned by `pm_agent`. Every open item (bug report, feature request, architecture follow-up) is tracked here. Detailed reproduction steps for resolved or historical bugs reside in [`bug_reports/`](bug_reports/).

## Status

The project is a CLI language-learning roleplay application using local LLMs via MLX on Apple Silicon for English and Japanese instruction. All quality gates are currently green: the catalog comprises 80 scenarios × 69 tasks = 5,520 tasks stored in [`app/scenarios/data/scenario_01.json`](app/scenarios/data/scenario_01.json) … `scenario_80.json` and loaded via [`app/scenarios/builtins.py`](app/scenarios/builtins.py); depth checks ([`scripts/check_task_depth.py`](scripts/check_task_depth.py) `1-80 --expect-total=5520`), scenario parity ([`scripts/check_scenario_parity.py`](scripts/check_scenario_parity.py)), content coherence ([`scripts/check_content_coherence.py`](scripts/check_content_coherence.py)), and catalog roundtrip ([`scripts/check_catalog_roundtrip.py`](scripts/check_catalog_roundtrip.py), sha256 `48af3341797c6074`) all return zero errors; unit tests pass (120/120 via `pytest`); and evaluation suites show 99.5% playtest pass rate (199/200, seed 42), 100% coach eval ([`scripts/eval_coach.py`](scripts/eval_coach.py), 65/65), 100% actor eval ([`scripts/eval_actor.py`](scripts/eval_actor.py), 15/15), and 93.8% judge eval ([`scripts/eval_judge.py`](scripts/eval_judge.py), 75/80 with 0 false negatives).

## Open Items

| ID | Title | File / Context | Status & Note |
| :--- | :--- | :--- | :--- |
| OPEN-01 | Judge fixture case 5 false positive | [`scripts/eval_judge.py`](scripts/eval_judge.py), [`eval/judge_cases.json`](eval/judge_cases.json) | **Accepted trade.** The judge credits a partial answer ("charged full price") as complete without an explicit refund request. Fixing it reintroduced false negatives, which are worse for learners. |
| OPEN-02 | No session resume | [`app/db.py`](app/db.py) | **Not yet built.** Sessions are recorded to SQLite, but an interrupted session cannot be resumed. |
| OPEN-03 | No progress view | [`app/db.py`](app/db.py) | **Not yet built.** `get_scenario_stats()` exists in `app/db.py` to calculate progress metrics, but no CLI command or UI view invokes it. |
| OPEN-04 | MLX / Apple Silicon only | [`app/llm.py`](app/llm.py) | **Deliberate scope choice.** Runs directly against MLX on Apple Silicon without a backend abstraction layer (e.g. Ollama, vLLM). |
| OPEN-05 | JSON catalog storage / No authoring UI | [`app/scenarios/data/`](app/scenarios/data/) | **Deliberate scope choice.** Content is stored per-scenario as JSON files; authoring relies on JSON files and maintenance scripts rather than an authoring tool. |
| OPEN-06 | Language support limited to English & Japanese | [`app/cli.py`](app/cli.py) | **Deliberate scope choice.** UI localization, scenario content, and prompt structures support English and Japanese; Thai and other languages are not supported. |

## Recently Resolved

For historical commit logs and detailed change history, see `git log`. Key recent milestones include:

- **Scenario 2 Misalignment Fix:** Replaced 69 job-interview tasks under an airport scenario heading with true airport-relevant tasks.
- **Catalog-Wide Content Polish:** Eliminated near-duplicate goals, trivial vocabulary targets, and goal/`done_when` mismatches across all 5,520 tasks.
- **Actor Output Validation & Repair:** `call_actor` can no longer return text that fails `validate()`. `repair_actor_output` truncates over-length turns and `salvage_actor_output` drops closed yes/no questions, both preserving the vocab block; the diagnostic that used to print at the learner is now behind `DEBUG`.
- **Engine Robustness & Error Handling:** Lazy MLX model loading via `_ensure_model` with the original exception chained, replacing an import-time load whose bare `except` discarded the cause. `MLX_ERRORS` is deliberately **not** narrowed — `mlx-lm` documents no exception contract and [`app/cli.py`](app/cli.py) catches it at top-level boundaries to show a readable message instead of a traceback mid-conversation; the handlers re-raise under `DEBUG` so real bugs still surface.
- **JSON Migration & Codebase Infrastructure:** Migrated scenario data into per-scenario JSON files ([`app/scenarios/data/`](app/scenarios/data/)), simplified [`app/scenarios/builtins.py`](app/scenarios/builtins.py), added [`README.md`](README.md) and [`pyproject.toml`](pyproject.toml), and localized CLI outputs for English and Japanese.
