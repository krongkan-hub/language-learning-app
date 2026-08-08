import sys
from app.scenarios.builtins import SCENARIOS

def verify_all_scenario_topics():
    print("=== SCENARIO TOPIC VERIFICATION ===")
    for idx, s in enumerate(SCENARIOS):
        goals_text = " ".join([t.goal.lower() for t in s.tasks])
        hints_text = " ".join([t.hint.lower() for t in s.tasks])
        combined = goals_text + " " + hints_text
        
        print(f"\nS{idx:02d}: {s.name} (Place: {s.place}, Role: {s.role}, Speaker: {s.speaker})")
        
        # Check specific keywords for sanity
        if idx == 1: # Airport Check-in
            if "interview" in combined or "salary" in combined or "resume" in combined:
                print("  [CRITICAL DEFECT] S01 contains Job Interview tasks instead of Airport Check-in tasks!")
                
        # Check other scenarios for keywords that don't match
        # Let's inspect first 3 and last 3 goals of every scenario
        print(f"  Sample T0-T2: {[t.goal for t in s.tasks[:3]]}")
        print(f"  Sample T66-T68: {[t.goal for t in s.tasks[66:]]}")

if __name__ == "__main__":
    verify_all_scenario_topics()
