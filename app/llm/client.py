"""Talking to the local model: loading it, the prompt cache, one call.

The prompt cache is sized to the number of distinct cache keys in the app;
a test asserts that relationship rather than trusting the constant.
"""
import os
import re
import threading
import time
from typing import Optional
from mlx_lm import load, generate, stream_generate
from mlx_lm.models.cache import (make_prompt_cache, trim_prompt_cache,
                                 can_trim_prompt_cache, cache_length)


TRANSLATE_OPTS = {'temperature': 0.0, 'max_tokens': 1024}
BASE_MODEL = 'mlx-community/Qwen2.5-7B-Instruct-4bit'

# 'shall' was missing until the parity check in scripts/check_rule_vacuity.py
# flagged it on its first run: "Shall I help you?" passed while its Japanese
# twin 「お手伝いしましょうか？」 was correctly caught. For once the vacuous side
# was the English list, not the Japanese branch — which is the argument for
# parity over a one-directional "does it work on Japanese" test.
CLOSED_OPENERS = {'do', 'does', 'did', 'is', 'are', 'was', 'were', 'can', 'could', 'will', 'would', 'should', 'shall', 'have', 'has', 'want', 'need', 'may', 'am'}
WH_WORDS = {'what', 'why', 'how', 'which', 'where', 'when', 'who'}
EMOJI_PATTERN = r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u27BF]'
DEBUG = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')

_llm_lock = threading.Lock()
_model = None
_tokenizer = None

_prompt_caches = {}
# One slot per cache key in use: actor, coach, judge, judge_confirm. At 3 the
# four keys thrashed — judge_confirm joins the rotation on any failed attempt,
# and MAX_TASK_ATTEMPTS is 4, so a cyclic access pattern of 4 against 3 slots
# evicted every entry before it could be reused. Measured through the real
# _prepare_prompt_cache_for_call: reuse {actor: 9, coach: 9} without
# judge_confirm, {} with it, and {actor: 9, coach: 9} again at capacity 4
# (OPEN-28). Raising this costs one more KV cache in memory and nothing else.
PROMPT_CACHE_MAX_ENTRIES = 4
PROMPT_CACHE_MAX_KV_SIZE = 4096
PROMPT_CACHE_PREFIX_THRESHOLD = 256

def reset_prompt_caches():
    """Clear all prompt KV caches."""
    with _llm_lock:
        _prompt_caches.clear()

def _longest_common_prefix(seq1: list, seq2: list) -> int:
    """Compute the length of the longest common prefix between two lists."""
    min_len = min(len(seq1), len(seq2))
    idx = 0
    while idx < min_len and seq1[idx] == seq2[idx]:
        idx += 1
    return idx

def _prepare_prompt_cache_for_call(model, tokenizer, prompt_text: str, cache_key: str):
    """Retrieve or initialize prompt cache for cache_key, trimming if prefix matches threshold.

    Must be called while holding `_llm_lock`.
    Returns (prompt_cache, prompt_arg, full_tokens).
    """
    full_tokens = tokenizer.encode(prompt_text)
    now = time.time()

    if cache_key in _prompt_caches:
        entry = _prompt_caches[cache_key]
        cached_cache = entry['cache']
        cached_tokens = entry['tokens']
        prefix_len = _longest_common_prefix(full_tokens, cached_tokens)

        if prefix_len == len(full_tokens):
            if len(full_tokens) > 1:
                prefix_len = len(full_tokens) - 1
            else:
                prefix_len = 0

        try:
            curr_len = cache_length(cached_cache)
        except Exception:
            curr_len = -1

        try:
            can_trim = can_trim_prompt_cache(cached_cache)
        except Exception:
            can_trim = False

        if (
            prefix_len >= PROMPT_CACHE_PREFIX_THRESHOLD
            and can_trim
            and curr_len >= prefix_len
        ):
            tokens_to_trim = curr_len - prefix_len
            try:
                trim_prompt_cache(cached_cache, tokens_to_trim)
                entry['last_used'] = now
                return cached_cache, full_tokens[prefix_len:], full_tokens
            except Exception:
                _prompt_caches.pop(cache_key, None)
        else:
            _prompt_caches.pop(cache_key, None)

    while len(_prompt_caches) >= PROMPT_CACHE_MAX_ENTRIES:
        lru_key = min(_prompt_caches.keys(), key=lambda k: _prompt_caches[k]['last_used'])
        del _prompt_caches[lru_key]

    new_cache = make_prompt_cache(model, max_kv_size=PROMPT_CACHE_MAX_KV_SIZE)
    return new_cache, full_tokens, full_tokens

