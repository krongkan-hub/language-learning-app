import re
import sys

def apply_fixes():
    with open('app/scenarios/builtins.py', 'r') as f:
        content = f.read()

    with open('scratch/sc0_fixed.py', 'r') as f:
        sc0_text = f.read().strip()
    with open('scratch/sc2_fixed.py', 'r') as f:
        sc2_text = f.read().strip()
    with open('scratch/sc3_fixed.py', 'r') as f:
        sc3_text = f.read().strip()
    with open('scratch/sc4_fixed.py', 'r') as f:
        sc4_text = f.read().strip()

    # Replace scenario_0_tasks
    content = re.sub(
        r'scenario_0_tasks = \[\n.*?\n\]\n\n# Scenario: Airport',
        f'{sc0_text}\n\n# Scenario: Airport',
        content,
        flags=re.DOTALL
    )

    # Replace scenario_2_tasks
    content = re.sub(
        r'scenario_2_tasks = \[\n.*?\n\]\n\n# Scenario: Pharmacy',
        f'{sc2_text}\n\n# Scenario: Pharmacy',
        content,
        flags=re.DOTALL
    )

    # Replace scenario_3_tasks
    content = re.sub(
        r'scenario_3_tasks = \[\n.*?\n\]\n\n# Scenario: Hotel',
        f'{sc3_text}\n\n# Scenario: Hotel',
        content,
        flags=re.DOTALL
    )

    # Replace scenario_4_tasks
    content = re.sub(
        r'scenario_4_tasks = \[\n.*?\n\]\n\n# Scenario: Customs',
        f'{sc4_text}\n\n# Scenario: Customs',
        content,
        flags=re.DOTALL
    )

    with open('app/scenarios/builtins.py', 'w') as f:
        f.write(content)

    print("Successfully updated app/scenarios/builtins.py")

if __name__ == '__main__':
    apply_fixes()
