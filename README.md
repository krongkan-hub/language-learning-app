# Language Conversation Coach

A command-line language-conversation coach for practicing English. The learner role-plays realistic scenarios (such as checking in at an airport or negotiating with a landlord) against a locally-run Large Language Model.

On each turn, three internal roles process the interaction: an **Actor** that plays the NPC in character, a **Coach** that provides grammar and phrasing feedback on the learner's English, and a **Judge** that evaluates whether the learner accomplished the task's goal. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#2-pipeline) §2 for details on the execution pipeline.

> [!IMPORTANT]
> **Hardware Requirement: Apple Silicon Mac (M-Series)**  
> This application uses [MLX](https://github.com/ml-explore/mlx) for local model inference, which is Apple-Silicon-only. It was developed and tested on an Apple Silicon Mac with 16 GB RAM. On a 16 GB machine, ensure only one inference process runs at a time.

---

## Architecture at a glance

A one-minute map from what this codebase does to the names the field already
has for it. The standard term is not a rebrand — each row only claims it where
the code actually does the thing; the project's own reasoning, which is often
the more specific and more interesting part, stays in [ARCHITECTURE.md](docs/ARCHITECTURE.md).

| This project | Standard term | What it means here |
|---|---|---|
| 10 suites in [`dev/evals/`](dev/evals), scored against [`dev/fixtures/eval_baselines.json`](dev/fixtures/eval_baselines.json) by [`dev/check_evals.sh`](dev/check_evals.sh) | Offline evaluation suite, run as a regression gate | A fixed labelled case set per suite; a suite scoring below its floor fails the gate. Nine suites are gated this way; the tenth, `eval_rawactor.py`, is a deliberately ungated diagnostic (see [ARCHITECTURE.md §6](docs/ARCHITECTURE.md#6-quality-tooling)). |
| `app/coach/nets/*`, `validate()`, and the retry → repair → salvage → fallback chain in [`app/llm/actor.py`](app/llm/actor.py) | Deterministic guardrails and output validation, with graded fallback | Rule-based checks that run on model output, not instead of it. A real model correction always outranks a net; the actor degrades through named stages rather than failing outright. |
| [`app/judge.py`](app/judge.py) | LLM-as-a-judge, with error-shape gating | Two deterministic checks run first; the model is the fallback. The eval gate tracks false negatives and false positives as separate counts, not just accuracy, because the two failures are not equally bad here. |
| 4-bit `Qwen2.5-7B-Instruct` on MLX; prompt cache in [`app/llm/client.py`](app/llm/client.py) | On-device quantised inference, with prompt-cache (KV-cache) reuse | Inference runs on the Mac's own GPU, no network call. Each of the three model roles keeps its own KV cache, so a repeated prompt prefix is not re-processed from scratch on the next turn. |
| SSE in [`app/web.py`](app/web.py) | Token/sentence streaming | The web UI receives the actor's reply sentence-by-sentence over server-sent events, rather than waiting for the whole turn to finish. |
| [`app/retrieval.py`](app/retrieval.py) + `vocab_log.embedding` + `db.due_words_for` | Semantic retrieval / embedding-based ranking | RAG-style retrieval, but over the learner's own vocabulary history rather than documents: the scenario being entered becomes the query, past taught words become the corpus. Deliberately **not** a vector database — the corpus is one learner's rows, a brute-force cosine scan is microseconds, and the module docstring explains why that beats standing up a network service for it. |
| [`dev/evals/fhalf.py`](dev/evals/fhalf.py) | F0.5, the GEC field's precision-weighted metric | Weights precision twice recall, because a learner told their correct sentence is wrong loses more than one told nothing — see the module docstring for how this project's TP/FN/FP counting differs from ERRANT's. |
| [`dev/tools/probe_jfleg.py`](dev/tools/probe_jfleg.py) | Evaluation against an external public benchmark (JFLEG) | Scores the coach against 1,501 sentences it was never tuned on (Napoles et al., EACL 2017), as a check against every other suite being written, and possibly overfit, in-house. Not vendored (CC BY-NC-SA 4.0); downloaded to a scratch directory at run time. |

---

## Installation

Requirements: **Python >= 3.11** (developed on Python 3.11). Python 3.9 reached
end of life in October 2025, and the embedding model used for retrieval needs
3.10 or newer.

1. **Create and activate a Python virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install runtime dependencies:**

   Run the setup script:

   ```bash
   ./setup.sh
   ```

   *(Note: `setup.sh` runs `pip install mlx-lm`. `mlx-lm` version 0.29.1 is the sole runtime dependency, which automatically pulls in `mlx` and `huggingface_hub`.)*

3. **(Optional) Install development and testing dependencies:**

   ```bash
   pip install pytest pyflakes
   ```

4. **(Optional) Install the retrieval extra for semantic vocabulary selection:**

   ```bash
   pip install -e ".[retrieval]"
   ```

   Optional on purpose. Without it, [`app/retrieval.py`](app/retrieval.py) falls
   back to least-recently-seen vocabulary selection, which is what the app did
   before retrieval existed; nothing breaks and no session is lost.

---

## Running the App

Start the conversation coach CLI:

```bash
python3 main.py
```

### First-Run Expectations
On its initial run, the application automatically downloads the model ([`mlx-community/Qwen2.5-7B-Instruct-4bit`](https://huggingface.co/mlx-community/Qwen2.5-7B-Instruct-4bit), approximately 4 GB) into `~/.cache/huggingface/hub/`. Once downloaded, `main.py` sets `HF_HUB_OFFLINE=1` automatically on subsequent runs so the app operates entirely offline without network requests.

---

## Session Data & Storage

All session history and progress log entries are saved locally to a SQLite database at:

```
~/.language-coach/sessions.db
```

---

## Content

The application includes 80 built-in scenarios with 69 tasks per scenario (5,520 total tasks), stored as one JSON file per scenario in [`app/scenarios/data/`](app/scenarios/data/) and loaded by [`app/scenarios/builtins.py`](app/scenarios/builtins.py).

---

## Debugging

To view per-attempt diagnostics and force error handlers to re-raise exceptions instead of displaying user-friendly error messages, set `DEBUG=1`:

```bash
DEBUG=1 python3 main.py
```

---

## Quality Tooling & Testing

The repository contains quality tools and evaluation scripts for content verification and test suites.

### Test Suite & Makefile

- **Run all local CI checks:** `bash dev/check_all.sh` (this is exactly what CI runs)
- **Run unit tests (591 passed on Python 3.11):**
  ```bash
  make test
  # or directly:
  ./venv/bin/pytest
  ```
- **Web UI** (optional front end, same core):
  ```bash
  pip install -e ".[web]"
  make web          # then open http://127.0.0.1:8000
  ```
  The CLI remains the primary front end; the web UI exists because coach
  feedback scrolls away in a terminal, and a panel that stays on screen is what
  makes that feedback reach the learner. It follows the language being studied,
  using the same i18n table as the CLI.

- **Automated AI playtester:**
  ```bash
  make playtest
  ```
  Required before merging any change under `app/scenarios/data/` — it is the
  acceptance gate from `docs/ADRs/ADR-003`, confirming a simulated learner can still
  reach each task goal. It drives the 7B model through multi-turn dialogue, so
  it costs minutes per scenario and is deliberately not part of `make check` or
  CI; it is a checklist item people run, not machinery. Note that
  `dev/playtest/playtest_sample.py` resumes from its `--out` file, so use a fresh
  path when verifying a change or you will replay old numbers without touching
  the model.
- **Run the LLM-graded gate (offline evaluation suite, run as a regression
  gate — compares every suite to its baseline):**
  ```bash
  make check-evals            # every suite
  make check-evals SUITES=coach   # one at a time
  ```
  Needs MLX and a loaded 7B, and takes minutes, which is why it is not part of
  `make check` or CI (OPEN-08). `make eval` is an alias for it. A suite scoring
  below its floor in `dev/fixtures/eval_baselines.json` fails the gate; when a
  change legitimately moves a number, re-measure and edit that file in the same
  commit.

### Structural & Content Quality Scripts

- **Check structural task depth across scenarios:**
  ```bash
  python3 dev/checks/check_task_depth.py 1-80 --expect-total=5520
  ```
  *(All 80 scenarios pass. The check also prints a non-fatal warning listing goals that are duplicated across scenarios — mostly shared greeting/farewell boilerplate.)*

- **Check scenario structural parity against flagship reference standards:**
  ```bash
  python3 dev/checks/check_scenario_parity.py 1-80
  ```

- **Check content coherence:**
  ```bash
  python3 dev/checks/check_content_coherence.py
  ```
  *(Verifies topic relevance, detects duplicate/trivial vocabulary, flags near-duplicate goals, and checks goal/`done_when` alignment.)*

- **LLM Role Evaluation Scripts (slow, requires model inference):**
  ```bash
  make check-evals          # all gated suites, scored against dev/fixtures/eval_baselines.json
  make check-evals SUITES=coach   # or gate one at a time
  ```
  Ten suites live in `dev/evals/`. Nine are gated by default —
  `eval_coach.py`, `eval_judge.py`, `eval_actor.py`, `eval_moods.py`,
  `eval_coachreason.py`, `eval_coachrecall.py`, `eval_explain.py`,
  `eval_jarecall.py`, `eval_jalength.py` — each scored against its floor in
  `dev/fixtures/eval_baselines.json`. The tenth, `eval_rawactor.py`, scores the
  actor's first generation with no retry/salvage/fallback and has no floor on
  purpose (the sample size is too small to gate on without the floor tripping
  on noise); it is a diagnostic, run by name, not part of the default set. All
  ten are deliberately kept out of `check_all.sh` and CI: each needs the 7B
  loaded and together they take minutes.

---

## Project Layout

Opening the folder shows far more than the project. **Six directories are the
project; the rest is tooling output you can ignore.**

### The project

Three directories, split by who uses them.

| | |
|---|---|
| [`app/`](app) | the code that runs — see the table below |
| [`dev/`](dev) | everything used to maintain it: [`tests/`](dev/tests), [`checks/`](dev/checks) (fast, deterministic), [`evals/`](dev/evals) (LLM-graded, slow), [`fixtures/`](dev/fixtures) (labelled rulers and score floors), [`playtest/`](dev/playtest), [`tools/`](dev/tools), [`archive/`](dev/archive) (one-offs that already ran) |
| [`docs/`](docs) | [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) how it works and why, [`BACKLOG.md`](docs/BACKLOG.md) what is known to be wrong and what was already measured, plus [`ADRs/`](docs/ADRs), [`bug_reports/`](docs/bug_reports), [`diagrams/`](docs/diagrams) |

Plus four files at the root: [`main.py`](main.py) (CLI entry point),
[`Makefile`](Makefile) (`make check`, `make web`, `make playtest`),
`pyproject.toml` and `setup.sh`.

### Inside `app/`

| | |
|---|---|
| [`app/llm/`](app/llm) | everything that talks to the model: `client.py` (loading, prompt cache, one call), `guards.py` (script and question checks), `actor.py` (the NPC), `vocab.py`, `translate.py` |
| [`app/coach/`](app/coach) | grammar feedback: `prompt.py`, `filters.py`, `verdict.py`, `pipeline.py`, and `nets/` — one file per class of error the model misses |
| [`app/judge.py`](app/judge.py) | did the learner complete the task? Deterministic first, LLM as fallback |
| [`app/cli.py`](app/cli.py) / [`app/web.py`](app/web.py) | the two front ends over one core |
| [`app/static/index.html`](app/static/index.html) | the entire web UI — markup, style and script in one file |
| [`app/explain.py`](app/explain.py) | explain mode: the learner explains, a listener asks back |
| [`app/session.py`](app/session.py) [`app/db.py`](app/db.py) [`app/i18n.py`](app/i18n.py) | session state, SQLite, and every visible string in both languages |
| [`app/retrieval.py`](app/retrieval.py) | semantic retrieval over the learner's own taught vocabulary — embeds the scenario being entered, ranks due words by cosine similarity to it. Optional: falls back to least-recently-seen without `mlx-embeddings` installed |
| [`app/scenarios/`](app/scenarios) | the 80-scenario catalogue and its loader |

### Safe to ignore, and safe to delete

None of these are in git; every one is regenerated on demand.

| | |
|---|---|
| `venv/` | the Python environment. Large, necessary, never edited by hand |
| `.git/` | git's own storage |
| `.pytest_cache/` `.coverage` `.eval_logs/` `*.egg-info/` | rebuilt by `make check` |
| `docs/diagrams/*.visual-check.*` `*.delta.*` | by-products of the diagram tool |
| `scratch/` | throwaway probe scripts from past sessions |

