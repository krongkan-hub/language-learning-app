#!/usr/bin/env python3
"""
Smoke run measuring Time-To-First-Token (TTFT) for two consecutive actor turns.
"""
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mlx_lm import load, stream_generate
from mlx_lm.sample_utils import make_sampler
from app.llm import (
    _ensure_model,
    reset_prompt_caches,
    ACTOR_SYS,
    ACTOR_OPTS,
    build_task_setup_block,
    _prepare_prompt_cache_for_call,
    _save_prompt_cache_on_success,
    _llm_lock
)
from app.scenarios.builtins import SCENARIOS

def run_smoke_test():
    model, tokenizer = _ensure_model()
    reset_prompt_caches()

    scenario = SCENARIOS[0]
    task = scenario.tasks[0]
    actor_system = ACTOR_SYS.format(
        place=scenario.place,
        role=scenario.role,
        language='English',
        mood='cheerful',
        complication='',
        task_setup=build_task_setup_block(task)
    )

    # Turn 1
    msgs1 = [{'role': 'system', 'content': actor_system}, {'role': 'user', 'content': 'Hello, I need to check in.'}]
    prompt1 = tokenizer.apply_chat_template(msgs1, tokenize=False, add_generation_prompt=True)
    sampler = make_sampler(temp=0.6)

    with _llm_lock:
        cache1, arg1, tok1 = _prepare_prompt_cache_for_call(model, tokenizer, prompt1, 'actor')
        t0 = time.perf_counter()
        gen1 = stream_generate(model, tokenizer, prompt=arg1, max_tokens=100, sampler=sampler, prompt_cache=cache1)
        first_token1_time = None
        full_text1 = ""
        for item in gen1:
            if first_token1_time is None:
                first_token1_time = time.perf_counter()
            full_text1 += item.text
        _save_prompt_cache_on_success('actor', cache1, tok1)

    ttft1 = first_token1_time - t0

    # Turn 2
    msgs2 = msgs1 + [{'role': 'assistant', 'content': full_text1}, {'role': 'user', 'content': 'My name is Smith.'}]
    prompt2 = tokenizer.apply_chat_template(msgs2, tokenize=False, add_generation_prompt=True)
    sampler = make_sampler(temp=0.6)

    with _llm_lock:
        cache2, arg2, tok2 = _prepare_prompt_cache_for_call(model, tokenizer, prompt2, 'actor')
        t0 = time.perf_counter()
        gen2 = stream_generate(model, tokenizer, prompt=arg2, max_tokens=100, sampler=sampler, prompt_cache=cache2)
        first_token2_time = None
        full_text2 = ""
        for item in gen2:
            if first_token2_time is None:
                first_token2_time = time.perf_counter()
            full_text2 += item.text
        _save_prompt_cache_on_success('actor', cache2, tok2)

    ttft2 = first_token2_time - t0

    print(f"\n--- SMOKE RUN TIMINGS ---")
    print(f"Turn 1 Time-To-First-Token (TTFT): {ttft1:.3f}s")
    print(f"Turn 2 Time-To-First-Token (TTFT): {ttft2:.3f}s")
    print(f"Speedup: {ttft1 / ttft2:.1f}x faster TTFT on Turn 2!")

if __name__ == '__main__':
    run_smoke_test()
