import json
import os
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm import call_actor, GREETING_SYS, validate
from app.cli import extract_and_format_vocab

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'eval', 'actor_cases.json')

def evaluate_case(case):
    system = GREETING_SYS.format(
        place=case['place'],
        role=case['role'],
        language=case['language'],
        mood=case.get('mood', "chatty and friendly"),
        complication="",
        task_setup=""
    )
    seed = [{'role': 'user', 'content': 'Hello!'}]
    raw_actor = call_actor(seed, system, speaker=case['speaker'], max_sentences=4, language=case['language'])
    ok, reason = validate(raw_actor, max_sentences=4, language=case['language'])
    clean_text, vocab_box = extract_and_format_vocab(raw_actor)
    has_vocab = len(vocab_box.strip()) > 0
    return (ok and has_vocab), raw_actor, reason, has_vocab, ok

def main():
    if not os.path.exists(FIXTURE_PATH):
        print(f"Fixture not found: {FIXTURE_PATH}")
        sys.exit(1)

    with open(FIXTURE_PATH, 'r') as f:
        cases = json.load(f)

    print(f"Running Actor Eval on {len(cases)} cases across 5 iterations...")
    total_runs = len(cases) * 5
    passed_runs = 0

    print("=" * 80)
    for i, case in enumerate(cases):
        print(f"Case {i+1}: {case['name']} — {case['speaker']} at {case['place']} [{case['language']}]")
        case_passes = 0
        for it in range(5):
            passed, raw, reason, has_vocab, ok = evaluate_case(case)
            if passed:
                case_passes += 1
            else:
                print(f"  Iter {it+1} FAIL: valid={ok}, reason='{reason}', has_vocab={has_vocab}")
                print(f"    raw: {raw!r}")
        passed_runs += case_passes
        print(f"  Result: {case_passes}/5 passed")
        print("-" * 80)

    score = (passed_runs / total_runs) * 100
    print(f"\nFinal Actor Score: {score:.1f}% ({passed_runs}/{total_runs})")

if __name__ == "__main__":
    main()
