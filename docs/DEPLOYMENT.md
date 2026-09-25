# Deployment

Read this before assuming the `Dockerfile` in the repo root gives you a
running app. It does not, today. This page says exactly what it gives you
instead, why, and what the smallest honest fix would look like.

## Build and run

```
docker build -t language-coach-web .
docker run --rm -p 8000:8000 -v language-coach-data:/data language-coach-web
```

Docker was not installed on the machine this was written on, so neither
command has actually been run here. Everything below was verified a
different way — reading `app/llm/client.py`, fetching `mlx-lm`'s published
package metadata from PyPI, inspecting the contents of its wheel, and
building this project's own wheel locally with `python -m build` — all
without Docker and without loading the MLX model. Run `docker build` for
real before trusting this page over your own eyes; report back if what you
see differs.

## Why the container cannot run inference

This app runs local inference through Apple's MLX, which needs Metal. Two
independent things break that in this container, not one:

**1. `mlx-lm`'s own dependency declares `mlx` as Darwin-only.**
`mlx-lm==0.29.1` (the version pinned in `pyproject.toml`) lists its
dependency on Apple's `mlx` package as `mlx>=0.29.2; platform_system ==
"Darwin"`. On this Linux image, pip does not even attempt to install `mlx`
— the marker makes it skip cleanly. So `pip install .[web]` succeeds, but
`mlx` itself is not present in the image afterwards.

**2. `mlx_lm` imports `mlx` unconditionally, and so does this app.**
`mlx_lm/__init__.py` does `from .utils import load`, and `mlx_lm/utils.py`
opens with `import mlx.core as mx` / `import mlx.nn as nn` — no guard, no
lazy import. `app/llm/client.py` line 11 does
`from mlx_lm import load, generate, stream_generate`, also at module top
level, and `app/llm/__init__.py` and `app/web.py` both import that chain
before anything else runs. The result: `from app.web import serve` — the
exact line this Dockerfile's `CMD` runs — raises
`ModuleNotFoundError: No module named 'mlx'` before uvicorn ever binds a
socket. This is not a per-request degrade caught by `MLX_ERRORS`; it is a
process that never starts. Under any orchestrator health check this
container restart-loops.

**3. Even if that were patched, macOS Docker has no Metal to give it.**
Docker Desktop on macOS runs its Linux containers inside a lightweight VM
with no GPU passthrough to the host's Metal device. Newer `mlx` releases do
publish Linux CPU and CUDA wheels (`mlx[cpu]`, `mlx[cuda]`), so it is
*possible* to get some `mlx` build to import on Linux — but CPU inference of
a 7B model abandons the entire reason this project chose MLX, and CUDA needs
an NVIDIA GPU no Mac has. `mlx-lm==0.29.1`'s own dependency spec does not
reach for either: it only asks for `mlx` on Darwin at all. Nothing here
tries the CPU/CUDA path, on purpose.

## A second, independent packaging gap (found while checking this — now fixed)

`pyproject.toml` declared no `package-data` and there was no `MANIFEST.in`, so
a wheel built from `pip install .` contained only `.py` files: 40 of them, and
none of the 80 `app/scenarios/data/*.json` scenarios, `app/explain_topics.json`
or `app/static/index.html`. A server started against the *installed* package
would have come up with zero scenarios and a 404 on its own UI, MLX aside
entirely. Nothing caught it because this repo always runs from a source
checkout, where those files are simply present.

`[tool.setuptools.package-data]` now declares them, and the rebuilt wheel
carries 122 files including all 80 scenarios. `test_the_wheel_contains_the_
content_the_app_needs` in `dev/tests/test_docker_packaging.py` builds the
wheel and counts them, so the next person to change the packaging finds out
from a test rather than from a deployment.

This `Dockerfile` still runs from `/app` rather than from the installed
package — that is now a choice about reload-ability rather than a workaround,
and either would work.

## What works in the container, and what doesn't

**Works:** the image builds. `fastapi`, `uvicorn`, and `mlx-lm`'s own
(pure-Python) wheel all install cleanly on Linux, because nothing in that
list needs `mlx` to *install* — only to be *imported*, which happens one
step later, at container startup, not at build time.

**Doesn't work:** anything that requires the server to actually start.
Every deterministic, non-model part of this app — serving
`app/static/index.html`, storing sessions and vocab in the SQLite file at
`LANGUAGE_COACH_DB` (mapped to the `/data` volume above), loading the 80
scenarios — would run fine on Linux if `app.web` could be imported. It
can't be, today (see above), so none of it is reachable. "Works in the
container" is currently "builds"; nothing serves a request.

## The adapter interface

`app/llm/client.py` was read in full to write this and was **not**
modified — this section describes what an adapter would have to provide to
make this Dockerfile useful, not a plan to write one here.

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
  `options.get('max_tokens', options.get('num_predict', 200))`. Note the
  `num_predict` fallback — `app/explain.py`'s `LISTENER_OPTS` still uses
  that (Ollama-era) key instead of `max_tokens`. An adapter that only
  handles `max_tokens` silently truncates that one call site to the 200
  default.
- Return shape: exactly `{'message': {'content': <str>}}` — every caller
  does `response['message']['content']`.
- Call sites, so the adapter has every options dict it needs to honor:
  `app/judge.py` (`JUDGE_OPTS`: temp 0.0, max_tokens 64),
  `app/coach/pipeline.py` (`COACH_OPTS`: temp 0.2, max_tokens 250),
  `app/explain.py` (`LISTENER_OPTS`: temp 0.3, num_predict 120),
  `app/llm/translate.py` (`TRANSLATE_OPTS`: temp 0.0, max_tokens 1024),
  `app/llm/actor.py`'s `call_actor` (`ACTOR_OPTS`: temp 0.6, max_tokens 200).
- The adapter's job is to replace this one function's body with an HTTP call
  (e.g. POST to an OpenAI-compatible `/v1/chat/completions`), map `options`
  onto that endpoint's request shape, and reshape its response back into the
  `{'message': {'content': ...}}` dict above. Nothing else in the app needs
  to change for these five call sites.

### 2. The actor's streaming path — `stream_actor` (used only by `app/web.py`)

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
`app/web.py`'s one call site
(`produce_actor_turn(..., actor_fn=stream_actor, ...)`) doesn't forward it —
that's a one-line change in a file this task was not allowed to touch,
flagged here for whoever owns `app/web.py`.

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
llama.cpp, AWQ/GPTQ via vLLM, Ollama's own build, ...) is a *different*
quantization of the same base model, not bit-identical output.
`eval/eval_baselines.json` was measured against the MLX build specifically.
Pointing this app at a different backend without re-running
`make check-evals` against that new endpoint, and deliberately updating the
baseline file, leaves the floor numbers describing a model that is no
longer the one actually running — exactly the drift this project's own gate
rules say not to allow.

### 5. Error shape

`MLX_ERRORS = (RuntimeError, ValueError, OSError, FileNotFoundError)` and
`describe_llm_error()` (`f"MLX Engine Error: {str(e)}"`) are what
`app/web.py` and `app/cli.py` catch to show a learner a clean message
instead of a traceback. An HTTP adapter should raise one of those same
types (wrap a connection/timeout error as `RuntimeError`, for instance) so
the existing catch sites keep working unmodified.

## What the smallest honest path would cost

Not a number — the shape of the work:

- Replacing `_llm_chat`'s body with an HTTP call is genuinely small: one
  function, on the order of tens of lines, covering §1 above.
- `stream_actor`'s direct-MLX branch needs either its own adapter or the
  one-line `app/web.py` change in §2 to start forwarding `generator_fn` —
  small, but outside files this task could touch.
- Deciding what happens to prompt-cache reuse (§3) and re-measuring the
  turn-latency budget once a local KV cache is no longer doing the work is
  a real investigation, not a config flag.
- Standing up the actual model server this container would talk to is
  infrastructure entirely outside this repository — and worth pausing on:
  a Mac already runs MLX in-process for free, so this only earns its cost
  if the goal is running the coach on a host that isn't Apple Silicon.
- Whatever backend gets stood up, `make check-evals` has to be re-run
  against it and `eval/eval_baselines.json` updated deliberately (§4)
  before the new setup can be trusted the way the MLX one currently is.
