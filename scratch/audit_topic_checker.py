import sys
from app.scenarios.builtins import SCENARIOS

def audit_topics():
    print("=== DEEP SCENARIO TOPIC MISMATCH AUDIT ===")
    mismatches = []
    
    for idx, s in enumerate(SCENARIOS):
        name = s.name
        place = s.place
        role = s.role
        
        # Check first 10 goals
        sample_goals = [t.goal for t in s.tasks[:10]]
        sample_hints = [t.hint for t in s.tasks[:10]]
        
        # Combine text
        text = " ".join(sample_goals + sample_hints).lower()
        
        # Keywords expected vs unexpected
        print(f"\nS{idx:02d}: [{name}]")
        print(f"   Place: {place}")
        print(f"   Sample Goal 0: {s.tasks[0].goal}")
        print(f"   Sample Goal 1: {s.tasks[1].goal}")
        print(f"   Sample Goal 2: {s.tasks[2].goal}")
        print(f"   Sample Goal 5: {s.tasks[5].goal}")

if __name__ == "__main__":
    audit_topics()
