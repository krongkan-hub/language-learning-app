import sys
import re
from app.scenarios.builtins import SCENARIOS

def inspect_substantive_mismatches():
    print("=== SUBSTANTIVE GOAL VS DONE_WHEN MISMATCHES ===")
    
    findings = []
    
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            g = t.goal.strip()
            d = t.done_when.strip()
            
            g_low = g.lower()
            d_low = d.lower()
            
            # Check cases where goal mentions a specific entity or concept, but done_when requires something completely different or narrower/broader
            # e.g., Goal: ask about X, DoneWhen: check for Y
            
            # 1. Action type mismatch: goal is Ask, done_when requires Explain/State (or vice versa)
            is_goal_ask = g_low.startswith("ask") or g_low.startswith("inquire")
            is_done_ask = "asked" in d_low or "inquired" in d_low or "question" in d_low
            is_done_state = "stated" in d_low or "explained" in d_low or "described" in d_low or "mentioned" in d_low or "provided" in d_low
            
            if is_goal_ask and is_done_state and not is_done_ask:
                findings.append((s_idx, s.name, t_idx, g, d, "Goal asks/inquires, but DoneWhen requires stating/explaining without asking"))
                
            # 2. Key noun mismatch
            # Example from prompt: goal about power outlets vs done_when about charging stations
            # Let's check for specific noun mismatches
            g_nouns = set(re.findall(r'\b[a-z]{4,}\b', g_low))
            d_nouns = set(re.findall(r'\b[a-z]{4,}\b', d_low))
            
            ignore = {'learner', 'asked', 'about', 'whether', 'would', 'could', 'their', 'with', 'have', 'from', 'this', 'that', 'your', 'please', 'inquire', 'request', 'state', 'confirm', 'express', 'address', 'explicitly', 'mentioned', 'inquired', 'stated', 'explained', 'described', 'provided', 'say'}
            g_sub = g_nouns - ignore
            d_sub = d_nouns - ignore
            
            # Look for specific cases where g_sub has terms not present in d_sub
            if "outlet" in g_sub and "charging" in d_sub:
                findings.append((s_idx, s.name, t_idx, g, d, "Outlet vs Charging Station mismatch"))
            if "seat" in g_sub and "table" in d_sub:
                findings.append((s_idx, s.name, t_idx, g, d, "Seat vs Table mismatch"))

    print(f"Total substantive mismatches found: {len(findings)}")
    for f in findings[:25]:
        print(f"\nS{f[0]:02d} [{f[1]}] Task {f[2]:02d} - Reason: {f[5]}")
        print(f"  Goal:     '{f[3]}'")
        print(f"  DoneWhen: '{f[4]}'")

if __name__ == "__main__":
    inspect_substantive_mismatches()
