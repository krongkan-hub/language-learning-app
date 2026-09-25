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

English turns also run `apply_verbform_net`, which catches three verb-form
shapes the coach prompt would not (OPEN-39): he/she/it + "don't", "did" plus a
past form, and a past-time phrase with a present-tense verb from a closed
list. Like every net here it only overturns a CLEAN verdict, so a real model
correction always wins.

A fourth LLM call — a second opinion asking the model plainly whether the
sentence is correct — was built and measured against that net, and **rejected
despite scoring higher**: 58/60 against 50/60 on the recall probe. Asked
plainly about a short reply, the model rewrites style and sometimes breaks it,
turning "Yes," into "Sure," and "No problem." into "No problems.", which is
worse English than the learner wrote. The recall probe's clean arm was eight
full sentences and did not contain that shape. The coach suite did, and caught
it as case 72 falling 5/5 to 0/5. The lesson lives in the net's
must-stay-quiet fixtures now.

The judge is a three-stage chain dispatched by `evaluate_task`, cheapest first:
`judge_deterministic` (regex/stem match) → `judge_identifier_readback` (the goal
is to read back an identifier the NPC gave, so the real one must appear) →
`judge_llm` (LLM-graded fallback — the field calls this pattern **LLM-as-a-judge**,
here reached only after two deterministic stages fail to decide). `judge_llm`
re-checks a NO against the learner's sentence alone and lets a context-free YES
overturn it, except on multi-clause goals. The eval gate for this file
(`dev/check_evals.sh`, §6) tracks its false-negative and false-positive counts
separately from its score — an accurate term for that is **error-shape
gating**: a steady percentage can hide false negatives growing, and this
project treats a learner told they failed a task they completed as the worst
failure a verdict can produce.

