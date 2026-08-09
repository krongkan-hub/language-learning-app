#!/usr/bin/env python3
import argparse
import os
import random
import sys
import time

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm import NPC_MOODS, call_actor, validate
from app.scenarios.builtins import SCENARIOS
from app.session import build_actor_system_prompt, ACTOR_MAX_SENTENCES


def evaluate_mood(mood: str, scenario, turns: int, seed: int):
    random.seed(seed)
    task = scenario.tasks[0]
    complication = scenario.complications[0] if scenario.complications else None
    system_prompt = build_actor_system_prompt(
        scenario, task, language='English', mood=mood, complication=complication
    )
    messages = [{'role': 'user', 'content': 'Hello!'}]

    passed_count = 0
    failure_reasons = {}
    latencies = []

    for _ in range(turns):
        t0 = time.time()
        reply = call_actor(
            messages,
            system_prompt,
            speaker=scenario.speaker,
            max_sentences=ACTOR_MAX_SENTENCES,
            cache_key=None,
        )
        elapsed = time.time() - t0
        latencies.append(elapsed)

        ok, reason = validate(reply, max_sentences=ACTOR_MAX_SENTENCES)
        if ok:
            passed_count += 1
        else:
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

    mean_lat = sum(latencies) / len(latencies) if latencies else 0.0
    return {
        'mood': mood,
        'turns': turns,
        'passed': passed_count,
        'failed': turns - passed_count,
        'failure_reasons': failure_reasons,
        'mean_latency': mean_lat,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate actor output validation pass rate and latency across NPC_MOODS."
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=3,
        help="Number of actor turns to generate per mood (default: 3)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--scenario-idx",
        type=int,
        default=0,
        help="Scenario index to use for evaluation (default: 0)",
    )

    args = parser.parse_args()

    scenario = SCENARIOS[args.scenario_idx]
    print(
        f"Evaluating {len(NPC_MOODS)} moods ({args.turns} turns/mood) on scenario '{scenario.name}' [seed={args.seed}]..."
    )
    print("=" * 100)

    results = []
    for idx, mood in enumerate(NPC_MOODS, 1):
        mood_seed = args.seed + idx
        print(f"[{idx}/{len(NPC_MOODS)}] Evaluating mood: '{mood}'...")
        res = evaluate_mood(mood, scenario, args.turns, mood_seed)
        results.append(res)

    print("\n" + "=" * 100)
    print("MOOD EVALUATION SUMMARY TABLE")
    print("=" * 100)
    header = f"{'Mood':<55} | {'Pass':<6} | {'Fail':<6} | {'Pass %':<8} | {'Mean Lat (s)':<12} | {'Failure Reasons'}"
    print(header)
    print("-" * 100)

    for r in results:
        pass_pct = (r['passed'] / r['turns']) * 100 if r['turns'] > 0 else 0.0
        reasons_str = (
            ", ".join(f"{k}: {v}" for k, v in r['failure_reasons'].items())
            if r['failure_reasons']
            else "None"
        )
        pass_ratio = f"{r['passed']}/{r['turns']}"
        print(
            f"{r['mood']:<55} | {pass_ratio:<6} | {r['failed']:<6} | {pass_pct:>6.1f}%  | {r['mean_latency']:>10.2f}s  | {reasons_str}"
        )

    print("=" * 100)


if __name__ == "__main__":
    main()
