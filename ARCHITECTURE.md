# Architecture — Language Conversation Coach CLI

Owned by `architect_agent`. Other agents read this; only `architect_agent`
writes it. Keep it describing what's true of the *committed* codebase —
don't let this drift into aspirational documentation.

## 1. Purpose
A local CLI that role-plays scenario-based conversations (coffee shop,
pharmacy, job interview, ...) with a learner practicing a target language,
gives grammar feedback per turn, and grades whether the learner accomplished
each scenario's task objectives.

## 2. Pipeline
```
learner input
     │
     ▼
┌─────────┐   scene/task setup    ┌──────────┐
│  actor   │◄──────────────────── │   task    │  (app/scenarios/*)
│ (NPC)    │   greeting/reply      │  state    │
└────┬─────┘                      └──────────┘
     │ NPC reply
     ▼
┌─────────┐                    ┌──────────┐
│  coach   │  grammar feedback  │  judge    │  task-completion verdict
│          │  on learner input  │           │  (deterministic → LLM fallback)
└─────────┘                    └──────────┘
     │                              │
     └──────────────┬───────────────┘
                     ▼
              app/cli.py orchestrates the turn loop, prints
              actor reply + coach feedback + task status
```

Three independent LLM calls per learner turn: **actor** (NPC dialogue),
**coach** (grammar feedback on the learner's message), **judge**
(task-completion check). All three hit the same local MLX model instance
through `app/llm.py:_llm_chat`, serialized by `_llm_lock`.

The judge is a three-stage chain dispatched by `evaluate_task`, cheapest first:
`judge_deterministic` (regex/stem match) → `judge_identifier_readback` (the goal
is to read back an identifier the NPC gave, so the real one must appear) →
`judge_llm` (LLM-graded fallback). `judge_llm` re-checks a NO against the
learner's sentence alone and lets a context-free YES overturn it, except on
multi-clause goals.

The actor has **two** output paths and they are not interchangeable:
`call_actor` assembles a whole turn and validates it, retrying up to 3× then
salvaging then falling back; `stream_actor` emits sentence-by-sentence and is
the path the learner actually reads. Both dispatch to the single per-sentence
rule set in `sentence_rejection_reason` — they each carried their own copy
until 2026-09-05, and the copies had silently diverged.

## 3. File map
- `main.py` — entrypoint; sets `HF_HUB_OFFLINE=1` only if the model cache directory already exists before importing the app.
- `app/cli.py` — turn loop, input handling (`skip`/`quit`), vocab-box rendering, session persistence calls.
- `app/llm.py` — lazy model loading (`_ensure_model`), `_llm_chat` (shared MLX chat wrapper), actor system prompts (`ACTOR_SYS`, `GREETING_SYS`), output `sanitize()`, `validate()`, `repair_actor_output()` (over-length truncation), `salvage_actor_output()` (drops closed yes/no questions, re-attaches vocab block), and `call_actor` (guaranteed never to return text that fails `validate()`).
- `app/coach.py` — `COACH_SYS` prompt, the optional `COACH_SITUATION` block, `filter_coach_output` post-processing, and the deterministic post-LLM nets that catch Japanese classes the model calls natural.
- `app/judge.py` — `judge_deterministic`, `judge_identifier_readback`, `judge_llm`, and `evaluate_task` (the entry point chaining all three).
- `app/session.py` — builds the actor/greeting system prompts (`build_actor_system_prompt`, `build_greeting_system_prompt`) and produces a turn.
- `app/i18n.py` — UI string table and lookup (`t`), plus `scenario_name`/`scenario_place` translation accessors and `normalize_language`.
- `app/scenarios/models.py` — `Scenario`/`Task` dataclasses.
- `app/scenarios/builtins.py` — a 56-line **loader**: reads `app/scenarios/data/scenario_*.json` into `Scenario`/`Task` objects and exposes `SCENARIOS`. The content itself lives in those 80 JSON files (80 scenarios × 69 tasks = 5,520 tasks), not in this module.
- `app/db.py` — SQLite session logging (`~/.language-coach/sessions.db`).

## 4. Model runtime
Local inference via `mlx-lm` (Apple Silicon), model `mlx-community/Qwen2.5-7B-Instruct-4bit`. The model is loaded lazily on first use via `_ensure_model()` in `app/llm.py` using thread-safe double-checked locking, cached for subsequent calls, and on failure raises a `RuntimeError` naming `BASE_MODEL` with the original exception chained. Importing `app.llm` no longer touches the model at all.

This replaced an earlier Ollama-based runtime (`qwen3:8b` served via a local Ollama daemon) — see `ADRs/ADR-001-ollama-to-mlx-migration.md`.

**Known trap:** the two runtimes use different option-dict keys (`num_predict`/`num_ctx` for Ollama vs `max_tokens` for the MLX wrapper). This already caused one real regression (judge/coach silently getting the wrong token budget after the migration — `bug_reports/judge.md#BUG-011`). When touching `_llm_chat` call sites, verify the options dict uses MLX-native keys, not leftover Ollama ones.

## 5. Quality tooling
Two gates, deliberately separated by cost.

**`make check` → `scripts/check_all.sh`** — the fast deterministic gate, and the
one CI runs (the workflow calls this script rather than relisting its steps, so
the two cannot drift). Runs in seconds:

| Check | What it holds |
| :--- | :--- |
| `pytest` | the unit suite |
| `pyflakes` | `app/ scripts/ tests/ main.py` |
| `check_task_depth.py` | structural task depth, required-field distribution, exact catalog total; warns (does not fail) on goals duplicated across scenarios |
| `check_scenario_parity.py` | scene-hint / reactive / advanced / vocabulary ratios against the flagship scenarios |
| `check_content_coherence.py` | topic-setting mismatch, trivial or venue-naming vocabulary, cross-scenario vocabulary reuse, near-duplicate goals, goal/`done_when` alignment |
| `check_catalog_roundtrip.py` | the catalog hashes to a known sha256 after a load/dump cycle |
| `check_fixture_contamination.py` | no eval fixture is quoted verbatim in the prompt it grades |
| `check_rule_vacuity.py` | no validation rule is silently inert on Japanese — parity, non-vacuity, punctuation normalization, and the ~160 scenario translation strings |
| coverage floor | `app/` at ≥80% |

**`make check-evals` → `scripts/check_evals.sh`** — the LLM-graded gate. Four
suites (`scripts/eval_coach.py`, `eval_judge.py`, `eval_actor.py`,
`eval_moods.py`) scored against `eval/eval_baselines.json`. Kept out of
`check_all.sh` and out of CI on purpose: each needs MLX with the 7B loaded and
the four together take minutes. Run it before shipping anything touching a
prompt, the judge, the coach, or the actor. The judge additionally gates on its
false-negative and false-positive counts separately, because a steady score can
hide false negatives growing — a learner who completed the task being told they
did not is the failure this project treats as worst.

`scripts/ai_playtester.py` (`make playtest`) drives a simulated learner through
a scenario to check tasks are winnable; it is manual and wired into neither
gate (ADR-003).

## 6. Test coverage
370 tests across four files — `tests/test_main.py`, `tests/test_cli_session.py`,
`tests/test_generator.py`, `tests/test_playtester.py` — running in about a
second now that model loading is lazy. Coverage of `app/` is 86%, floored at
80% by the gate.

Behavioural regression cases for the LLM roles live in `eval/`
(`coach_cases.json` 72 cases, `judge_cases.json` 30, `actor_cases.json` 20;
`eval_moods.py` generates its own 96 samples). These run against the live model
via `check_evals.sh`, not in `check_all.sh`. See `bug_reports/README.md` for how
`qa_agent` should extend them, and note `check_fixture_contamination.py`: six
coach fixtures are quoted verbatim in `COACH_SYS` and are tagged
`prompt_example` and excluded from the headline score, because a fixture the
prompt hands the model the answer to cannot fail.
