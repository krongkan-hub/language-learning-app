import sys
import re
from app.scenarios.builtins import SCENARIOS

SELECTED_INDICES = [0, 1, 4, 8, 16, 34, 38, 41, 45, 49, 69, 76]

def inspect_12_in_detail():
    print("=== DETAILED LINE-BY-LINE AUDIT OF 12 SELECTED SCENARIOS ===")
    
    for s_idx in SELECTED_INDICES:
        s = SCENARIOS[s_idx]
        print(f"\n==================================================")
        print(f"S{s_idx:02d}: {s.name}")
        print(f"Place: {s.place} | Role: {s.role} | Speaker: {s.speaker}")
        print(f"Total tasks: {len(s.tasks)}")
        
        # Count non-empty scene hints
        non_empty_sh = sum(1 for t in s.tasks if t.scene_hint.strip())
        print(f"Scene hints coverage: {non_empty_sh} / {len(s.tasks)} ({non_empty_sh/len(s.tasks)*100:.1f}%)")
        
        # Find suspicious tasks
        for t_idx, t in enumerate(s.tasks):
            g = t.goal.strip()
            h = t.hint.strip()
            d = t.done_when.strip()
            sh = t.scene_hint.strip()
            
            # Check 1: Job interview leak in non-interview scenarios
            if s_idx != 16 and s_idx != 17 and s_idx != 7 and ("interview" in g.lower() or "salary" in g.lower() or "career goals" in g.lower()):
                print(f"  [CRITICAL: Topic Corruption] T{t_idx:02d}: Goal='{g}' | Hint='{h}'")
                
            # Check 2: Useless vocabulary
            if "Use the word" in g:
                m = re.search(r"Use the word ['\"]([^'\"]+)['\"]", g)
                w = m.group(1) if m else "N/A"
                print(f"  [VOCAB TASK] T{t_idx:02d}: Word='{w}' | Hint='{h}'")
                
            # Check 3: Definition hints
            if " means " in h or " refers to " in h or " is a " in h or " is an " in h:
                print(f"  [PEDANTIC HINT] T{t_idx:02d}: Goal='{g}' | Hint='{h}'")
                
            # Check 4: Domain knowledge
            if any(term in g.lower() for term in ["lapel", "camber", "emulsifier", "din release", "actuator", "bushing", "demurrage", "tariff code"]):
                print(f"  [DOMAIN KNOWLEDGE] T{t_idx:02d}: Goal='{g}' | Hint='{h}'")

if __name__ == "__main__":
    inspect_12_in_detail()
