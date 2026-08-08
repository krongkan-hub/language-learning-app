import sys
import re
from app.scenarios.builtins import SCENARIOS

def inspect_mismatches_deep():
    print("=== 5. GOAL VS DONE_WHEN MISMATCH DEEP INSPECTION ===")
    
    mismatches = []
    
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            g = t.goal.strip()
            d = t.done_when.strip()
            
            # Key checks:
            # 1. Action mismatch (Ask vs State / Order vs Decline / Confirm vs Inquire)
            # 2. Specific Noun mismatch (e.g. power outlet vs charging station, coffee vs tea, etc.)
            
            # Simple keyword extraction
            g_lower = g.lower()
            d_lower = d.lower()
            
            # Check specific discrepancies
            # Goal asks, done_when checks statement (or vice versa)
            if g_lower.startswith("ask ") and (" learner stated " in d_lower or " learner explained " in d_lower or " learner described " in d_lower):
                mismatches.append((s_idx, s.name, t_idx, g, d, "Goal asks for a question, but DoneWhen checks for a statement/explanation"))
            elif (g_lower.startswith("say ") or g_lower.startswith("state ") or g_lower.startswith("explain ")) and (" learner asked " in d_lower or " learner inquired " in d_lower):
                mismatches.append((s_idx, s.name, t_idx, g, d, "Goal asks for a statement, but DoneWhen checks for a question"))
                
            # Check content noun mismatch
            # Find nouns in goal not in done_when and vice versa
            g_nouns = set(re.findall(r'\b[a-z]{4,}\b', g_lower)) - {'learner', 'asked', 'about', 'whether', 'would', 'could', 'their', 'with', 'have', 'from', 'this', 'that', 'your', 'please', 'word', 'inquire', 'request', 'state', 'confirm', 'express', 'address'}
            d_nouns = set(re.findall(r'\b[a-z]{4,}\b', d_lower)) - {'learner', 'asked', 'about', 'whether', 'would', 'could', 'their', 'with', 'have', 'from', 'this', 'that', 'your', 'please', 'word', 'inquire', 'request', 'state', 'confirm', 'express', 'address', 'explicitly', 'mentioned'}
            
            # If goal has specific distinct nouns not in done_when
            # e.g. "outlet" vs "charging station", "wifi" vs "internet", etc.
            diff = g_nouns - d_nouns
            if len(g_nouns) > 0 and len(d_nouns) > 0 and len(g_nouns.intersection(d_nouns)) == 0:
                mismatches.append((s_idx, s.name, t_idx, g, d, f"Zero overlapping key terms between Goal and DoneWhen"))

    print(f"Total potential mismatches flagged: {len(mismatches)}")
    for m in mismatches[:30]:
        print(f"\nS{m[0]:02d} [{m[1]}] Task {m[2]:02d} ({m[5]}):")
        print(f"  Goal:     '{m[3]}'")
        print(f"  DoneWhen: '{m[4]}'")

if __name__ == "__main__":
    inspect_mismatches_deep()
