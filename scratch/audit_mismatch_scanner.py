import sys
from app.scenarios.builtins import SCENARIOS

def check_scenario_alignment():
    print("=== SCENARIO CONTENT ALIGNMENT CHECK ===")
    for idx, s in enumerate(SCENARIOS):
        print(f"\n--- Scenario [{idx}] {s.name} ---")
        print(f"  Place: {s.place} | Role: {s.role} | Speaker: {s.speaker}")
        # Print first 5 goals and last 5 goals
        first_3 = [t.goal for t in s.tasks[:3]]
        last_3 = [t.goal for t in s.tasks[-3:]]
        print(f"  First 3 goals: {first_3}")
        print(f"  Last 3 goals:  {last_3}")

if __name__ == "__main__":
    check_scenario_alignment()
