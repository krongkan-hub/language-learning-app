import sys
import re
from app.scenarios.builtins import SCENARIOS

def inspect_vocab_list():
    word_pattern = re.compile(r"Use the word ['\"]([^'\"]+)['\"]", re.IGNORECASE)
    
    print("=== FULL VOCABULARY WORD LIST BY SCENARIO ===")
    for s_idx, s in enumerate(SCENARIOS):
        words = []
        for t_idx, t in enumerate(s.tasks):
            m = word_pattern.search(t.goal)
            if m:
                words.append((t_idx, m.group(1)))
        if words:
            print(f"S{s_idx:02d} [{s.name}]: {', '.join([f'T{t}:{w}' for t, w in words])}")

if __name__ == "__main__":
    inspect_vocab_list()
