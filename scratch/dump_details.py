import sys
import os

sys.path.insert(0, '.')
from app.scenarios.builtins import SCENARIOS

def dump_scenario(idx, filename):
    sc = SCENARIOS[idx]
    with open(filename, 'w') as f:
        f.write(f"Scenario {idx + 1}: {sc.name}\n")
        f.write("=" * 80 + "\n\n")
        for i, t in enumerate(sc.tasks):
            f.write(f"Task index {i}:\n")
            f.write(f"  Goal:       {t.goal!r}\n")
            f.write(f"  Hint:       {t.hint!r}\n")
            f.write(f"  Done_when:  {t.done_when!r}\n")
            f.write(f"  Phase:      {t.phase}\n")
            f.write(f"  Difficulty: {t.difficulty!r}\n")
            f.write(f"  Reactive:   {t.reactive}\n")
            f.write(f"  Scene_hint: {t.scene_hint!r}\n")
            f.write("\n")

dump_scenario(0, "scratch/sc1.txt")
dump_scenario(2, "scratch/sc3.txt")
dump_scenario(3, "scratch/sc4.txt")
dump_scenario(4, "scratch/sc5.txt")
print("Dumped sc1, sc3, sc4, sc5 to scratch/")
