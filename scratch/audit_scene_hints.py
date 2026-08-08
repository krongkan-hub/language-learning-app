import sys
from collections import Counter
from app.scenarios.builtins import SCENARIOS

def audit_scene_hints():
    print("=== 3. SCENE HINT QUALITY AUDIT ===")
    
    empty_count = 0
    non_empty_count = 0
    
    scene_hints_by_scenario = {}
    
    for s_idx, s in enumerate(SCENARIOS):
        sh_list = []
        for t_idx, t in enumerate(s.tasks):
            sh = t.scene_hint.strip()
            if sh:
                non_empty_count += 1
                sh_list.append((t_idx, sh))
            else:
                empty_count += 1
        scene_hints_by_scenario[s.name] = sh_list

    print(f"Total Tasks: {empty_count + non_empty_count}")
    print(f"Empty scene_hints: {empty_count} ({empty_count / (empty_count + non_empty_count) * 100:.1f}%)")
    print(f"Non-empty scene_hints: {non_empty_count} ({non_empty_count / (empty_count + non_empty_count) * 100:.1f}%)")
    
    print("\nBreakdown of scene_hints per scenario:")
    for s_name, sh_list in scene_hints_by_scenario.items():
        if len(sh_list) > 0:
            print(f"  [{s_name}]: {len(sh_list)} tasks have scene_hints")
        else:
            print(f"  [{s_name}]: 0 tasks have scene_hints (100% EMPTY)")

if __name__ == "__main__":
    audit_scene_hints()
