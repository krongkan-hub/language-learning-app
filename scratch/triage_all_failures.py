import json

with open('scratch/playtest_71_80_results.json') as f:
    data = json.load(f)

print("=" * 80)
print("COMPREHENSIVE TRIAGE REPORT FOR ALL FAILED PLAYTEST TASKS")
print("=" * 80)

failures = []

for scen_name, sdata in data.items():
    scen_num = sdata['scen_num']
    for t in sdata['tasks']:
        if not t['passed']:
            failures.append({
                'scen_num': scen_num,
                'scen_name': scen_name,
                'task_num': t['task_num'],
                'goal': t['goal'],
                'done_when': t['done_when'],
                'history': t['history']
            })

print(f"Total Failed Tasks in Dataset: {len(failures)}\n")

for idx, item in enumerate(failures, 1):
    print(f"#{idx:02d}. Scenario {item['scen_num']} ({item['scen_name']}) — Task {item['task_num']:02d}: '{item['goal']}'")
    print(f"    Done_when: \"{item['done_when']}\"")
    history = item['history']
    print(f"    Dialogue History:")
    for turn in history[-4:]:
        role = turn['role'].upper()
        content = turn['content'].replace('\n', ' ')
        print(f"      {role}: {content[:100]}...")
    print("-" * 80)
