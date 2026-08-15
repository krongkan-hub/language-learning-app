# Backlog

Owned by `pm_agent`. Every open item (bug report, feature request, architecture follow-up) is tracked here. Detailed reproduction steps for resolved or historical bugs reside in [`bug_reports/`](bug_reports/).

## Status

The project is a CLI language-learning roleplay application using local LLMs via MLX on Apple Silicon for English and Japanese instruction.

All figures below were re-measured on **2026-08-15** at commit `a386434`, replacing earlier numbers that had drifted from reality. Every deterministic gate is green; the LLM-graded suites are green except for the judge and coach limits recorded in OPEN-01 and OPEN-07.

### Deterministic gates — [`scripts/check_all.sh`](scripts/check_all.sh), all passing

| Check | Result |
| :--- | :--- |
| `pytest` | 222 passed |
| `pyflakes` (`app/ scripts/ main.py`) | clean |
| [`check_task_depth.py`](scripts/check_task_depth.py) `1-80 --expect-total=5520` | pass |
| [`check_scenario_parity.py`](scripts/check_scenario_parity.py) `1-80` | pass |
| [`check_content_coherence.py`](scripts/check_content_coherence.py) | pass (6/6 sub-checks) |
| [`check_catalog_roundtrip.py`](scripts/check_catalog_roundtrip.py) | 80 scenarios, 5,520 tasks, sha256 `48af3341797c6074` |
| coverage floor (≥80%) | 82% |

The catalog comprises 80 scenarios × 69 tasks = 5,520 tasks stored in [`app/scenarios/data/scenario_01.json`](app/scenarios/data/scenario_01.json) … `scenario_80.json` and loaded via [`app/scenarios/builtins.py`](app/scenarios/builtins.py).

### LLM-graded suites — not run by `check_all.sh`, see OPEN-08

| Suite | Result | Note |
| :--- | :--- | :--- |
| [`eval_actor.py`](scripts/eval_actor.py) | 100% (20/20) | 4 cases × 5 iterations |
| [`eval_moods.py`](scripts/eval_moods.py) | 100% (18/18) | 6 moods × 3 turns; mean latency 7.1–10.7s |
| [`eval_coach.py`](scripts/eval_coach.py) | 93.8% (75/80) | 16 cases × 5; case 14 fails 5/5 — OPEN-07 |
| [`eval_judge.py`](scripts/eval_judge.py) | 84.6% (110/130) | 26 cases × 5; 3/15 false negatives, 1/11 false positives — OPEN-01 |
| [`playtest_sample.py`](scripts/playtest_sample.py) | 99.5% (199/200, seed 42) | fresh run, 73.5 min compute; 1 failure — OPEN-09 |

The coach and judge percentages are lower than the figures previously published here (100% and 93.8%). **This is not a regression.** Both denominators grew when Japanese fixtures were added in `f6fc457` and two reproducible judge false negatives were added as fixtures in `076c296`; the failing cases are deliberately left visible rather than deleted. The old numbers were simply never updated.

## Open Items

