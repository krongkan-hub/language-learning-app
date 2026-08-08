import re
from app.scenarios.builtins import SCENARIOS

def verify_total_tasks():
    total = sum(len(s.tasks) for s in SCENARIOS)
    print(f"1. Total tasks: {total}")
    assert total == 5520, f"Expected 5520 tasks, got {total}"

def verify_zero_duplicate_vocab_targets():
    vocab_words = {}
    for sc_idx, s in enumerate(SCENARIOS, 1):
        for t_idx, t in enumerate(s.tasks, 1):
            m = re.search(r"Use the word '([^']+)'", t.goal)
            if m:
                w = m.group(1).lower()
                vocab_words.setdefault(w, []).append((sc_idx, s.name, t_idx))

    duplicates = {w: locs for w, locs in vocab_words.items() if len(locs) > 1}
    print(f"5. Zero duplicate vocabulary targets check: total unique={len(vocab_words)}, duplicates count={len(duplicates)}")
    if duplicates:
        for w, locs in duplicates.items():
            print(f"   Duplicate vocab target '{w}': {locs}")
        assert False, f"Found {len(duplicates)} duplicate vocabulary targets catalog-wide!"
    else:
        print("   PASSED: Zero duplicate vocabulary targets found catalog-wide!")

def verify_no_prohibited_terms():
    terms = [
        'DIN', 'actuator', 'bushing', 'wastegate', 'demurrage',
        'harmonized tariff', 'lapel', 'pick stitching', 'emulsifier',
        'commutation', 'matriculation', 'substrate'
    ]
    found_violations = []
    for term in terms:
        # Use word boundary search
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        for sc_idx, s in enumerate(SCENARIOS, 1):
            for t_idx, t in enumerate(s.tasks, 1):
                if pattern.search(t.goal) or pattern.search(t.hint):
                    found_violations.append((term, sc_idx, s.name, t_idx, t.goal, t.hint))

    print(f"6. Prohibited terms check: total terms checked={len(terms)}, violations count={len(found_violations)}")
    if found_violations:
        for term, sc_idx, sname, t_idx, g, h in found_violations:
            print(f"   VIOLATION '{term}': Sc{sc_idx} ({sname}) Task {t_idx}:\n     goal={g!r}\n     hint={h!r}")
        assert False, f"Found {len(found_violations)} violations of prohibited terms!"
    else:
        print("   PASSED: None of the prohibited terms appear in any goal or hint!")

if __name__ == '__main__':
    verify_total_tasks()
    verify_zero_duplicate_vocab_targets()
    verify_no_prohibited_terms()
