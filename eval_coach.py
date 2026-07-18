import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import _llm_chat, COACH_SYS, COACH_OPTS

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'eval', 'coach_cases.json')

def evaluate_case(case, language="English"):
    system = COACH_SYS.format(language=language)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": case['input']},
    ]
    
    response = _llm_chat(messages=messages, options=COACH_OPTS)
    raw = response['message']['content']
    
    # Check expectation against raw output (since we haven't implemented filtering yet)
    if case['expect'] == 'clean':
        if 'perfectly natural' in raw.lower():
            return True, raw
        # With current prompt, it might still hallucinate corrections.
        return False, raw
        
    if case['expect'] == 'correct':
        must_contain = case.get('must_contain', '').lower()
        must_not_contain = case.get('must_not_contain', '').lower()
        
        raw_lower = raw.lower()
        if must_contain and must_contain not in raw_lower:
            return False, raw
        if must_not_contain and must_not_contain in raw_lower:
            return False, raw
            
        return True, raw
        
    return False, raw

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
        print(f"Case {i+1}: {case['input']} (Expect: {case['expect']})")
        case_passes = 0
        for it in range(5):
            passed, output = evaluate_case(case)
            if passed:
                case_passes += 1
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
            # print(f"  Iter {it+1}: {status}")
            # print(f"    Output: {output}")
            
        passed_runs += case_passes
        print(f"  Result: {case_passes}/5 passed")
        print("-" * 80)
        
    score = (passed_runs / total_runs) * 100
    print(f"\nFinal Score: {score:.1f}% ({passed_runs}/{total_runs})")
    
if __name__ == "__main__":
    main()
