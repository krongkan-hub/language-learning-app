import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scenarios.builtins import SCENARIOS

def parse_range(range_arg, max_scenarios):
    if not range_arg or range_arg == "all":
        return list(range(max_scenarios))
    if '-' in range_arg:
        start_str, end_str = range_arg.split('-')
        return list(range(int(start_str) - 1, int(end_str)))
    elif range_arg.isdigit():
        return [int(range_arg) - 1]
    else:
        return list(range(max_scenarios))

def check_task_depth(range_arg="1-80"):
    target_indices = parse_range(range_arg, len(SCENARIOS))
    target_scenarios = [(i + 1, SCENARIOS[i]) for i in target_indices if i < len(SCENARIOS)]

    print("=" * 110)
    print(f"TASK DEPTH CHECK — Target Range [{range_arg}]")
    print("=" * 110)
    headers = f"{'#':<4} | {'Scenario Name':<32} | {'Tasks':<6} | {'Hint':<8} | {'React':<7} | {'Adv':<7} | {'Vocab':<6} | {'P1':<5} | {'P3':<5} | {'Dups':<5} | {'Status':<6}"
    print(headers)
    print("-" * 110)

    all_passed = True
    catalog_goals = {}

    for sc_num, scenario in target_scenarios:
        tasks = scenario.tasks
        total = len(tasks)
        sh_count = sum(1 for t in tasks if t.scene_hint and t.scene_hint.strip())
        react_count = sum(1 for t in tasks if t.reactive)
        adv_count = sum(1 for t in tasks if t.difficulty == "advanced")
        vocab_count = sum(1 for t in tasks if "Learner used the word" in t.done_when or "Use the word" in t.goal)
        p1_count = sum(1 for t in tasks if t.phase == 1)
        p3_count = sum(1 for t in tasks if t.phase == 3)
        goals = [t.goal for t in tasks]
        intra_dups = len(goals) - len(set(goals))

        for g in goals:
            catalog_goals.setdefault(g, []).append(sc_num)

        c_total = (total == 69)
        c_sh = (10 <= sh_count <= 16)
        c_react = (14 <= react_count <= 18)
        c_adv = (19 <= adv_count <= 24) and (adv_count >= 7)
        c_vocab = (4 <= vocab_count <= 6)
        c_p1 = (p1_count >= 5)
        c_p3 = (p3_count >= 8)
        c_dups = (intra_dups == 0)

        sc_passed = c_total and c_sh and c_react and c_adv and c_vocab and c_p1 and c_p3 and c_dups
        if not sc_passed:
            all_passed = False

        status_str = "PASS" if sc_passed else "FAIL"
        
        # Truncate scenario name if too long
        sc_name_disp = (scenario.name[:29] + "...") if len(scenario.name) > 32 else scenario.name

        sh_str = f"{sh_count}" + ("" if c_sh else "!")
        react_str = f"{react_count}" + ("" if c_react else "!")
        adv_str = f"{adv_count}" + ("" if c_adv else "!")
        vocab_str = f"{vocab_count}" + ("" if c_vocab else "!")
        p1_str = f"{p1_count}" + ("" if c_p1 else "!")
        p3_str = f"{p3_count}" + ("" if c_p3 else "!")
        tot_str = f"{total}" + ("" if c_total else "!")
        dup_str = f"{intra_dups}" + ("" if c_dups else "!")

        print(f"{sc_num:<4} | {sc_name_disp:<32} | {tot_str:<6} | {sh_str:<8} | {react_str:<7} | {adv_str:<7} | {vocab_str:<6} | {p1_str:<5} | {p3_str:<5} | {dup_str:<5} | {status_str:<6}")

    print("=" * 110)

    # Check for catalog-wide duplicate goals in range
    catalog_dups = {g: scs for g, scs in catalog_goals.items() if len(scs) > 1}
    if catalog_dups:
        print("\n⚠️ CATALOG-WIDE WARNING: Duplicate task goals found across scenarios in range:")
        for goal_str, sc_list in list(catalog_dups.items())[:10]: # cap printout
            print(f"  - Goal '{goal_str}' appears in Scenarios: {sc_list}")
        if len(catalog_dups) > 10:
            print(f"  ... and {len(catalog_dups) - 10} more catalog duplicate goals.")

    if all_passed:
        print("\n✅ TASK DEPTH VERIFIED — All target scenarios meet required depth, band, and quality standards!")
        return True
    else:
        print("\n❌ TASK DEPTH FAILED — One or more target scenarios failed depth requirements.")
        return False

if __name__ == '__main__':
    range_param = sys.argv[1] if len(sys.argv) > 1 else "1-80"
    ok = check_task_depth(range_param)
    sys.exit(0 if ok else 1)
