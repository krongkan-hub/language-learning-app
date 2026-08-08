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
(task-completion check, first tried via `judge_deterministic`'s regex/word
match, falling back to `judge_llm`). All three currently hit the same local
MLX model instance — see `app/llm.py:_llm_chat`.

## 3. File map
- `main.py` — entrypoint; sets `HF_HUB_OFFLINE=1` only if the model cache directory already exists before importing the app.
- `app/cli.py` — turn loop, input handling (`skip`/`quit`), vocab-box rendering, session persistence calls.
- `app/llm.py` — lazy model loading (`_ensure_model`), `_llm_chat` (shared MLX chat wrapper), actor system prompts (`ACTOR_SYS`, `GREETING_SYS`), output `sanitize()`, `validate()`, `repair_actor_output()` (over-length truncation), `salvage_actor_output()` (drops closed yes/no questions, re-attaches vocab block), and `call_actor` (guaranteed never to return text that fails `validate()`).
- `app/coach.py` — `COACH_SYS` prompt, `filter_coach_output` post-processing.
- `app/judge.py` — `judge_deterministic` (regex/stem match), `judge_llm` (LLM-graded fallback), `evaluate_task` (entry point combining both).
- `app/scenarios/models.py` — `Scenario`/`Task` dataclasses.
- `app/scenarios/builtins.py` — built-in scenario and task content (80 scenarios of 69 tasks each, 5,520 tasks total).
- `app/db.py` — SQLite session logging (`~/.language-coach/sessions.db`).

## 4. Model runtime
Local inference via `mlx-lm` (Apple Silicon), model `mlx-community/Qwen2.5-7B-Instruct-4bit`. The model is loaded lazily on first use via `_ensure_model()` in `app/llm.py` using thread-safe double-checked locking, cached for subsequent calls, and on failure raises a `RuntimeError` naming `BASE_MODEL` with the original exception chained. Importing `app.llm` no longer touches the model at all.

This replaced an earlier Ollama-based runtime (`qwen3:8b` served via a local Ollama daemon) — see `ADRs/ADR-001-ollama-to-mlx-migration.md`.

**Known trap:** the two runtimes use different option-dict keys (`num_predict`/`num_ctx` for Ollama vs `max_tokens` for the MLX wrapper). This already caused one real regression (judge/coach silently getting the wrong token budget after the migration — `bug_reports/judge.md#BUG-011`). When touching `_llm_chat` call sites, verify the options dict uses MLX-native keys, not leftover Ollama ones.

## 5. Quality tooling
- `scripts/check_task_depth.py` — verifies structural task depth and required field distribution across scenarios, catching placeholder strings and duplicate goals (Scenarios 1, 3, 4, and 5 fail by design as legacy content).
- `scripts/check_scenario_parity.py` — validates scenario structural metrics (scene hint, reactive, advanced, and vocabulary task ratios) against flagship reference standards (Scenarios 1-6 & 70).
- `scripts/check_content_coherence.py` — enforces content quality across scenarios by guarding against topic/setting mismatches, trivial or venue-naming vocabulary targets, cross-scenario vocabulary reuse, near-duplicate goals, and goal/`done_when` misalignment.

## 6. Test coverage
Automated unit tests across three test files — `tests/test_main.py`, `tests/test_generator.py`, and `tests/test_playtester.py` — provide 106 passing tests, running in under a second now that model loading is lazy. `eval/coach_cases.json` holds behavioral regression cases for the coach, run against the live model (see `bug_reports/README.md` for how `qa_agent` should extend it).
