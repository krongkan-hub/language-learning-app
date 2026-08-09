import json
import os
import re
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.llm import _llm_chat
from app.coach import filter_coach_output, COACH_SYS, COACH_OPTS

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'eval', 'coach_cases.json')

def evaluate_case(case):
    language = case.get('language', 'English')
    system = COACH_SYS.format(language=language)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": case['input']},
    ]

    response = _llm_chat(messages=messages, options=COACH_OPTS)
    raw = response['message']['content']
    # Score the same filtered text the learner actually sees, not the raw
    # model output — otherwise this eval can pass while the shipped output
    # (post-dedupe/no-op-collapse) fails, or vice versa.
    output = filter_coach_output(raw)
    # must_contain/must_not_contain are about the correction itself, not the
    # bonus "Level up" suggestion — split it off so an unrelated (legitimate)
    # alternative phrasing there can't flip a correctness check.
    feedback_only = re.split(r'⬆️\s*Level up:', output)[0]

    if case['expect'] == 'clean':
        if 'perfectly natural' in feedback_only.lower():
            return True, output
        # With current prompt, it might still hallucinate corrections.
        return False, output

    if case['expect'] == 'correct':
        # must_contain may be a single string or a list of acceptable
        # alternatives (any one present = pass) — several inputs have more than
        # one equally-valid correction (e.g. 欲しいだ → ください / お願いします /
        # ほしい), and demanding one exact target would fail a correct coach.
        must_contain = case.get('must_contain', '')
        alternatives = must_contain if isinstance(must_contain, list) else [must_contain]
        alternatives = [a.lower() for a in alternatives if a]
        must_not_contain = case.get('must_not_contain', '').lower()

        feedback_lower = feedback_only.lower()
        if alternatives and not any(a in feedback_lower for a in alternatives):
            return False, output
        if must_not_contain and must_not_contain in feedback_lower:
            return False, output

        return True, output

    return False, output

def main():
    if not os.path.exists(FIXTURE_PATH):
        print(f"Fixture not found: {FIXTURE_PATH}")
        sys.exit(1)
        
    with open(FIXTURE_PATH, 'r') as f:
        cases = json.load(f)
        
    print(f"Running eval on {len(cases)} cases, 5 iterations each (temp={COACH_OPTS.get('temperature', 0.2)})...")
    
    total_runs = len(cases) * 5
    passed_runs = 0
    
    print("\n" + "="*80)
    
    for i, case in enumerate(cases):
        language = case.get('language', 'English')
        print(f"Case {i+1} [{language}]: {case['input']} (Expect: {case['expect']})")
        case_passes = 0
        for it in range(5):
            passed, output = evaluate_case(case)
            if passed:
                case_passes += 1
            # print(f"  Iter {it+1}")
            # print(f"    Output: {output}")
            
        passed_runs += case_passes
        print(f"  Result: {case_passes}/5 passed")
        print("-" * 80)
        
    score = (passed_runs / total_runs) * 100
    print(f"\nFinal Score: {score:.1f}% ({passed_runs}/{total_runs})")
    
if __name__ == "__main__":
    main()
