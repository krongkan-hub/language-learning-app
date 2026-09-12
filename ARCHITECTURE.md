# Architecture — Language Conversation Coach

Owned by `architect_agent`. Other agents read this; only `architect_agent`
writes it. Keep it describing what's true of the *committed* codebase —
don't let this drift into aspirational documentation.

## 1. Purpose
A local app that role-plays scenario-based conversations (coffee shop,
pharmacy, job interview, ...) with a learner practicing a target language,
gives grammar feedback per turn, and grades whether the learner accomplished
each scenario's task objectives.

It has **two front ends over one core**. `app/cli.py` is the original and the
one the eval harnesses drive; `app/web.py` serves a browser UI. Everything
below the front end — `session`, `llm`, `coach`, `judge`, `db`, `i18n` — is
shared and knows about neither.

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
              app/cli.py or app/web.py orchestrates the turn loop and
              delivers actor reply + coach feedback + task status
```

Three independent LLM calls per learner turn: **actor** (NPC dialogue),
**coach** (grammar feedback on the learner's message), **judge**
(task-completion check). All three hit the same local MLX model instance
through `app/llm.py:_llm_chat`, serialized by `_llm_lock`.

**They run judge → actor → coach, and the order is load-bearing in both
directions.** The judge must come first because the actor's system prompt
depends on its verdict: a completed task advances the index that picks the
next task, or the wrap-up prompt on the final one. The coach must come last
because it has no such dependency, and running it first meant the learner
watched a spinner through the whole turn before any dialogue appeared —
measured at 7.7-9.1s of silence out of a 9-11s turn (`7e312f0`). Both front
ends follow it.

The judge is a three-stage chain dispatched by `evaluate_task`, cheapest first:
`judge_deterministic` (regex/stem match) → `judge_identifier_readback` (the goal
is to read back an identifier the NPC gave, so the real one must appear) →
`judge_llm` (LLM-graded fallback). `judge_llm` re-checks a NO against the
learner's sentence alone and lets a context-free YES overturn it, except on
multi-clause goals.

The coach is the LLM call plus eight deterministic post-LLM nets in
`app/coach.py` (`apply_particle_net`, `apply_transitivity_net`,
`apply_counter_net`, `apply_conjugation_net`, `apply_register_net`,
`apply_word_order_net`, `apply_collocation_net`, `apply_apology_net`), chained
in `coach_feedback` and each returning early once one has fired. They exist
because the 7B model calls certain Japanese errors natural with total
consistency — the same cases score 0/5 run after run, which is what makes them
catchable in code at all.

**Every net only ever overturns a CLEAN verdict.** A real correction from the
model always wins, so a net can never tell a learner that correct Japanese is
wrong — the failure this project treats as worse than missing an error. That
invariant is load-bearing and constrains what a net can fix: where the model
returns a confidently *wrong* correction, every net stands down by design, and
the fix has to be made in `COACH_SYS` instead. Two such prompt fixes are in the
tree, and both work by the same indirect route — they stop the model producing
a wrong correction, the verdict comes back clean, and the net that already
exists then fires on it.

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
- `app/web.py` — the browser front end: a FastAPI app, a per-session state machine, and an SSE stream. Holds no conversation logic of its own; it drives the same `session`/`llm`/`coach`/`judge` calls the CLI does, in the same order.
- `app/static/index.html` — the whole UI, one file, no build step: markup, CSS and the client that consumes the SSE stream.

## 4. Model runtime
Local inference via `mlx-lm` (Apple Silicon), model `mlx-community/Qwen2.5-7B-Instruct-4bit`. The model is loaded lazily on first use via `_ensure_model()` in `app/llm.py` using thread-safe double-checked locking, cached for subsequent calls, and on failure raises a `RuntimeError` naming `BASE_MODEL` with the original exception chained. Importing `app.llm` no longer touches the model at all.

This replaced an earlier Ollama-based runtime (`qwen3:8b` served via a local Ollama daemon) — see `ADRs/ADR-001-ollama-to-mlx-migration.md`.

**Known trap:** the two runtimes use different option-dict keys (`num_predict`/`num_ctx` for Ollama vs `max_tokens` for the MLX wrapper). This already caused one real regression (judge/coach silently getting the wrong token budget after the migration — `bug_reports/judge.md#BUG-011`). When touching `_llm_chat` call sites, verify the options dict uses MLX-native keys, not leftover Ollama ones.

## 5. The web front end

