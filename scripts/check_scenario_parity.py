import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scenarios.builtins import SCENARIOS

def calculate_metrics(scenario_list):
    total_tasks = sum(len(s.tasks) for s in scenario_list)
    if total_tasks == 0:
        return {}

    scene_hint_count = sum(1 for s in scenario_list for t in s.tasks if t.scene_hint and t.scene_hint.strip())
    reactive_count = sum(1 for s in scenario_list for t in s.tasks if t.reactive)
    advanced_count = sum(1 for s in scenario_list for t in s.tasks if t.difficulty == "advanced")
    vocab_count = sum(1 for s in scenario_list for t in s.tasks if "Learner used the word" in t.done_when or "Use the word" in t.goal)

    return {
        'total_scenarios': len(scenario_list),
        'total_tasks': total_tasks,
        'scene_hint_pct': (scene_hint_count / total_tasks) * 100,
        'reactive_pct': (reactive_count / total_tasks) * 100,
        'advanced_pct': (advanced_count / total_tasks) * 100,
        'vocab_pct': (vocab_count / total_tasks) * 100
    }

def check_parity(range_arg="71-80"):
    # Flagship reference: Scenarios 1-6 & 70
    flagship_scenarios = [SCENARIOS[i] for i in [0, 1, 2, 3, 4, 5, 69]]
    flagship_metrics = calculate_metrics(flagship_scenarios)

    # Parse target range
    if '-' in range_arg:
        start_str, end_str = range_arg.split('-')
        target_indices = list(range(int(start_str) - 1, int(end_str)))
    elif range_arg.isdigit():
        target_indices = [int(range_arg) - 1]
    else:
        target_indices = list(range(len(SCENARIOS)))

    target_scenarios = [SCENARIOS[i] for i in target_indices if i < len(SCENARIOS)]
    target_metrics = calculate_metrics(target_scenarios)

    print("=" * 80)
    print(f"STRUCTURAL PARITY CHECK — Target Range [{range_arg}] vs Flagship Reference (Scenarios 1-6 & 70)")
    print("=" * 80)
    print(f"{'Metric':<25} | {'Flagship Baseline':<20} | {'Target Range (' + range_arg + ')':<20}")
    print("-" * 80)
    print(f"{'scene_hint usage %':<25} | {flagship_metrics['scene_hint_pct']:<19.1f}% | {target_metrics['scene_hint_pct']:<19.1f}%")
    print(f"{'reactive tasks %':<25} | {flagship_metrics['reactive_pct']:<19.1f}% | {target_metrics['reactive_pct']:<19.1f}%")
    print(f"{'advanced difficulty %':<25} | {flagship_metrics['advanced_pct']:<19.1f}% | {target_metrics['advanced_pct']:<19.1f}%")
    vocab_label = "'Use the word X' tasks %"
    print(f"{vocab_label:<25} | {flagship_metrics['vocab_pct']:<19.1f}% | {target_metrics['vocab_pct']:<19.1f}%")
    print("=" * 80)

    # Validation checks
    warnings = []
    if target_metrics['scene_hint_pct'] < 5.0:
        warnings.append(f"CRITICAL: scene_hint usage ({target_metrics['scene_hint_pct']:.1f}%) is below 5.0% baseline threshold!")
    if target_metrics['vocab_pct'] > 10.0:
        warnings.append(f"WARNING: 'Use the word X' tasks ({target_metrics['vocab_pct']:.1f}%) exceed 10.0% max threshold (7x over flagship baseline)!")
    if target_metrics['reactive_pct'] < 15.0:
        warnings.append(f"WARNING: reactive tasks ({target_metrics['reactive_pct']:.1f}%) are below 15.0% minimum threshold!")

    if warnings:
        print("\n⚠️ PARITY DRIFT DETECTED:")
        for w in warnings:
            print(f"  - {w}")
        return False
    else:
        print("\n✅ STRUCTURAL PARITY VERIFIED — Target batch matches flagship scenario quality standards!")
        return True

if __name__ == '__main__':
    range_param = sys.argv[1] if len(sys.argv) > 1 else "71-80"
    ok = check_parity(range_param)
    sys.exit(0 if ok else 1)
