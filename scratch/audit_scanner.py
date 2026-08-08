import sys
import re
from typing import List, Dict, Any

from app.scenarios.builtins import SCENARIOS

def analyze_catalog():
    print(f"Total Scenarios: {len(SCENARIOS)}")
    total_tasks = sum(len(s.tasks) for s in SCENARIOS)
    print(f"Total Tasks: {total_tasks}")

    # Inspect all scenarios
    for idx, s in enumerate(SCENARIOS):
        print(f"[{idx}] {s.name} (place: {s.place}, role: {s.role}, speaker: {s.speaker}, tasks: {len(s.tasks)})")

if __name__ == "__main__":
    analyze_catalog()
