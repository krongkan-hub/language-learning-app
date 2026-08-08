import sys

sys.path.insert(0, '.')
from app.scenarios.builtins import SCENARIOS

sc1 = SCENARIOS[0]

print(f"Scenario 1 total tasks: {len(sc1.tasks)}")
for i, t in enumerate(sc1.tasks):
    sh = f" [SH: {t.scene_hint!r}]" if t.scene_hint else ""
    react = " [REACT]" if t.reactive else ""
    adv = " [ADV]" if t.difficulty == "advanced" else ""
    p = f" [P{t.phase}]" if t.phase else ""
    print(f"{i:2d}: {t.goal}{adv}{react}{p}{sh}")
