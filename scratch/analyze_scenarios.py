import sys
import os

sys.path.insert(0, '.')
from app.scenarios.builtins import SCENARIOS

target_sc_indices = [0, 2, 3, 4]  # Scenario 1, 3, 4, 5

for idx in target_sc_indices:
    sc = SCENARIOS[idx]
    print("=" * 80)
    print(f"Scenario {idx + 1}: {sc.name} ({len(sc.tasks)} tasks)")
    print("=" * 80)
    
    sh_count = sum(1 for t in sc.tasks if t.scene_hint and t.scene_hint.strip())
    react_count = sum(1 for t in sc.tasks if t.reactive)
    adv_count = sum(1 for t in sc.tasks if t.difficulty == "advanced")
    vocab_tasks = [(i, t) for i, t in enumerate(sc.tasks) if "Learner used the word" in t.done_when or "Use the word" in t.goal]
    p1_count = sum(1 for t in sc.tasks if t.phase == 1)
    p2_count = sum(1 for t in sc.tasks if t.phase == 2 or t.phase is None or t.phase == 0) # default/none
    p3_count = sum(1 for t in sc.tasks if t.phase == 3)
    
    print(f"Metrics: Hint={sh_count} (req 10-16) | React={react_count} (req 14-18) | Adv={adv_count} (req 19-24) | Vocab={len(vocab_tasks)} (req 4-6) | P1={p1_count} (req >=5) | P3={p3_count} (req >=8)")
    print("\nVocab tasks:")
    for i, t in vocab_tasks:
        print(f"  [{i}] {t.goal} | Hint: {t.hint}")
        
    print("\nScene Hints:")
    sh_tasks = [(i, t) for i, t in enumerate(sc.tasks) if t.scene_hint and t.scene_hint.strip()]
    for i, t in sh_tasks:
        print(f"  [{i}] Goal: {t.goal} | Hint: {t.scene_hint}")
