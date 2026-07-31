import json
import os
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.judge import evaluate_task, judge_deterministic, judge_llm, JUDGE_OPTS

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'eval', 'judge_cases.json')

def main():
    if not os.path.exists(FIXTURE_PATH):
        print(f"Fixture not found: {FIXTURE_PATH}")
        sys.exit(1)

    with open(FIXTURE_PATH, 'r') as f:
        cases = json.load(f)

    print(f"Running Judge Eval on {len(cases)} cases across 5 iterations (max_tokens={JUDGE_OPTS.get('max_tokens')})...")
    total_runs = len(cases) * 5
    passed_runs = 0

    print("=" * 80)
    for i, case in enumerate(cases):
        print(f"Case {i+1} [{case['type']}]: '{case['input']}' -> Goal: '{case['done_when']}'")
        case_passes = 0
        for it in range(5):
            conv = [{'role': 'user', 'content': case['input']}]
            is_done, hint = evaluate_task(case['input'], case['done_when'], conv, case.get('language', 'English'))
            passed = (is_done == case['expect_done'])
            if passed:
                case_passes += 1
            else:
                print(f"  Iter {it+1} FAIL: got is_done={is_done}, hint={hint}")
        passed_runs += case_passes
        print(f"  Result: {case_passes}/5 passed")
        print("-" * 80)

    score = (passed_runs / total_runs) * 100
    print(f"\nFinal Judge Score: {score:.1f}% ({passed_runs}/{total_runs})")

if __name__ == "__main__":
    main()
