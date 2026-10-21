# Deployment

The app runs on the Mac it is installed on, in a terminal, and nowhere else.
There is no container image for it and no server: the web front end and the
Dockerfile that packaged it were removed on 2026-10-21 (ADR-006).

## Running it

```
./setup.sh          # pip install -e .
make run            # python3 main.py
```

PostgreSQL 17 with pgvector is the one service it needs — Homebrew (README),
or the `db` service in `docker-compose.yml` (`docker compose up -d`, then
point `$LANGUAGE_COACH_DSN` at `127.0.0.1:5433`). The database is the only
part that can live in a container.

## Why the app cannot run in a container

This app runs local inference through Apple's MLX, which needs Metal. Three
independent things stand in the way on Linux, the first two before a model is
ever loaded:

**1. `mlx-lm`'s own dependency declares `mlx` as Darwin-only.**
`mlx-lm==0.29.1` (the version pinned in `pyproject.toml`) lists its
dependency on Apple's `mlx` package as `mlx>=0.29.2; platform_system ==
"Darwin"`. On Linux, pip skips it cleanly, so `pip install .` succeeds and
`mlx` is simply absent afterwards.

**2. `mlx_lm` imports `mlx` unconditionally, and so does this app.**
`mlx_lm/utils.py` opens with `import mlx.core as mx` — no guard, no lazy
import — and `app/llm/client.py` does `from mlx_lm import load, generate,
stream_generate` at module top level. `app.cli` imports that chain, so
`python3 main.py` on Linux raises `ModuleNotFoundError: No module named 'mlx'`
before the first prompt.

**3. Even if that were patched, macOS Docker has no Metal to give it.**
Docker Desktop runs Linux containers in a VM with no GPU passthrough to the
host's Metal device. `mlx[cpu]` and `mlx[cuda]` wheels exist, but CPU
inference of a 7B model abandons the reason this project chose MLX, and CUDA
needs an NVIDIA GPU no Mac has.

## Packaging

`[tool.setuptools.package-data]` in `pyproject.toml` declares the non-Python
files (the 80 scenario JSONs, `explain_topics.json`, the lexicon); without it
a wheel shipped only `.py` files. `test_the_wheel_contains_the_content_the_app_needs`
in `dev/tests/test_packaging.py` builds the wheel and counts them.

## The adapter interface

`app/llm/client.py` was read in full to write this and was **not**
modified — this section describes what an adapter would have to provide to
run the coach against a remote model server, not a plan to write one here.
Nothing here is wanted while the project is MLX-only; it is kept because it is
the map of every model call site.

There are two independent seams, because the app has two different call
shapes today, and a remote-endpoint adapter has to cover both.

### 1. `_llm_chat` — the synchronous call (judge, coach, explain, translate)

```python
def _llm_chat(messages: list, options: dict, cache_key: Optional[str] = None) -> dict:
    ...
    return {'message': {'content': response_text}}
```

- `messages`: OpenAI-style `[{'role': ..., 'content': ...}]`.
- `options`: read as `options.get('temperature', 0.6)` and
  `options.get('max_tokens', 200)`.
- Return shape: exactly `{'message': {'content': <str>}}` — every caller
  does `response['message']['content']`.
- Call sites, so the adapter has every options dict it needs to honor:
  `app/judge.py` (`JUDGE_OPTS`: temp 0.0, max_tokens 64),
  `app/coach/pipeline.py` (`COACH_OPTS`: temp 0.2, max_tokens 250),
  `app/explain.py` (`LISTENER_OPTS`: temp 0.3, max_tokens 120),
  `app/llm/translate.py` (`TRANSLATE_OPTS`: temp 0.0, max_tokens 1024),
  `app/llm/actor.py`'s `call_actor` (`ACTOR_OPTS`: temp 0.6, max_tokens 200).
- The adapter's job is to replace this one function's body with an HTTP call
  (e.g. POST to an OpenAI-compatible `/v1/chat/completions`), map `options`
  onto that endpoint's request shape, and reshape its response back into the
  `{'message': {'content': ...}}` dict above. Nothing else in the app needs
  to change for these five call sites.

### 2. The actor's streaming path — `stream_actor` (used only by `app/cli/turns.py`)

This does **not** go through `_llm_chat`. To validate and emit
sentence-by-sentence as tokens arrive, it reaches directly into
`client._ensure_model()`, `client._llm_lock`,
`client._prepare_prompt_cache_for_call()`, `client.stream_generate()`, and
`client._save_prompt_cache_on_success()`.

It already has a seam built for exactly this, unused today:

```python
def stream_actor(messages, system_prompt, speaker=None, max_sentences=3,
                  callback=None, generator_fn=None, cache_key='actor',
                  language=''): ...
