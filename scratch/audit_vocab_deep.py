import sys
from app.scenarios.builtins import SCENARIOS

def inspect_suspect_vocab():
    suspects = [
        (8, 24, "commutation"),
        (22, 5, "patisserie"),
        (27, 5, "affidavit"),
        (34, 5, "matriculation"),
        (38, 26, "emulsifier"),
        (41, 26, "camber"),
        (44, 25, "primer"),
        (48, 18, "encumbrance"),
        (49, 5, "actuator"),
        (49, 18, "bushing"),
        (51, 21, "refraction"),
        (66, 18, "substrate")
    ]
    
    print("=== SUSPECT VOCABULARY TASKS IN DETAIL ===")
    for s_idx, t_idx, word in suspects:
        s = SCENARIOS[s_idx]
        t = s.tasks[t_idx]
        print(f"\nS{s_idx:02d} [{s.name}] Task {t_idx:02d} (Word: '{word}')")
        print(f"  Goal:      {t.goal}")
        print(f"  Hint:      {t.hint}")
        print(f"  DoneWhen:  {t.done_when}")

if __name__ == "__main__":
    inspect_suspect_vocab()
