import sys
import re
from collections import defaultdict
from app.scenarios.builtins import SCENARIOS

def find_near_duplicates():
    print("=== 7. NEAR-DUPLICATE TASKS AUDIT WITHIN SCENARIOS ===")
    
    total_duplicates = 0
    for s_idx, s in enumerate(SCENARIOS):
        duplicates_in_s = []
        tasks = s.tasks
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                t1 = tasks[i]
                t2 = tasks[j]
                
                # Check normalized similarity between goals
                g1_clean = re.sub(r'[^a-z0-9 ]', '', t1.goal.lower()).strip()
                g2_clean = re.sub(r'[^a-z0-9 ]', '', t2.goal.lower()).strip()
                
                # Strip common prefix filler
                g1_stem = re.sub(r'^(greet the [a-z ]+ and state your purpose|ask about|inquire about|confirm whether|ask if|inquire if|request)\s+', '', g1_clean)
                g2_stem = re.sub(r'^(greet the [a-z ]+ and state your purpose|ask about|inquire about|confirm whether|ask if|inquire if|request)\s+', '', g2_clean)
                
                if g1_stem == g2_stem and len(g1_stem) > 5:
                    duplicates_in_s.append((i, j, t1.goal, t2.goal))
                elif g1_clean == g2_clean:
                    duplicates_in_s.append((i, j, t1.goal, t2.goal))
                    
        if duplicates_in_s:
            total_duplicates += len(duplicates_in_s)
            print(f"\nS{s_idx:02d} [{s.name}] has {len(duplicates_in_s)} near-duplicate task pairs:")
            for item in duplicates_in_s[:10]:
                print(f"  - T{item[0]:02d} vs T{item[1]:02d}:")
                print(f"      T{item[0]:02d}: '{item[2]}'")
                print(f"      T{item[1]:02d}: '{item[3]}'")

    print(f"\nTotal near-duplicate task pairs found: {total_duplicates}")

if __name__ == "__main__":
    find_near_duplicates()