`make web` (optional extra: `pip install -e ".[web]"`). The CLI runs without
fastapi or uvicorn installed, so a CLI-only install keeps the single
runtime-dependency property the project started with.

It exists for a reason that is not cosmetic: **coach feedback scrolls away in
a terminal.** The coach was taken from 69% to 84% on the Japanese arm, and
none of that reaches a learner who does not read it. A panel that stays on
screen is the point. A turn also costs 9-11s across three `_llm_lock`-
serialised calls, and SSE lets the NPC's reply arrive before the coach verdict
rather than after it.

**Turn order is the CLI's, for the CLI's reason.** judge → actor → coach. The
judge must precede the actor because a completed task advances the index that
selects the next task, or the wrap-up prompt on the final one; the coach
follows the actor so the reply reaches the learner first (`7e312f0`).

**The state machine is the front end's only real logic.** A session is
`AWAITING_INPUT → BUSY → (DRILL) → AWAITING_INPUT`, and the correction drill
is enforced **server-side**: `POST /api/turn` answers 409 while a drill is
open. `run_correction_drill` is a `while True` with no skip in the CLI, and
disabling an input box would leave that bypassable from the browser console.

**Things that are deliberately absent.** There is no resume: no table stores
message text, so a resume could only show a half-ticked task list above an
empty transcript. What resume is for — not losing the tasks you were working
on — happens through the same `retry_goals` path the CLI uses. The scenario is
drawn for the learner from the least-played band rather than chosen, and
browsing all 80 is secondary.

**Sessions close themselves.** The SSE stream ending is taken as the signal
that nobody is watching, and the session is written out with whatever progress
it had. Before that, closing a tab left the row unfinished forever; 13 had
accumulated.

## 6. Quality tooling
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
| `check_actor_path_parity.py` | `call_actor`'s assembly and `stream_actor` treat the SAME bytes identically — a vocab card survives on both paths or neither. Deterministic and model-free: `stream_actor` takes `generator_fn`, so both are fed captured text. The two paths diverged twice (`0df1d3f`, OPEN-31) and nothing could see it |
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

`scripts/eval_rawactor.py` scores the actor's **first generation only** — no
retry, salvage or fallback — because the four gated suites all measure the
repair pipeline and cannot see the actor itself regress while repair covers for
it. It is deliberately **ungated**: at 48 samples the binomial standard error is
about 7 points, so a floor loose enough to survive the noise would catch
nothing. Read it as a level and, more usefully, as a distribution of rejection
reasons — that says *which* rule the actor trips, which no repaired score can.
It has already shown that `Closed yes/no question` is the largest raw failure
class, invisible downstream because `salvage_actor_output` strips exactly those
sentences.

`scripts/ai_playtester.py` (`make playtest`) drives a simulated learner through
a scenario to check tasks are winnable. It is the ADR-003 acceptance gate before
any change under `app/scenarios/data/` merges, and it is enforced by people
rather than machinery: it needs the 7B model and costs minutes per scenario, so
it is in neither gate.

## 7. Test coverage
478 tests across five files — `tests/test_main.py`, `tests/test_cli_session.py`,
`tests/test_web.py`, `tests/test_generator.py`, `tests/test_playtester.py` —
running in about two seconds now that model loading is lazy. Coverage of `app/`
is 86%, floored at 80% by the gate.

A note on the web tests, because the obvious way to write them does not work:
an SSE response never completes, so `TestClient.stream(...)` waits for an end
that never comes and hangs the suite. `tests/test_web.py` drives the response's
async generator directly and closes it, which is what a dropped client does.

Behavioural regression cases for the LLM roles live in `eval/`
(`coach_cases.json` 72 cases, `judge_cases.json` 30, `actor_cases.json` 20;
`eval_moods.py` generates its own 96 samples). These run against the live model
via `check_evals.sh`, not in `check_all.sh`. `scripts/eval_rawactor.py` sits
beside them and is deliberately **ungated**: it scores the actor's first
generation with no retry or salvage, and at 48 samples the binomial standard
error is about 7 points, so a floor loose enough to survive the noise would
catch nothing. Read it as a level and a distribution of rejection reasons —
that is how `Closed yes/no question` was found to be the largest raw failure
class, invisible downstream because `salvage_actor_output` strips exactly those
sentences. See `bug_reports/README.md` for how
`qa_agent` should extend them, and note `check_fixture_contamination.py`: six
coach fixtures are quoted verbatim in `COACH_SYS` and are tagged
`prompt_example` and excluded from the headline score, because a fixture the
prompt hands the model the answer to cannot fail.