def _save_prompt_cache_on_success(cache_key: str, cache_obj, full_tokens: list):
    """Store updated cache object and full tokens for cache_key on successful generation.

    Must be called while holding `_llm_lock`.
    """
    _prompt_caches[cache_key] = {
        'cache': cache_obj,
        'tokens': full_tokens,
        'last_used': time.time()
    }

def _ensure_model():
    """Load the MLX model on first use. Raises with the original cause on failure."""
    global _model, _tokenizer
    if _model is not None and _tokenizer is not None:
        return _model, _tokenizer
    with _llm_lock:
        if _model is not None and _tokenizer is not None:
            return _model, _tokenizer
        try:
            m, t = load(BASE_MODEL)
            _model, _tokenizer = m, t
            return _model, _tokenizer
        except Exception as e:
            _model, _tokenizer = None, None
            raise RuntimeError(
                f"Failed to load MLX model '{BASE_MODEL}'. "
                f"Please run setup.sh or check the model cache under ~/.cache/huggingface/hub/."
            ) from e

# Deliberately broad because MLX_ERRORS is used at top-level user-facing CLI boundaries
# to present clean error messages rather than tracebacks to learners.
MLX_ERRORS = (RuntimeError, ValueError, OSError, FileNotFoundError)

def describe_llm_error(e: Exception) -> str:
    """Turn an MLX exception into a learner-facing hint."""
    return f"MLX Engine Error: {str(e)}"


def _llm_chat(messages: list, options: dict, cache_key: Optional[str] = None) -> dict:
    from mlx_lm.sample_utils import make_sampler
    
    model, tokenizer = _ensure_model()
    
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    temperature = options.get('temperature', 0.6)
    max_tokens = options.get('max_tokens', options.get('num_predict', 200))
    
    sampler = make_sampler(temp=temperature)
    with _llm_lock:
        if cache_key is not None:
            prompt_cache, prompt_arg, full_tokens = _prepare_prompt_cache_for_call(
                model, tokenizer, prompt, cache_key
            )
            try:
                response_text = generate(
                    model, tokenizer, prompt=prompt_arg, max_tokens=max_tokens,
                    sampler=sampler, prompt_cache=prompt_cache
                )
                _save_prompt_cache_on_success(cache_key, prompt_cache, full_tokens)
            except Exception:
                _prompt_caches.pop(cache_key, None)
                raise
        else:
            response_text = generate(
                model, tokenizer, prompt=prompt, max_tokens=max_tokens, sampler=sampler
            )
    return {'message': {'content': response_text}}

# The other half of the Chinese leak: the model dropping back into English
# mid-line, which a simplified-Chinese denylist can never see. カatering and
# コンフィeti are words in no language — a katakana transliteration abandoned
# partway. Measurements: BACKLOG OPEN-26.
#
# DELIBERATELY NARROW. A Latin run glued directly to kana or kanji is always a
# defect; a Latin word standing alone is not, because real Japanese carries
# them (AV機器, Wi-Fiのパスワード, eSIM). Adjacency is what keeps proper nouns
# and initialisms working.


def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> reasoning traces (qwen3) and any stray tags."""
    text = re.sub('<think>.*?</think>', '', text, flags=re.DOTALL)
    return re.sub('<[^>]+>', '', text)


# Reached as client.<name> from actor.py and translate.py so that a patch
# on app.llm.client lands on the call site. Declared so the linter can see
# that "unused here" does not mean unused.
__all__ = ['BASE_MODEL', 'DEBUG', 'MLX_ERRORS', 'TRANSLATE_OPTS',
           'CLOSED_OPENERS', 'WH_WORDS', 'EMOJI_PATTERN',
           'PROMPT_CACHE_MAX_ENTRIES', 'PROMPT_CACHE_MAX_KV_SIZE',
           'PROMPT_CACHE_PREFIX_THRESHOLD', '_llm_chat', '_ensure_model',
           '_longest_common_prefix', '_prepare_prompt_cache_for_call',
           '_save_prompt_cache_on_success', '_prompt_caches', '_llm_lock',
           'describe_llm_error', 'reset_prompt_caches', 'strip_think_tags',
           'load', 'generate', 'stream_generate', 'make_prompt_cache',
           'trim_prompt_cache', 'can_trim_prompt_cache', 'cache_length']
