# Architecture — Language Conversation Coach CLI

Owned by `architect_agent`. Other agents read this; only `architect_agent`
writes it. Keep it describing what's true of the *committed* codebase, with
an explicit "In-flight changes" section for uncommitted work in progress —
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
- `main.py` — entrypoint; sets `HF_HUB_OFFLINE=1` before importing the app
  (see `bug_reports/infra.md#BUG-031` for why this breaks fresh installs).
- `app/cli.py` — turn loop, input handling (`skip`/`quit`), vocab-box
  rendering, session persistence calls.
- `app/llm.py` — model load (`mlx_lm.load`), `_llm_chat` (the shared
  MLX chat wrapper all three roles call through), actor system prompts
  (`ACTOR_SYS`, `GREETING_SYS`), output `sanitize()`/`validate()`.
- `app/coach.py` — `COACH_SYS` prompt, `filter_coach_output` post-processing.
- `app/judge.py` — `judge_deterministic` (regex/stem match), `judge_llm`
  (LLM-graded fallback), `evaluate_task` (entry point combining both).
- `app/scenarios/models.py` — `Scenario`/`Task` dataclasses.
- `app/scenarios/builtins.py` — the actual scenario/task content (69
  scenarios; see `bug_reports/task-data.md` for known content-quality gaps).
- `db.py` — SQLite session logging, `~/.language-coach/sessions.db`.

## 4. Model runtime
Local inference via `mlx-lm` (Apple Silicon), model
`mlx-community/Qwen2.5-7B-Instruct-4bit`, loaded once at import time in
`app/llm.py`. This replaced an earlier Ollama-based runtime
(`qwen3:8b` served via a local Ollama daemon) — see
`ADRs/ADR-001-ollama-to-mlx-migration.md`.

**Known trap:** the two runtimes use different option-dict keys
(`num_predict`/`num_ctx` for Ollama vs `max_tokens` for the MLX wrapper).
This already caused one real regression (judge/coach silently getting the
wrong token budget after the migration — `bug_reports/judge.md#BUG-011`).
When touching `_llm_chat` call sites, verify the options dict uses MLX-native
keys, not leftover Ollama ones.

## 5. In-flight changes (uncommitted, as of this writing)
The working tree has substantial uncommitted changes across nearly every
app file (`git status` / `git diff --stat`), including:
- Coach/judge bug fixes already applied — see `bug_reports/coach.md` and
  `bug_reports/judge.md` for which ones (marked FIXED-UNCOMMITTED).
- A large rewrite of `app/scenarios/builtins.py` (+2264 lines) and deletion
  of `app/scenarios/generator.py`.
- Two new **untracked** scripts not yet wired into the app:
  `scripts/fill_69_tasks.py` (LLM-driven task-content generator per
  scenario) and `scripts/ai_playtester.py` (an AI-learner-driven automated
  playtester that validates a generated task is actually completable before
  accepting it). This looks like an unfinished attempt at fixing
  `bug_reports/task-data.md#BUG-025` (63 of 69 scenarios were boilerplate
  clones) and is architecturally interesting: it's a hand-rolled precursor
  to what `content_designer_agent` (authoring) + `qa_agent` (validation)
  should own as a standing capability, not a one-off script.

**Action for `architect_agent`:** decide whether to finish and commit the
Ollama→MLX migration as one clean commit (with `bug_reports/infra.md#BUG-031`
and `#BUG-014` closed out first), and whether `fill_69_tasks.py`/
`ai_playtester.py` should be formalized into `content_designer_agent`'s and
`qa_agent`'s standing toolset rather than living as standalone scripts.
Record either decision as an ADR.

## 6. Test coverage
`tests/test_main.py`, `tests/test_generator.py` — also under uncommitted
change (`tests/test_generator.py` lost 188 lines, likely tracking the
`generator.py` deletion). `eval/coach_cases.json` holds behavioral regression
cases for the coach, run against the live model (see
`bug_reports/README.md` for how `qa_agent` should extend it).
