import sys
import json
import re
from difflib import SequenceMatcher

def get_first_sentence(text: str) -> str:
    s = re.split(r'[.!?]', text.strip())
    return s[0].strip().lower() if s else ''

def is_echo(prev_assistant: str, curr_user: str) -> bool:
    p = prev_assistant.strip().lower()
    c = curr_user.strip().lower()
    if not p or not c:
        return False
    # Sequence similarity ratio
    ratio = SequenceMatcher(None, p, c).ratio()
    if ratio >= 0.55:
        return True
    # First sentence match (if non-trivial length)
    p_first = get_first_sentence(p)
    c_first = get_first_sentence(c)
    if len(p_first) > 15 and p_first == c_first:
        return True
    # Substring match (at least 20 chars)
    if len(p) >= 20 and p in c:
        return True
    if len(c) >= 20 and c in p:
        return True
    return False

def analyze_results(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    total = len(results)
    passed_list = [r for r in results if r.get('passed')]
    failed_list = [r for r in results if not r.get('passed')]
    
    pass_count = len(passed_list)
    fail_count = len(failed_list)
    pass_rate = (pass_count / total * 100) if total > 0 else 0.0
    
    pass_echo_count = 0
    for r in passed_list:
        tr = r.get('transcript', [])
        for i in range(1, len(tr)):
            if tr[i-1].get('role') == 'assistant' and tr[i].get('role') == 'user':
                if is_echo(tr[i-1].get('content', ''), tr[i].get('content', '')):
                    pass_echo_count += 1
                    break

    fail_echo_count = 0
    for r in failed_list:
        tr = r.get('transcript', [])
        for i in range(1, len(tr)):
            if tr[i-1].get('role') == 'assistant' and tr[i].get('role') == 'user':
                if is_echo(tr[i-1].get('content', ''), tr[i].get('content', '')):
                    fail_echo_count += 1
                    break

    pass_echo_rate = (pass_echo_count / pass_count * 100) if pass_count > 0 else 0.0
    fail_echo_rate = (fail_echo_count / fail_count * 100) if fail_count > 0 else 0.0
    total_echo_count = pass_echo_count + fail_echo_count
    total_echo_rate = (total_echo_count / total * 100) if total > 0 else 0.0

    print(f"File: {filepath}")
    print(f"Total tasks: {total}")
    print(f"Passes: {pass_count}/{total} ({pass_rate:.1f}%)")
    print(f"Failures: {fail_count}/{total} ({100 - pass_rate:.1f}%)")
    print(f"Echo rate in passed tasks:  {pass_echo_count}/{pass_count} ({pass_echo_rate:.1f}%)")
    print(f"Echo rate in failed tasks:  {fail_echo_count}/{fail_count} ({fail_echo_rate:.1f}%)")
    print(f"Overall echo rate:          {total_echo_count}/{total} ({total_echo_rate:.1f}%)")

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'scratch/playtest_sample_results.json'
    analyze_results(path)
