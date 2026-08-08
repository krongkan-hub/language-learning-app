import sys
import re
from app.scenarios.builtins import SCENARIOS

def find_semantic_duplicates():
    print("=== DEEP SEMANTIC NEAR-DUPLICATES AUDIT ===")
    
    total_semantic_dups = 0
    for s_idx, s in enumerate(SCENARIOS):
        tasks = s.tasks
        dups = []
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                g1 = set(re.findall(r'\b[a-z]{3,}\b', tasks[i].goal.lower())) - {'greet', 'state', 'your', 'purpose', 'ask', 'inquire', 'confirm', 'whether', 'request', 'about', 'the', 'and', 'for', 'with'}
                g2 = set(re.findall(r'\b[a-z]{3,}\b', tasks[j].goal.lower())) - {'greet', 'state', 'your', 'purpose', 'ask', 'inquire', 'confirm', 'whether', 'request', 'about', 'the', 'and', 'for', 'with'}
                
                if len(g1) >= 2 and len(g2) >= 2:
                    jaccard = len(g1.intersection(g2)) / len(g1.union(g2))
                    if jaccard >= 0.75:
                        dups.append((i, j, tasks[i].goal, tasks[j].goal, jaccard))
                        
        if dups:
            total_semantic_dups += len(dups)
            print(f"\nS{s_idx:02d} [{s.name}] ({len(dups)} semantic near-duplicate pairs):")
            for item in dups[:10]:
                print(f"  - T{item[0]:02d} vs T{item[1]:02d} (Jaccard: {item[4]:.2f}):")
                print(f"      T{item[0]:02d}: '{item[2]}'")
                print(f"      T{item[1]:02d}: '{item[3]}'")

    print(f"\nTotal semantic near-duplicate task pairs: {total_semantic_dups}")

if __name__ == "__main__":
    find_semantic_duplicates()
