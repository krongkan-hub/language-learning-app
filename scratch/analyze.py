import sys
sys.path.insert(0, '.')
from app.scenarios.builtins import SCENARIOS

def inspect_failures():
    # 1. TRIVIAL VOCABULARY targets:
    trivial_items = [
        (23, 5), (30, 5), (69, 3), (70, 3), (73, 3), (73, 11), (76, 3), (76, 27), (77, 26)
    ]
    print("=== 2. TRIVIAL VOCABULARY ===")
    for si, ti in trivial_items:
        s = SCENARIOS[si]
        t = s.tasks[ti]
        print(f"Sc{si+1} ('{s.name}'), task {ti}:")
        print(f"  goal: {t.goal}")
        print(f"  hint: {t.hint}")
        print(f"  done_when: {t.done_when}")
        print(f"  phase: {t.phase}, reactive: {t.reactive}, difficulty: {t.difficulty}")

    # 2. GOAL / DONE_WHEN DISAGREEMENT:
    disagree_items = [
        (69, 42), (71, 34), (73, 52), (73, 56), (79, 67)
    ]
    print("\n=== 3. GOAL / DONE_WHEN DISAGREEMENT ===")
    for si, ti in disagree_items:
        s = SCENARIOS[si]
        t = s.tasks[ti]
        print(f"Sc{si+1} ('{s.name}'), task {ti}:")
        print(f"  goal: {t.goal}")
        print(f"  hint: {t.hint}")
        print(f"  done_when: {t.done_when}")
        print(f"  phase: {t.phase}, reactive: {t.reactive}, difficulty: {t.difficulty}")

    # 3. NEAR-DUPLICATE GOALS: 15 pairs
    near_dupe_pairs = [
        (4, 14, 65),
        (8, 2, 15),
        (13, 8, 20),
        (14, 6, 18),
        (15, 1, 15),
        (15, 2, 17),
        (23, 10, 65),
        (33, 4, 19),
        (34, 1, 15),
        (34, 6, 20),
        (34, 7, 21),
        (34, 9, 24),
        (35, 2, 16),
        (35, 3, 18),
        (35, 12, 63),
    ]
    print("\n=== 1. NEAR-DUPLICATE GOALS ===")
    for si, ti1, ti2 in near_dupe_pairs:
        s = SCENARIOS[si]
        t1, t2 = s.tasks[ti1], s.tasks[ti2]
        print(f"Sc{si+1} ('{s.name}'):")
        print(f"  Task {ti1}: goal='{t1.goal}', hint='{t1.hint}', done_when='{t1.done_when}'")
        print(f"          phase={t1.phase}, reactive={t1.reactive}, difficulty={t1.difficulty}")
        print(f"  Task {ti2}: goal='{t2.goal}', hint='{t2.hint}', done_when='{t2.done_when}'")
        print(f"          phase={t2.phase}, reactive={t2.reactive}, difficulty={t2.difficulty}")

if __name__ == '__main__':
    inspect_failures()
