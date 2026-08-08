import sys
import re
from collections import defaultdict, Counter
from app.scenarios.builtins import SCENARIOS

def analyze_all_vocabulary():
    print("=== 1. FULL VOCABULARY WORD EXTRACTION ===")
    word_pattern = re.compile(r"Use the word ['\"]([^'\"]+)['\"]", re.IGNORECASE)
    all_vocab = []
    
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            m = word_pattern.search(t.goal)
            if m:
                word = m.group(1)
                all_vocab.append((s_idx, s.name, t_idx, word, t.goal, t.hint))
            elif "Use the word" in t.goal or "Use the word" in t.hint:
                all_vocab.append((s_idx, s.name, t_idx, "UNKNOWN", t.goal, t.hint))

    print(f"Total vocabulary tasks across all scenarios: {len(all_vocab)}")
    
    # Categorize vocabulary words to evaluate quality
    for s_idx, s_name, t_idx, word, g, h in all_vocab:
        # Check for technical/hyper-niche/obscure words
        print(f"S{s_idx:02d} [{s_name}] T{t_idx:02d}: '{word}' -> Goal: '{g}' | Hint: '{h}'")

if __name__ == "__main__":
    analyze_all_vocabulary()
