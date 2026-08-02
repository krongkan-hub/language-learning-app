import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scenarios.builtins import SCENARIOS

# Substrings that have shipped as placeholder content in generated batches.
# These are shapes of failure, not topics — none should ever appear in real
# authored content, so a plain substring match is a reliable signal.
FORBIDDEN_PHRASES = [
    "Include '",                             # lazy vocab hint template
    "Sensory details of the environment",    # placeholder scene_hint
    "Ambient detail of setting",             # placeholder scene_hint
    "in your sentence",                      # lazy hint phrasing
]

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

def check_task_depth(range_arg="1-80", expect_total=None):
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

    # ── Semantic-integrity checks ────────────────────────────────────────────
    # The band checks above count features; these check that the feature has
    # content. Generated batches have shipped placeholder text that satisfied
    # every count — 149 identical scene_hints reading "Sensory details of the
    # environment surround the customer", and 46 hints reading "Include 'X' in
    # your sentence". Banning the shape of the failure catches that for free.
    print()
    integrity_failed = False

    # (a) forbidden boilerplate phrasing anywhere in the range
    hits = {phrase: [] for phrase in FORBIDDEN_PHRASES}
    for sc_num, scenario in target_scenarios:
        for t in scenario.tasks:
            blob = f"{t.goal}\n{t.hint}\n{t.done_when}\n{t.scene_hint}"
            for phrase in FORBIDDEN_PHRASES:
                if phrase.lower() in blob.lower():
                    hits[phrase].append(sc_num)
    for phrase, where in hits.items():
        if where:
            integrity_failed = True
            print(f"❌ BOILERPLATE: {len(where)} task(s) contain {phrase!r} "
                  f"(scenarios {sorted(set(where))[:8]})")

    # (b) scene_hint must be distinct — a repeated hint is filler by definition
    hint_locs = {}
    for sc_num, scenario in target_scenarios:
        for t in scenario.tasks:
            if t.scene_hint.strip():
                hint_locs.setdefault(t.scene_hint, []).append(sc_num)
    repeated = {h: w for h, w in hint_locs.items() if len(w) > 1}
    if repeated:
        integrity_failed = True
        print(f"❌ DUPLICATE scene_hint: {len(repeated)} string(s) reused")
        for h, w in list(repeated.items())[:5]:
            print(f"     x{len(w)} in {sorted(set(w))}: {h[:66]}")

    # (c) vocab hints must define the term, not merely name it
    lazy = []
    for sc_num, scenario in target_scenarios:
        for t in scenario.tasks:
            if "Use the word" in t.goal and len(t.hint.split()) < 8:
                lazy.append((sc_num, t.goal))
    if lazy:
        integrity_failed = True
        print(f"❌ THIN vocab hint (<8 words, likely not definitional): {len(lazy)}")
        for sc_num, g in lazy[:5]:
            print(f"     Sc{sc_num}: {g}")

    if not integrity_failed:
        print("✅ Semantic integrity: no boilerplate phrasing, all scene_hints "
              "distinct, all vocab hints definitional.")

    # ── Expected catalog total ───────────────────────────────────────────────
    # Cheap conservation law. A silently double-applied batch grew one scenario
    # from 69 tasks to 175 while every band check still passed; only the total
    # failing to reconcile exposed it.
    total_failed = False
    if expect_total is not None:
        actual = sum(len(s.tasks) for s in SCENARIOS)
        if actual != expect_total:
            total_failed = True
            print(f"\n❌ CATALOG TOTAL: expected {expect_total}, found {actual} "
                  f"(difference {actual - expect_total:+d})")
        else:
            print(f"\n✅ Catalog total reconciles exactly: {actual} tasks.")

    ok = all_passed and not integrity_failed and not total_failed
    if ok:
        print("\n✅ TASK DEPTH VERIFIED — All target scenarios meet required depth, band, and quality standards!")
        return True
    else:
        print("\n❌ TASK DEPTH FAILED — One or more checks failed.")
        return False

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = [a for a in sys.argv[1:] if a.startswith('--')]
    range_param = args[0] if args else "1-80"
    expect = None
    for f in flags:
        if f.startswith('--expect-total='):
            expect = int(f.split('=', 1)[1])
    ok = check_task_depth(range_param, expect_total=expect)
    sys.exit(0 if ok else 1)
