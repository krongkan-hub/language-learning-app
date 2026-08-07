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
    per_case = []

    print("=" * 80)
    for i, case in enumerate(cases):
        tag = 'expect PASS' if case['expect_done'] else 'expect FAIL'
        print(f"Case {i+1} [{case['type']}, {tag}]: '{case['input'][:58]}' -> '{case['done_when'][:58]}'")
        case_passes = 0
        for it in range(5):
            # Use the case's own NPC context when supplied. The real app always
            # judges with conversation history present, and the judge behaves
            # differently with it, so evaluating bare utterances tests a
            # condition no user ever hits.
            conv = list(case.get('context', [])) + [{'role': 'user', 'content': case['input']}]
            is_done, hint = evaluate_task(case['input'], case['done_when'], conv, case.get('language', 'English'))
            passed = (is_done == case['expect_done'])
            if passed:
                case_passes += 1
            else:
                print(f"  Iter {it+1} FAIL: got is_done={is_done}, hint={hint}")
        passed_runs += case_passes
        per_case.append(case_passes)
        print(f"  Result: {case_passes}/5 passed")
        print("-" * 80)

    score = (passed_runs / total_runs) * 100
    print(f"\nFinal Judge Score: {score:.1f}% ({passed_runs}/{total_runs})")
    fn = sum(1 for c, p in zip(cases, per_case) if c['expect_done'] and p < 5)
    fp = sum(1 for c, p in zip(cases, per_case) if not c['expect_done'] and p < 5)
    print(f"  false negatives (should pass, judged fail): {fn}/{sum(1 for c in cases if c['expect_done'])}")
    print(f"  false positives (should fail, judged pass): {fp}/{sum(1 for c in cases if not c['expect_done'])}")

if __name__ == "__main__":
    main()
