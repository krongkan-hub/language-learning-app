import sys
import re
from collections import defaultdict, Counter
from app.scenarios.builtins import SCENARIOS

def run_checks():
    print("=== SCENE HINTS ANALYSIS ===")
    scene_hint_counts = Counter()
    empty_scene_hints = 0
    total_tasks = 0
    
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            total_tasks += 1
            sh = t.scene_hint.strip()
            if not sh:
                empty_scene_hints += 1
            else:
                scene_hint_counts[sh] += 1

    print(f"Total tasks: {total_tasks}")
    print(f"Empty scene hints count: {empty_scene_hints}")
    print(f"Unique non-empty scene hints: {len(scene_hint_counts)}")
    print("\nMost common non-empty scene hints:")
    for sh, count in scene_hint_counts.most_common(15):
        print(f"  [{count}x] {sh}")

    print("\n=== HINT TEMPLATE / 'INCLUDE' ANALYSIS ===")
    include_hints = []
    exact_repeat_hints = []
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            h = t.hint.strip()
            g = t.goal.strip()
            if "include" in h.lower():
                include_hints.append((s_idx, s.name, t_idx, g, h))
            if g.lower() == h.lower():
                exact_repeat_hints.append((s_idx, s.name, t_idx, g, h))
                
    print(f"Hints containing 'include': {len(include_hints)}")
    for item in include_hints[:10]:
        print(f"  S{item[0]} [{item[1]}] T{item[2]}: Goal='{item[3]}' | Hint='{item[4]}'")

    print(f"\nHints exactly repeating Goal: {len(exact_repeat_hints)}")
    for item in exact_repeat_hints[:10]:
        print(f"  S{item[0]} [{item[1]}] T{item[2]}: Goal='{item[3]}'")

    print("\n=== VOCABULARY SCAN ===")
    # Find tasks that look like vocabulary tasks or mention specific words/terms
    vocab_pattern = re.compile(r"\b(word|vocabulary|term|phrase|meaning|use the word|say the word)\b", re.IGNORECASE)
    vocab_tasks = []
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            if vocab_pattern.search(t.goal) or vocab_pattern.search(t.hint):
                vocab_tasks.append((s_idx, s.name, t_idx, t.goal, t.hint))
    print(f"Tasks mentioning vocab keywords: {len(vocab_tasks)}")
    for item in vocab_tasks[:15]:
        print(f"  S{item[0]} [{item[1]}] T{item[2]}: Goal='{item[3]}' | Hint='{item[4]}'")

if __name__ == "__main__":
    run_checks()