```

When `generator_fn` is given, `stream_actor` calls `generator_fn()` and
iterates the result, skipping the whole MLX branch. Each yielded item must
expose a `.text` attribute (matching `mlx_lm.stream_generate`'s own
`GenerationResponse`) or be usable via `str(item)`. An HTTP adapter that
streams SSE/chunked tokens from a remote endpoint can be wired in as
`generator_fn=lambda: remote_stream(messages, system_prompt, options)` with
**no change to `client.py`**.

The catch: nothing calls `stream_actor` with `generator_fn` today.
`app/cli/turns.py`'s one call site
(`produce_actor_turn(..., actor_fn=stream_actor, ...)`) doesn't forward it —
a one-line change.

### 3. Prompt-cache (`cache_key`) — the part with no honest remote equivalent

`cache_key` (`'actor'`, `'coach'`, the judge's key, `'judge_confirm'`)
selects one of up to `PROMPT_CACHE_MAX_ENTRIES = 4` in-process MLX KV
caches, reused by trimming to the longest common prefix once it passes
`PROMPT_CACHE_PREFIX_THRESHOLD = 256` tokens, capped at
`PROMPT_CACHE_MAX_KV_SIZE = 4096` tokens per slot, LRU-evicted. This is
`mlx_lm.models.cache` state tied to one process's memory; there is no way to
hand it across an HTTP call. An adapter has two honest choices, and both
need to be *measured*, not assumed:

- Drop it — resend the full prompt every call. Correct, but the
  9–11s-per-turn budget this project engineered around (see
  `app/session.py`'s `ACTOR_HISTORY_MESSAGES` comment, which explains why
  history is capped specifically to keep the KV cache trimmable) was
  measured with the cache in place. Expect it to get worse.
- Lean on the remote server's own prefix caching, if the endpoint has one
  (vLLM/SGLang "automatic prefix caching" and similar), and drop `cache_key`
  client-side. Whether that actually reuses anything depends entirely on the
  real server and can't be verified from this repo.

### 4. Model identity and the eval floor

`BASE_MODEL = 'mlx-community/Qwen2.5-7B-Instruct-4bit'` is one specific MLX
4-bit quantization. Whatever a remote endpoint serves instead (GGUF via
llama.cpp, AWQ/GPTQ via vLLM, ...) is a *different*
quantization of the same base model, not bit-identical output.
`dev/fixtures/eval_baselines.json` was measured against the MLX build specifically.
Pointing this app at a different backend without re-running
`make check-evals` against that new endpoint, and deliberately updating the
baseline file, leaves the floor numbers describing a model that is no
longer the one actually running — exactly the drift this project's own gate
rules say not to allow.

### 5. Error shape

`MLX_ERRORS = (RuntimeError, ValueError, OSError, FileNotFoundError)` and
`describe_llm_error()` (`f"MLX Engine Error: {str(e)}"`) are what
`app/cli/` catches to show a learner a clean message
instead of a traceback. An HTTP adapter should raise one of those same
types (wrap a connection/timeout error as `RuntimeError`, for instance) so
the existing catch sites keep working unmodified.

## What the smallest honest path would cost

Not a number — the shape of the work:

- Replacing `_llm_chat`'s body with an HTTP call is genuinely small: one
  function, on the order of tens of lines, covering §1 above.
- `stream_actor`'s direct-MLX branch needs either its own adapter or the
  one-line `app/cli/turns.py` change in §2 to start forwarding `generator_fn`.
- Deciding what happens to prompt-cache reuse (§3) and re-measuring the
  turn-latency budget once a local KV cache is no longer doing the work is
  a real investigation, not a config flag.
- Standing up the model server is infrastructure outside this repository —
  and worth pausing on: a Mac already runs MLX in-process for free, so this
  only earns its cost if the goal is running the coach on a host that isn't
  Apple Silicon.
- Whatever backend gets stood up, `make check-evals` has to be re-run
  against it and `dev/fixtures/eval_baselines.json` updated deliberately (§4)
  before the new setup can be trusted the way the MLX one currently is.
