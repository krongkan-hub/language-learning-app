import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ai_playtester import playtest_task
from app.scenarios.builtins import SCENARIOS

def run_playtest_scenarios_71_to_80():
    print("=" * 80)
    print("EXECUTING LIVE PLAYTEST: SCENARIOS 71 TO 80 (150 TASKS TOTAL)")
    print("=" * 80)

    results = {}
    total_passed = 0
    total_tasks = 0

    for s_idx in range(70, 80):
        scen = SCENARIOS[s_idx]
        scen_num = s_idx + 1
        print(f"\n" + "="*80)
        print(f"--- PLAYTESTING SCENARIO {scen_num}: {scen.name} ({len(scen.tasks)} Tasks) ---")
        print(f"Place: {scen.place} | Role: {scen.role[:60]}...")
        print("="*80)

        scen_results = []
        scen_passed_count = 0

        for t_idx, task in enumerate(scen.tasks):
            total_tasks += 1
            success, history = playtest_task(scen, task, max_attempts=3)
            status_str = "✅ PASS" if success else "❌ FAIL"
            if success:
                scen_passed_count += 1
                total_passed += 1
            
            print(f"Task {t_idx+1:02d} [{status_str}]: {task.goal}")
            if not success:
                print(f"   Done_when: {task.done_when}")
                print(f"   Last turn dialogue history:")
                for msg in history[-3:]:
                    print(f"     {msg['role'].upper()}: {msg['content']}")
            
            scen_results.append({
                'task_num': t_idx + 1,
                'goal': task.goal,
                'done_when': task.done_when,
                'passed': success,
                'history': history
            })

        pass_rate = (scen_passed_count / len(scen.tasks)) * 100
        print(f"\nScenario {scen_num} ({scen.name}) Final Score: {scen_passed_count}/{len(scen.tasks)} passed ({pass_rate:.1f}%)")
        results[scen.name] = {
            'scen_num': scen_num,
            'passed': scen_passed_count,
            'total': len(scen.tasks),
            'pass_rate': pass_rate,
            'tasks': scen_results
        }

    overall_pass_rate = (total_passed / total_tasks) * 100
    print("\n" + "=" * 80)
    print("       🏁 FINAL PLAYTEST SUITE SUMMARY (SCENARIOS 71 - 80)")
    print("=" * 80)
    for name, data in results.items():
        print(f"Scenario {data['scen_num']:02d} ({name}): {data['passed']}/{data['total']} passed ({data['pass_rate']:.1f}%)")
    print(f"\nOVERALL BATCH PASS RATE: {total_passed}/{total_tasks} passed ({overall_pass_rate:.1f}%)")
    print("=" * 80)

    # Save detailed JSON log for analysis
    with open('scratch/playtest_71_80_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    run_playtest_scenarios_71_to_80()
