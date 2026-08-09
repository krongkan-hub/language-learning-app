# Language Conversation Coach

A command-line language-conversation coach for practicing English. The learner role-plays realistic scenarios (such as checking in at an airport or negotiating with a landlord) against a locally-run Large Language Model.

On each turn, three internal roles process the interaction: an **Actor** that plays the NPC in character, a **Coach** that provides grammar and phrasing feedback on the learner's English, and a **Judge** that evaluates whether the learner accomplished the task's goal. See [ARCHITECTURE.md](ARCHITECTURE.md#2-pipeline) §2 for details on the execution pipeline.

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

The application includes 80 built-in scenarios with 69 tasks per scenario (5,520 total tasks), defined in [`app/scenarios/builtins.py`](app/scenarios/builtins.py).

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

- **Run unit tests (106 passed):**
  ```bash
  make test
  # or directly:
  ./venv/bin/pytest
  ```
- **Automated AI playtester:**
  ```bash
  make playtest
  ```
- **Run model evaluation scripts:**
  ```bash
  make eval
  ```

### Structural & Content Quality Scripts

- **Check structural task depth across scenarios:**
  ```bash
  python3 scripts/check_task_depth.py 1-80 --expect-total=5520
  ```
  *(Note: Scenarios 1, 3, 4, and 5 fail this check by design as they are older scenarios that have not yet been brought up to current depth standards.)*

- **Check scenario structural parity against flagship reference standards:**
  ```bash
  python3 scripts/check_scenario_parity.py 1-80
  ```

- **Check content coherence:**
  ```bash
  python3 scripts/check_content_coherence.py
  ```
  *(Verifies topic relevance, detects duplicate/trivial vocabulary, flags near-duplicate goals, and checks goal/`done_when` alignment.)*

- **LLM Role Evaluation Scripts (slow, requires model inference):**
  ```bash
  python3 scripts/eval_coach.py
  python3 scripts/eval_judge.py
  python3 scripts/eval_actor.py
  ```

---

## Project Layout

- [`main.py`](main.py) — CLI entrypoint and offline environment configuration.
- [`setup.sh`](setup.sh) — Helper script executing `pip install mlx-lm`.
- [`app/`](app) — Core application source code:
  - [`app/cli.py`](app/cli.py) — Turn loop, interactive prompt, vocabulary box display, and DB calls.
  - [`app/llm.py`](app/llm.py) — MLX model loading, chat interface wrapper, actor prompts, output sanitization and validation.
  - [`app/coach.py`](app/coach.py) — Coach system prompts and output filtering.
  - [`app/judge.py`](app/judge.py) — Task completion evaluation (deterministic regex/stem matching with LLM fallback).
  - [`app/db.py`](app/db.py) — SQLite database schema and session logging (`~/.language-coach/sessions.db`).
  - [`app/scenarios/`](app/scenarios) — Scenario models (`models.py`) and built-in content (`builtins.py`).
- [`scripts/`](scripts) — Quality assurance checks, parity validation, content coherence, and LLM evaluation tools.
- [`tests/`](tests) — Automated test suite.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Technical architecture and pipeline documentation.
