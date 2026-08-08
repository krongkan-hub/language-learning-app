import sys
from app.scenarios.builtins import SCENARIOS

SELECTED_INDICES = [0, 1, 4, 8, 16, 34, 38, 41, 45, 49, 69, 76]

def dump_selected_scenarios():
    for s_idx in SELECTED_INDICES:
        s = SCENARIOS[s_idx]
        print(f"\n================================================================================")
        print(f"SCENARIO [{s_idx:02d}] {s.name.upper()}")
        print(f"Place: {s.place} | Role: {s.role} | Speaker: {s.speaker}")
        print(f"================================================================================")
        for t_idx, t in enumerate(s.tasks):
            print(f"T{t_idx:02d} [Phase {t.phase}, Diff: {t.difficulty}, Reactive: {t.reactive}]")
            print(f"  Goal:       {t.goal}")
            print(f"  Hint:       {t.hint}")
            print(f"  DoneWhen:   {t.done_when}")
            if t.scene_hint:
                print(f"  SceneHint:  {t.scene_hint}")
            print("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ")

if __name__ == "__main__":
    dump_selected_scenarios()
