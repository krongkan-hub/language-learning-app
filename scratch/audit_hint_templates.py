import sys
import re
from collections import Counter
from app.scenarios.builtins import SCENARIOS

def find_hint_templates():
    print("=== HINT TEMPLATE & FILLER PHRASE SEARCH ===")
    
    phrases = [
        "you need information",
        "you need to communicate this",
        "you want to buy this",
        "you need a table",
        "ask if",
        "say you",
        "mention that",
        "inquire about"
    ]
    
    counts = Counter()
    template_hints = []
    
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            h_lower = t.hint.lower()
            for p in phrases:
                if p in h_lower:
                    counts[p] += 1
                    
    print("Template phrase occurrences in hints:")
    for p, c in counts.most_common():
        print(f"  [{c:4d}x] '{p}'")

    print("\nLet's check hints that give away exact dictionary definitions vs orientation:")
    def_hints = []
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            if " means " in t.hint or " refers to " in t.hint or " is an " in t.hint or " is a " in t.hint:
                def_hints.append((s_idx, s.name, t_idx, t.goal, t.hint))

    print(f"Hints containing dictionary definitions: {len(def_hints)}")
    for item in def_hints[:15]:
        print(f"  S{item[0]:02d} [{item[1]}] T{item[2]:02d}: Goal='{item[3]}' | Hint='{item[4]}'")

if __name__ == "__main__":
    find_hint_templates()
