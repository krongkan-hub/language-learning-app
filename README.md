# Language Conversation Coach

A command-line language-conversation coach for practicing English. The learner role-plays realistic scenarios (such as checking in at an airport or negotiating with a landlord) against a locally-run Large Language Model.

On each turn, three internal roles process the interaction: an **Actor** that plays the NPC in character, a **Coach** that provides grammar and phrasing feedback on the learner's English, and a **Judge** that evaluates whether the learner accomplished the task's goal. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#2-pipeline) §2 for details on the execution pipeline.

> [!IMPORTANT]
> **Hardware Requirement: Apple Silicon Mac (M-Series)**  
> This application uses [MLX](https://github.com/ml-explore/mlx) for local model inference, which is Apple-Silicon-only. It was developed and tested on an Apple Silicon Mac with 16 GB RAM. On a 16 GB machine, ensure only one inference process runs at a time.

---

## Installation

Requirements: **Python >= 3.9** (developed on Python 3.9.6).

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
- **Run unit tests (370 passed):**
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
- **Run the LLM-graded gate (compares every suite to its baseline):**
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
  make check-evals          # all four suites, scored against dev/fixtures/eval_baselines.json
  make check-evals SUITES=coach   # or gate one at a time
  ```
  The four suites are `dev/evals/eval_coach.py`, `eval_judge.py`, `eval_actor.py`
  and `eval_moods.py`. They are deliberately kept out of `check_all.sh` and CI:
  each needs the 7B loaded and the four together take minutes.

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

