import sys
import re
from app.scenarios.builtins import SCENARIOS

def audit_hints():
    print("=== 4. HINT QUALITY AUDIT ===")
    
    empty_hints = []
    goal_repeats = []
    giveaways = []
    rigid_syntax = []
    trivial_hints = []
    
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            g = t.goal.strip()
            h = t.hint.strip()
            
            if not h:
                empty_hints.append((s_idx, s.name, t_idx, g))
                continue
                
            if g.lower() == h.lower():
                goal_repeats.append((s_idx, s.name, t_idx, g, h))
                
            # Check trivial hints like "You need to communicate this." or "Ask about this." without giving useful orientation
            if h in ["You need to communicate this.", "You need information.", "Ask about this."]:
                trivial_hints.append((s_idx, s.name, t_idx, g, h))
                
            # Check giveaways (e.g., "Say: 'I would like...'" or "Say '...'")
            if re.search(r"say ['\"].*['\"]", h, re.IGNORECASE) or re.search(r"ask ['\"].*['\"]", h, re.IGNORECASE):
                giveaways.append((s_idx, s.name, t_idx, g, h))
                
            # Check rigid syntax forcing
            if "must use" in h.lower() or "exactly" in h.lower():
                rigid_syntax.append((s_idx, s.name, t_idx, g, h))

    print(f"Total tasks: {sum(len(s.tasks) for s in SCENARIOS)}")
    print(f"Empty hints: {len(empty_hints)}")
    print(f"Goal repeats: {len(goal_repeats)}")
    print(f"Trivial filler hints (e.g. 'You need to communicate this.'): {len(trivial_hints)}")
    print(f"Giveaways (quoting exact text to say): {len(giveaways)}")
    print(f"Rigid syntax hints: {len(rigid_syntax)}")
    
    print("\n--- Sample Trivial Filler Hints ---")
    for item in trivial_hints[:15]:
        print(f"  S{item[0]:02d} [{item[1]}] T{item[2]:02d}: Goal='{item[3]}' | Hint='{item[4]}'")

    print("\n--- Sample Giveaways ---")
    for item in giveaways[:15]:
        print(f"  S{item[0]:02d} [{item[1]}] T{item[2]:02d}: Goal='{item[3]}' | Hint='{item[4]}'")

if __name__ == "__main__":
    audit_hints()
