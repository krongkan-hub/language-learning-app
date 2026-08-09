#!/usr/bin/env python3
"""
Correctness verification script for MLX KV prompt caching in app/llm.py.
Compares model output with and without prompt caching at temperature 0.0
to prove that prompt caching produces 100% byte-identical output.
"""
import sys
import os

# Add parent directory to path so app modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
from app.llm import (
    _ensure_model,
    _llm_chat,
    reset_prompt_caches,
    ACTOR_SYS,
    build_task_setup_block
)
from app.scenarios.builtins import SCENARIOS

def verify_cache_correctness():
    print("Loading model and preparing correctness test...")
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

    turn1_messages = [
        {'role': 'system', 'content': actor_system},
        {'role': 'user', 'content': 'Hello! I would like to check in for my room.'}
    ]

    opts = {'temperature': 0.0, 'max_tokens': 50}

    print("\n--- TURN 1 (Without Cache / Fresh Cache) ---")
    reset_prompt_caches()
    res1_nocache = _llm_chat(turn1_messages, opts, cache_key=None)['message']['content']
    print("Turn 1 output (no cache):\n", repr(res1_nocache))

    turn2_messages = turn1_messages + [
        {'role': 'assistant', 'content': res1_nocache},
        {'role': 'user', 'content': 'My name is Alexander Smith, I have a reservation.'}
    ]

    print("\n--- TURN 2 WITHOUT CACHE ---")
    reset_prompt_caches()
    res2_nocache = _llm_chat(turn2_messages, opts, cache_key=None)['message']['content']
    print("Turn 2 output (no cache):\n", repr(res2_nocache))

    print("\n--- TURN 1 & TURN 2 WITH CACHE ---")
    reset_prompt_caches()
    res1_cached = _llm_chat(turn1_messages, opts, cache_key='actor')['message']['content']
    res2_cached = _llm_chat(turn2_messages, opts, cache_key='actor')['message']['content']
    print("Turn 1 output (cached):\n", repr(res1_cached))
    print("Turn 2 output (cached):\n", repr(res2_cached))

    print("\n--- VERIFYING BYTE-IDENTICAL OUTPUT ---")
    assert res1_nocache == res1_cached, f"Turn 1 mismatch:\nNo cache: {res1_nocache!r}\nCached: {res1_cached!r}"
    assert res2_nocache == res2_cached, f"Turn 2 mismatch:\nNo cache: {res2_nocache!r}\nCached: {res2_cached!r}"

    print("\nVERIFICATION SUCCESSFUL: Output with and without prompt cache is 100% byte-identical!")

if __name__ == '__main__':
    verify_cache_correctness()
