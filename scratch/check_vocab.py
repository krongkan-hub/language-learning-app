import re
import sys

sys.path.insert(0, '.')
from app.scenarios.builtins import SCENARIOS

vocab_by_sc = {}
all_vocab = {}

for si, s in enumerate(SCENARIOS):
    for ti, t in enumerate(s.tasks):
        m = re.match(r"Use the word '(.+)'", t.goal)
        if m:
            w = m.group(1).lower()
            vocab_by_sc.setdefault(si, []).append((w, ti, t.goal, t.hint))
            all_vocab.setdefault(w, []).append((si, ti))

print(f"Total distinct vocab words across all scenarios: {len(all_vocab)}")
print("\nVocab words in target scenarios (1, 3, 4, 5):")
for sc_num in [1, 3, 4, 5]:
    si = sc_num - 1
    print(f"\nScenario {sc_num} ({SCENARIOS[si].name}):")
    for w, ti, g, h in vocab_by_sc.get(si, []):
        print(f"  [{ti}] {g} -> hint: {h}")

print("\nAll vocab targets across catalog:")
for w in sorted(all_vocab.keys()):
    if len(all_vocab[w]) > 1:
        print(f"  DUPLICATE: {w} -> {all_vocab[w]}")