The coach is the LLM call plus eight deterministic post-LLM nets in
`app/coach/` (`apply_particle_net`, `apply_transitivity_net`,
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
exists then fires on it. The nets plus `filter_coach_output` are what a reader
coming from elsewhere would call **deterministic guardrails on model output**:
rule-based, run after generation, and — per the invariant above — permitted
only to add a correction, never to remove or override one the model made.

The actor has **two** output paths and they are not interchangeable:
`call_actor` assembles a whole turn and validates it, retrying up to 3× then
salvaging then falling back; `stream_actor` emits sentence-by-sentence and is
the path the learner actually reads. Both dispatch to the single per-sentence
rule set in `sentence_rejection_reason` — they each carried their own copy
until 2026-09-05, and the copies had silently diverged. Named as a pattern,
`validate()` plus that retry → repair → salvage → fallback sequence is
**graded output validation with fallback**: each stage is strictly cheaper and
less faithful to the model's own words than the one before it, and
`call_actor` is guaranteed to return something that passes `validate()` even
when every stage before the fallback line fails.

### Explain mode

A second thing to do, beside the roleplay scenarios: the learner explains
something and someone listens. `app/explain.py` plus `app/explain_topics.json`
(10 topics x 5 points, authored in both languages).

It shares everything below the front end — same session object, same drill,
same coach, same summary, same SSE contract. Three differences:

- **The listener's verdict replaces the task judge.** Deciding whether the
  point landed IS the grading, so a turn costs TWO model calls, not three.
- **The opening costs no model call at all.** There is nothing to react to yet
  and the topic is authored text, so the learner sees the screen immediately
  instead of waiting ~10s for small talk.
- **`listen()` fails open.** Given nothing usable it ACCEPTS the point, because
  this mode has no skip: too generous costs one practice opportunity, stuck
  costs the session.

The mechanic is the listener not understanding. A vague point gets a question
about exactly what is missing, and the learner says it again in other words.

**The instruction is authored per language and never translated at runtime**,
and that is measured, not stylistic. With an English instruction over Japanese
content the listener asked back at 5 of 6 already-CLEAR answers — the failure
that makes the mode a nag. With the instruction in Japanese, 2 of 6; English
content with an English instruction, 0 of 6. Splitting the decision into a
separate tiny "YES or NO" call was also tried and is worse in the other
direction: it let 5 of 6 vague answers through, the same shape as the 1.5B
judge that once returned 24/24 false positives.

### Vocabulary retrieval

`app/retrieval.py` picks which previously-taught words the NPC is nudged to
reuse. A word gets logged to `vocab_log` when it is taught and, without this,
never comes back: `times_correct` sits at 0 and the learner meets each word
once. The selection is what a reader coming from elsewhere would call
**semantic retrieval, or embedding-based ranking** — RAG-style, but the corpus
being retrieved over is the learner's own vocabulary history, not documents.
The query is the scenario the learner is entering (place + role + a few
goals); the corpus is that user's due words (`times_correct < 3`); both are
embedded with `intfloat/multilingual-e5-small` (118M params, English and
Japanese in one space) and ranked by cosine similarity, so a word fits the
conversation it gets reintroduced into rather than just being old.

**Deliberately not a vector database.** The corpus is one learner's rows —
hundreds, thousands at the extreme — and a brute-force dot product over that
is microseconds in numpy, so `app/retrieval.py`'s own docstring is explicit
that Pinecone or Weaviate would add a network service and a schema to keep in
sync to answer a query that fits in L2 cache. The vector lives in
`vocab_log.embedding`, a JSON-text column next to the row it belongs to, read
back by `db.due_words_for`.

**Optional by design.** `mlx-embeddings` is an extra package, not a runtime
dependency (see [README.md](../README.md#installation)); without it,
`due_words_for` falls back to least-recently-seen, which is what the app did
before retrieval existed, and `app/` still installs with a single runtime
dependency (`mlx-lm`).

## 3. File map
- `main.py` — entrypoint; sets `HF_HUB_OFFLINE=1` only if the model cache directory already exists before importing the app.
- `app/cli.py` — turn loop, input handling (`skip`/`quit`), vocab-box rendering, session persistence calls.
- `app/llm/` — lazy model loading (`_ensure_model`), `_llm_chat` (shared MLX chat wrapper), actor system prompts (`ACTOR_SYS`, `GREETING_SYS`), output `sanitize()`, `validate()`, `repair_actor_output()` (over-length truncation), `salvage_actor_output()` (drops closed yes/no questions, re-attaches vocab block), and `call_actor` (guaranteed never to return text that fails `validate()`).
- `app/coach/` — `COACH_SYS` prompt, the optional `COACH_SITUATION` block, `filter_coach_output` post-processing, and the deterministic post-LLM nets that catch Japanese classes the model calls natural.
- `app/judge.py` — `judge_deterministic`, `judge_identifier_readback`, `judge_llm`, and `evaluate_task` (the entry point chaining all three).
- `app/session.py` — builds the actor/greeting system prompts (`build_actor_system_prompt`, `build_greeting_system_prompt`) and produces a turn.
- `app/i18n.py` — UI string table and lookup (`t`), plus `scenario_name`/`scenario_place` translation accessors and `normalize_language`.
- `app/scenarios/models.py` — `Scenario`/`Task` dataclasses.
- `app/scenarios/builtins.py` — a 56-line **loader**: reads `app/scenarios/data/scenario_*.json` into `Scenario`/`Task` objects and exposes `SCENARIOS`. The content itself lives in those 80 JSON files (80 scenarios × 69 tasks = 5,520 tasks), not in this module.
- `app/retrieval.py` — semantic retrieval over the learner's own taught vocabulary: `embed`, `cosine`, `rank_by_similarity`, `scenario_query`; falls back to arrival order (least-recently-seen) with the optional `mlx-embeddings` package absent.
- `app/db.py` — SQLite session logging (`~/.language-coach/sessions.db`), including `vocab_log.embedding` and `due_words_for` (the retrieval read path).
- `app/web.py` — the browser front end: a FastAPI app, a per-session state machine, and an SSE stream. Holds no conversation logic of its own; it drives the same `session`/`llm`/`coach`/`judge` calls the CLI does, in the same order.
- `app/static/index.html` — the whole UI, one file, no build step: markup, CSS and the client that consumes the SSE stream.

## 4. Model runtime
Local inference via `mlx-lm` (Apple Silicon), model `mlx-community/Qwen2.5-7B-Instruct-4bit` — **on-device quantised inference**, in the field's term: the 7B model runs 4-bit-quantised entirely on the Mac's own GPU, no network call, no server. The model is loaded lazily on first use via `_ensure_model()` in `app/llm/` using thread-safe double-checked locking, cached for subsequent calls, and on failure raises a `RuntimeError` naming `BASE_MODEL` with the original exception chained. Importing `app.llm` no longer touches the model at all.

**Prompt cache (KV-cache) reuse.** `app/llm/client.py` keeps one MLX prompt
cache per `cache_key` (`actor`, `coach`, `judge`, `judge_confirm`), each capped
at `PROMPT_CACHE_MAX_KV_SIZE` tokens. `_prepare_prompt_cache_for_call` finds
the longest common token prefix between the new prompt and what that key
cached last time, trims the cache to that prefix with `trim_prompt_cache`, and
replays only the new suffix — so a call sharing most of its prompt with the
previous one (the same system prompt plus one more turn of history, which is
the common case here) does not re-process tokens it already generated a KV
state for. `PROMPT_CACHE_MAX_ENTRIES` bounds how many keys are held at once,
evicting the least-recently-used.

This replaced an earlier Ollama-based runtime (`qwen3:8b` served via a local Ollama daemon) — see `docs/ADRs/ADR-001-ollama-to-mlx-migration.md`.

**Known trap:** the two runtimes use different option-dict keys (`num_predict`/`num_ctx` for Ollama vs `max_tokens` for the MLX wrapper). This already caused one real regression (judge/coach silently getting the wrong token budget after the migration — `docs/bug_reports/judge.md#BUG-011`). When touching `_llm_chat` call sites, verify the options dict uses MLX-native keys, not leftover Ollama ones.

## 5. The web front end

`make web` (optional extra: `pip install -e ".[web]"`). The CLI runs without
fastapi or uvicorn installed, so a CLI-only install keeps the single
runtime-dependency property the project started with.

It exists for a reason that is not cosmetic: **coach feedback scrolls away in
a terminal.** The coach was taken from 69% to 84% on the Japanese arm, and
none of that reaches a learner who does not read it. A panel that stays on
screen is the point. A turn also costs 9-11s across three `_llm_lock`-
serialised calls, and SSE gives **token/sentence streaming** — the NPC's reply
arrives sentence-by-sentence as `stream_actor` produces it, rather than the
browser waiting for the whole turn (actor generation, then coach, then judge)
before showing anything.

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

**`make check` → `dev/check_all.sh`** — the fast deterministic gate, and the
one CI runs (the workflow calls this script rather than relisting its steps, so
the two cannot drift). Runs in seconds:

| Check | What it holds |
| :--- | :--- |
| `pytest` | the unit suite |
| `pyflakes` | `app/ dev/ dev/tests/ main.py` |
| `check_task_depth.py` | structural task depth, required-field distribution, exact catalog total; warns (does not fail) on goals duplicated across scenarios |
| `check_scenario_parity.py` | scene-hint / reactive / advanced / vocabulary ratios against the flagship scenarios |
| `check_content_coherence.py` | topic-setting mismatch, trivial or venue-naming vocabulary, cross-scenario vocabulary reuse, near-duplicate goals, goal/`done_when` alignment |
| `check_catalog_roundtrip.py` | the catalog hashes to a known sha256 after a load/dump cycle |
| `check_fixture_contamination.py` | no eval fixture is quoted verbatim in the prompt it grades |
| `check_rule_vacuity.py` | no validation rule is silently inert on Japanese — parity, non-vacuity, punctuation normalization, and the ~160 scenario translation strings |
| `check_actor_path_parity.py` | `call_actor`'s assembly and `stream_actor` treat the SAME bytes identically — a vocab card survives on both paths or neither. Deterministic and model-free: `stream_actor` takes `generator_fn`, so both are fed captured text. The two paths diverged twice (`0df1d3f`, OPEN-31) and nothing could see it |
| coverage floor | `app/` at ≥80% |

**`make check-evals` → `dev/check_evals.sh`** — the LLM-graded gate: an
**offline evaluation suite run as a regression gate**, in the field's term —
a fixed labelled case set per suite, scored against a floor, a drop fails the
build. Nine suites are gated by default (`dev/evals/eval_coach.py`,
`eval_judge.py`, `eval_actor.py`, `eval_moods.py`, `eval_coachreason.py`,
`eval_coachrecall.py`, `eval_explain.py`, `eval_jarecall.py`,
`eval_jalength.py`) scored against `dev/fixtures/eval_baselines.json`. Kept
out of `check_all.sh` and out of CI on purpose: each needs MLX with the 7B
loaded and together they take minutes. Run it before shipping anything
touching a prompt, the judge, the coach, or the actor. The judge additionally
gates on its false-negative and false-positive counts separately, because a
steady score can hide false negatives growing — a learner who completed the
task being told they did not is the failure this project treats as worst.

`dev/evals/eval_jarecall.py` measures Japanese error classes that no fixture
and no net covered — いる/ある animacy, な-adjective + の, い-adjective +
じゃない, い-adjective used adverbially, relative time word + に, で with an
existence verb — reaching 100% (60/60) after six new nets, against 20/60
before them. `dev/evals/eval_jalength.py` gates only the long arm of a
short/long/clean split, since long-arm recall is trivially raised by
correcting everything; the short and clean arms fail the suite outright
instead of being traded against the gated number. Both suites, like
`eval_coachrecall.py`, report **F0.5** (`dev/evals/fhalf.py`) — the GEC
field's precision-weighted metric, `1.25·P·R / (0.25·P + R)`, which counts a
wrong correction only as a recall miss here rather than as both a false
positive and a false negative the way ERRANT's edit-alignment scoring does;
the module docstring says why that makes this project's precision read
slightly high, and the clean arm each suite runs is what keeps that honest.
Using the field's own metric rather than a private score means these numbers
are comparable to published GEC results, not just to this project's own past
runs.

`dev/evals/eval_coachrecall.py` measures the opposite failure to every other
coach check: not a wrong correction, but no correction at all. Twelve clear
English errors in classes `coach_cases.json` never covered — subject-verb
agreement, simple past, auxiliary plus bare verb, determiner, ditransitive.
Read it WITH its clean arm, never alone: recall is trivially raised by
correcting everything, and the design that scored BEST on it is the one that
had to be reverted (see the turn-order section). That clean arm is eight full
sentences and has already proven too narrow once.

`dev/evals/eval_coachreason.py` reads the part of the coach's output that
`eval_coach.py` never looks at: the bracketed **reason** beside a correction.
That blind spot is how the coach could correct `"how much it cost"` →
`"how much it costs"` and explain it as *"use the base form of the verb"* —
right fix, backwards rule — while the suite stayed green. Its checks are
per-case predicates rather than one word list, because `"base form"` is a false
claim about `costs` and a true one about `open` in `"want to open"`. Only runs
that reached the correction are graded, since a reason cannot be wrong about a
correction never made, so it fails loudly below `GRADED_FLOOR` rather than let a
shrinking denominator flatter the score. Two of its eight cases are controls
where the template IS the true rule: losing one of those corrections fails the
suite outright, because suppressing the template everywhere would score 100%
while making the coach worse.

`dev/evals/eval_rawactor.py` scores the actor's **first generation only** — no
retry, salvage or fallback — because the other gated suites all measure the
repair pipeline (see the graded-output-validation note in §2) and cannot see
the actor itself regress while repair covers for it. It is deliberately
**ungated**: at 48 samples the binomial standard error is about 7 points, so a
floor loose enough to survive the noise would catch nothing. Read it as a
level and, more usefully, as a distribution of rejection reasons — that says
*which* rule the actor trips, which no repaired score can. It has already
shown that `Closed yes/no question` is the largest raw failure class, invisible
downstream because `salvage_actor_output` strips exactly those sentences.

`dev/tools/probe_jfleg.py` is evaluation against an external public
benchmark, in the field's term — JFLEG, 1,501 English sentences written by
real learners and corrected by four native annotators (Napoles et al., EACL
2017). Every fixture in `dev/fixtures` was authored by this project, so this
is the one check of the coach against errors nobody here thought of; it is
not vendored (CC BY-NC-SA 4.0, downloaded to a scratch directory at run time)
and, like `eval_rawactor.py`, is run by hand rather than gated.

`dev/playtest/ai_playtester.py` (`make playtest`) drives a simulated learner through
a scenario to check tasks are winnable. It is the ADR-003 acceptance gate before
any change under `app/scenarios/data/` merges, and it is enforced by people
rather than machinery: it needs the 7B model and costs minutes per scenario, so
it is in neither gate.

## 7. Test coverage
591 tests across five files — `dev/tests/test_main.py`, `dev/tests/test_cli_session.py`,
`dev/tests/test_web.py`, `dev/tests/test_generator.py`, `dev/tests/test_playtester.py` —
running in about two seconds now that model loading is lazy. Coverage of `app/`
is 86%, floored at 80% by the gate.

A note on the web tests, because the obvious way to write them does not work:
an SSE response never completes, so `TestClient.stream(...)` waits for an end
that never comes and hangs the suite. `dev/tests/test_web.py` drives the response's
async generator directly and closes it, which is what a dropped client does.

Behavioural regression cases for the LLM roles live in `dev/fixtures/`
(`coach_cases.json` 72 cases, `judge_cases.json` 30, `actor_cases.json` 20;
`eval_moods.py` generates its own 96 samples, `eval_coachreason.py` its own 8). These run against the live model
via `check_evals.sh`, not in `check_all.sh`. `dev/evals/eval_rawactor.py` sits
beside them and is deliberately **ungated**: it scores the actor's first
generation with no retry or salvage, and at 48 samples the binomial standard
error is about 7 points, so a floor loose enough to survive the noise would
catch nothing. Read it as a level and a distribution of rejection reasons —
that is how `Closed yes/no question` was found to be the largest raw failure
class, invisible downstream because `salvage_actor_output` strips exactly those
sentences. See `docs/bug_reports/README.md` for how
`qa_agent` should extend them, and note `check_fixture_contamination.py`: six
coach fixtures are quoted verbatim in `COACH_SYS` and are tagged
`prompt_example` and excluded from the headline score, because a fixture the
prompt hands the model the answer to cannot fail.