| ID | Title | File / Context | Status & Note |
| :--- | :--- | :--- | :--- |
| OPEN-01 | Judge false negatives and one false positive | [`scripts/eval_judge.py`](scripts/eval_judge.py), [`eval/judge_cases.json`](eval/judge_cases.json) | **Known limit, left visible.** 3/15 false negatives (cases 22, 25, 26) and 1/11 false positive (case 5). The three FNs are one bug class: conversation context is placed ahead of the goal in `judge_llm`'s prompt, so the judge grades the learner against the NPC's last question or demands every branch of an OR goal. All three vanish when context is removed. Two prompt restructures were tried and reverted — each cut false negatives to 0 but pushed false positives from 1 to 5 and the overall score to 80.8%, which is worse for a learner. Reads as a 7B capability limit rather than wording. Case 5 (crediting "charged full price" without an explicit refund request) is the accepted English trade. |
| OPEN-07 | Coach misses Japanese particle error, reports "Perfectly natural!" | [`app/coach.py`](app/coach.py), [`eval/coach_cases.json`](eval/coach_cases.json) case 14 | **Open, unfixed.** Input `昨日、久しぶりに友達を会いました。` needs `友達に` / `友達と`. The coach returns `💡 Feedback: Perfectly natural!` — 5/5 in the eval and 3/3 on manual re-run. This is a *silent miss*: the learner's error passes uncorrected, the same false-clean failure class the project treats as worst in the judge. Added as a fixture in `f6fc457` alongside the judge findings, but never triaged or written up until now. |
| OPEN-08 | `check_all.sh` omits every LLM suite | [`scripts/check_all.sh`](scripts/check_all.sh), [`Makefile`](Makefile) | **Open.** The script and CI run only the deterministic gates. The coach/judge/actor/moods evals and the playtest live solely in the `Makefile` `eval` target and must be run by hand, so a fully green CI says nothing about coach, judge, or actor quality. Related hazard: `playtest_sample.py` resumes from its `--out` file by design, so re-running against an existing results file replays old numbers instantly without touching the model — a stale file can look like a fresh verification. Use a new `--out` path when verifying. |
| OPEN-09 | Playtest failure: Sc28 task 11 | [`app/scenarios/data/scenario_28.json`](app/scenarios/data/scenario_28.json) | **Needs triage.** Police Station Lost Property, goal "Confirm case reference number for follow-up status inquiries", `done_when` "Learner confirmed case reference number." The learner is never given a reference number, so they ask the NPC for one and the NPC asks them back; the turn budget runs out. Reads as a content bug (the task presumes information the scenario never supplies) rather than a judge bug. |
| OPEN-04 | MLX / Apple Silicon only | [`app/llm.py`](app/llm.py) | **Deliberate scope choice.** Runs directly against MLX on Apple Silicon without a backend abstraction layer (e.g. Ollama, vLLM). |
| OPEN-05 | JSON catalog storage / No authoring UI | [`app/scenarios/data/`](app/scenarios/data/) | **Deliberate scope choice.** Content is stored per-scenario as JSON files; authoring relies on JSON files and maintenance scripts rather than an authoring tool. |
| OPEN-06 | Language support limited to English & Japanese | [`app/cli.py`](app/cli.py) | **Deliberate scope choice.** UI localization, scenario content, and prompt structures support English and Japanese; Thai and other languages are not supported. |

## Recently Resolved

For historical commit logs and detailed change history, see `git log`. Key recent milestones include:

- **OPEN-02 Session resume — done** (`a2c6308`). An interrupted session can now be resumed; `3e0e7c4` followed up on resume noise.
- **OPEN-03 Progress view — done** (`df326e8`). A progress report ships and mastery is surfaced in the chooser, wired to `get_scenario_stats()` in [`app/db.py`](app/db.py).
- **CI and local gate** (`6870b6b`, `a386434`): GitHub Actions workflow plus [`scripts/check_all.sh`](scripts/check_all.sh); a build backend was declared so the editable install works.
- **Judge deterministic matching** (`101439f`): widened from words to phrases and enabled for Japanese.
- **Mood and complication coverage** (`942cb5e`): moods and complications are now exercised and measured.
- **Profile and CLI robustness** (`4a0b642`, `3256088`, `3e0e7c4`): typos no longer fork learner profiles, Ctrl+D/Ctrl+C exit cleanly, and the session-summary crash and 80-line chooser are fixed.
- **Scenario 2 Misalignment Fix:** Replaced 69 job-interview tasks under an airport scenario heading with true airport-relevant tasks.
- **Catalog-Wide Content Polish:** Eliminated near-duplicate goals, trivial vocabulary targets, and goal/`done_when` mismatches across all 5,520 tasks.
- **Actor Output Validation & Repair:** `call_actor` can no longer return text that fails `validate()`. `repair_actor_output` truncates over-length turns and `salvage_actor_output` drops closed yes/no questions, both preserving the vocab block; the diagnostic that used to print at the learner is now behind `DEBUG`.
- **Engine Robustness & Error Handling:** Lazy MLX model loading via `_ensure_model` with the original exception chained, replacing an import-time load whose bare `except` discarded the cause. `MLX_ERRORS` is deliberately **not** narrowed — `mlx-lm` documents no exception contract and [`app/cli.py`](app/cli.py) catches it at top-level boundaries to show a readable message instead of a traceback mid-conversation; the handlers re-raise under `DEBUG` so real bugs still surface.
- **JSON Migration & Codebase Infrastructure:** Migrated scenario data into per-scenario JSON files ([`app/scenarios/data/`](app/scenarios/data/)), simplified [`app/scenarios/builtins.py`](app/scenarios/builtins.py), added [`README.md`](README.md) and [`pyproject.toml`](pyproject.toml), and localized CLI outputs for English and Japanese.
