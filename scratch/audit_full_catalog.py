import sys
import re
from collections import defaultdict
from app.scenarios.builtins import SCENARIOS

def dump_vocabulary_words():
    print("==================================================")
    print("1. VOCABULARY WORDS ANALYSIS Across Catalog")
    print("==================================================")
    
    vocab_by_scenario = defaultdict(list)
    word_pattern = re.compile(r"Use the word ['\"]([^'\"]+)['\"]", re.IGNORECASE)
    
    total_vocab_tasks = 0
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            m = word_pattern.search(t.goal)
            if m:
                word = m.group(1)
                vocab_by_scenario[s.name].append((t_idx, word, t.goal, t.hint))
                total_vocab_tasks += 1
            elif "Use the word" in t.goal:
                vocab_by_scenario[s.name].append((t_idx, "UNKNOWN", t.goal, t.hint))
                total_vocab_tasks += 1

    print(f"Total 'Use the word' tasks found: {total_vocab_tasks}")
    for s_name, v_list in vocab_by_scenario.items():
        words = [w[1] for w in v_list]
        print(f"[{s_name}] ({len(words)} words): {', '.join(words)}")

def dump_scene_hints():
    print("\n==================================================")
    print("2. SCENE HINTS ANALYSIS Across Catalog")
    print("==================================================")
    
    scene_hints_by_scenario = defaultdict(list)
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            sh = t.scene_hint.strip()
            if sh:
                scene_hints_by_scenario[s.name].append((t_idx, sh))

    print(f"Scenarios with non-empty scene_hints: {len(scene_hints_by_scenario)} / {len(SCENARIOS)}")
    for s_name, sh_list in scene_hints_by_scenario.items():
        print(f"\n--- {s_name} ({len(sh_list)} scene_hints) ---")
        for t_idx, sh in sh_list[:10]: # print sample
            print(f"  T{t_idx}: {sh}")

def dump_hints_issues():
    print("\n==================================================")
    print("3. HINTS QUALITY ANALYSIS")
    print("==================================================")
    
    include_hints = []
    giveaway_hints = []
    goal_repetition_hints = []
    
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            g = t.goal.strip()
            h = t.hint.strip()
            
            # Check 'Include X in your sentence' pattern
            if re.search(r"include ['\"].*['\"] in your sentence", h, re.IGNORECASE) or re.search(r"include .* in your sentence", h, re.IGNORECASE):
                include_hints.append((s.name, t_idx, g, h))
                
            # Check giveaways (e.g. Hint tells exact quote: Say "..." or "Ask: ...")
            if re.search(r"Say ['\"].*['\"]", h) or re.search(r"Ask ['\"].*['\"]", h):
                giveaway_hints.append((s.name, t_idx, g, h))

    print(f"Hints forcing 'Include X in your sentence': {len(include_hints)}")
    for item in include_hints:
        print(f"  [{item[0]}] T{item[1]}: Goal='{item[2]}' | Hint='{item[3]}'")

    print(f"\nHints with quote giveaways (Say/Ask '...'): {len(giveaway_hints)}")
    for item in giveaway_hints[:15]:
        print(f"  [{item[0]}] T{item[1]}: Goal='{item[2]}' | Hint='{item[3]}'")

def dump_goal_donewhen_mismatches():
    print("\n==================================================")
    print("4. GOAL VS DONE_WHEN MISMATCH ANALYSIS")
    print("==================================================")
    
    mismatches = []
    for s_idx, s in enumerate(SCENARIOS):
        for t_idx, t in enumerate(s.tasks):
            g = t.goal.strip()
            d = t.done_when.strip()
            
            # Check key noun discrepancies
            g_words = set(re.findall(r'\b[a-z]{4,}\b', g.lower()))
            d_words = set(re.findall(r'\b[a-z]{4,}\b', d.lower()))
            
            # Filter out common verbs/filler
            common = {'learner', 'asked', 'inquired', 'stated', 'requested', 'about', 'whether', 'would', 'could', 'their', 'with', 'have', 'from', 'this', 'that', 'your', 'please'}
            g_words -= common
            d_words -= common
            
            overlap = g_words.intersection(d_words)
            if len(g_words) > 0 and len(overlap) == 0:
                mismatches.append((s.name, t_idx, g, d))

    print(f"Potential Goal/DoneWhen mismatches (low keyword overlap): {len(mismatches)}")
    for item in mismatches[:20]:
        print(f"  [{item[0]}] T{item[1]}:\n    Goal:      {item[2]}\n    DoneWhen:  {item[3]}")

if __name__ == "__main__":
    dump_vocabulary_words()
    dump_scene_hints()
    dump_hints_issues()
    dump_goal_donewhen_mismatches()
