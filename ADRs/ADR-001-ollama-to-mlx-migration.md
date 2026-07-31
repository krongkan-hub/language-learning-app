# ADR-001: Migrate model runtime from Ollama to MLX

**Status:** Accepted, implementation in progress (uncommitted)
**Owner:** `architect_agent`

## Context
The app originally served its model (`qwen3:8b`) through a local Ollama
daemon (`ollama pull qwen3:8b`, `setup.sh`). The working tree has since moved
to `mlx-lm`, loading `mlx-community/Qwen2.5-7B-Instruct-4bit` in-process via
`mlx_lm.load()` at import time in `app/llm.py`, removing the dependency on a
separately-running Ollama server on Apple Silicon.

## Decision
Adopt MLX as the local inference runtime; drop the Ollama dependency.

## Consequences
- **Positive:** no separate server process to manage; one less moving part
  for a learner to have running before the CLI works.
- **Negative — already realized:** Ollama and MLX option dicts use different
  key names (`num_predict`/`num_ctx` vs `max_tokens`). The migration missed
  this in `coach.py`/`judge.py` initially, silently changing both roles'
  token budgets and causing a real regression (self-contradicting judge
  verdicts — `bug_reports/judge.md#BUG-010`/`#BUG-011`). Now fixed in the
  working tree; not yet committed or re-verified live.
- **Negative — not yet resolved:** `main.py` forces `HF_HUB_OFFLINE=1` before
  the model is guaranteed to be cached, contradicting `setup.sh`'s promise of
  automatic first-run download (`bug_reports/infra.md#BUG-031`).
- **Cleanup outstanding:** `BASE_MODEL = 'qwen3:8b'` (unused) and a
  qwen3-specific `/no_think` prompt suffix (meaningless to Qwen2.5) remain in
  `coach.py`/`judge.py` (`bug_reports/judge.md#BUG-014`).

## Follow-up
Do not consider this migration "done" until: (1) the option-key fix is
committed and re-verified against a live model run, not just read as correct
code; (2) the first-run/offline-mode contradiction is resolved one way or
the other; (3) the qwen3 leftovers are removed. Track as backlog items — see
`BACKLOG.md`.
