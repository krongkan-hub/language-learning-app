import sys
import os
import re

# Add parent dir to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.judge import evaluate_task
from app.llm import call_actor, GREETING_SYS, ACTOR_SYS, build_task_setup_block, _llm_chat
from app.cli import extract_and_format_vocab

LEARNER_SYS = """\
You are a language learner role-playing as a customer/guest in a scenario.
SCENARIO PLACE: {place}
YOUR GOAL: {goal}
SPECIFICALLY: {done_when}

Speak in natural, conversational English (1-2 sentences) to achieve your goal.
Do not break character. Do not include stage directions, asterisks, or quotes.
CRITICAL INSTRUCTION: Respond directly to the NPC. DO NOT repeat or echo the NPC's previous question or sentence back to them.
"""

def clean_msg(msg: str, previous_npc_msg: str = "") -> str:
    msg = msg.strip().replace('"', '')
    msg = re.sub(r'\*.*?\*', '', msg).strip()
    
    # Anti-echo / repetition fix: If learner repeats NPC question prefix, remove it
    if previous_npc_msg:
        # Check if learner starts with exact NPC question phrase
        npc_sentences = [s.strip() for s in re.split(r'[.!?]', previous_npc_msg) if s.strip()]
        for sentence in npc_sentences:
            if len(sentence) > 15 and sentence in msg:
                msg = msg.replace(sentence, '').strip()
    return msg

def playtest_task(scenario, task, max_attempts=3):
    """
    Simulates a conversation where an AI Learner tries to achieve the task.
    Returns (True, history) if the task is achieved within max_attempts, else (False, history).
    """
    mood = "neutral"
    
    # 1. Get NPC Greeting
    task_setup = build_task_setup_block(task)
    if task.phase == 3:
        task_setup += " (Note: The conversation is concluding or wrapping up.)"

    greeting_system = GREETING_SYS.format(
        place=scenario.place, 
        role=scenario.role, 
        language='English', 
        mood=mood, 
        complication='', 
        task_setup=task_setup
    )
    
    seed = [{'role': 'user', 'content': 'Hello.'}]
    try:
        raw_greeting = call_actor(seed, greeting_system, speaker=scenario.speaker, max_sentences=2)
        clean_greeting, _ = extract_and_format_vocab(raw_greeting)
    except Exception as e:
        return False, [f"Error generating greeting: {e}"]
        
    conversation = [{'role': 'assistant', 'content': clean_greeting}]
    learner_sys = LEARNER_SYS.format(place=scenario.place, goal=task.goal, done_when=task.done_when)
    
    for attempt in range(max_attempts):
        # 2. Learner speaks
        try:
            response = _llm_chat(
                messages=[{'role': 'system', 'content': learner_sys}] + conversation,
                options={'temperature': 0.5, 'max_tokens': 150}
            )
            raw_learner_msg = response['message']['content']
            raw_learner_msg = re.sub(r'<think>.*?</think>', '', raw_learner_msg, flags=re.DOTALL)
            last_npc_text = conversation[-1]['content'] if conversation else ""
            learner_msg = clean_msg(raw_learner_msg, last_npc_text)
            if not learner_msg:
                learner_msg = f"I would like to speak about {task.goal}."
        except Exception as e:
            return False, conversation + [{'role': 'user', 'content': f"[Error: {e}]"}]
            
        conversation.append({'role': 'user', 'content': learner_msg})
        
        # 3. Judge evaluates
        try:
            done, hint = evaluate_task(learner_msg, task.done_when, conversation, 'English')
            if done:
                return True, conversation
        except Exception as e:
            return False, conversation + [{'role': 'system', 'content': f"[Judge Error: {e}]"}]
            
        # 4. If not done and more attempts remain, NPC replies
        if attempt < max_attempts - 1:
            actor_sys = ACTOR_SYS.format(
                place=scenario.place, 
                role=scenario.role, 
                language='English', 
                mood=mood, 
                complication='', 
                task_setup=task_setup
            )
            try:
                raw_npc_msg = call_actor(conversation, actor_sys, speaker=scenario.speaker, max_sentences=2)
                clean_npc_msg, _ = extract_and_format_vocab(raw_npc_msg)
                conversation.append({'role': 'assistant', 'content': clean_npc_msg})
            except Exception:
                break
                
    return False, conversation

def run_playtest_suite(scenario_indices=None):
    from app.scenarios.builtins import SCENARIOS
    
    if scenario_indices is None:
        selected_scenarios = [(0, SCENARIOS[0])]
    else:
        selected_scenarios = [(i, SCENARIOS[i]) for i in scenario_indices if i < len(SCENARIOS)]

    total_tasks = 0
    passed_tasks = 0

    print("=" * 80, flush=True)
    print(f"AUTOMATED PLAYTEST SUITE — {len(selected_scenarios)} Scenario(s)", flush=True)
    print("=" * 80, flush=True)

    for s_idx, scen in selected_scenarios:
        print(f"\n--- Playtesting Scenario {s_idx + 1}: {scen.name} ({len(scen.tasks)} tasks) ---", flush=True)
        scen_passed = 0
        for t_idx, task in enumerate(scen.tasks):
            total_tasks += 1
            success, hist = playtest_task(scen, task, max_attempts=3)
            status_str = "✅ PASS" if success else "❌ FAIL"
            if success:
                scen_passed += 1
                passed_tasks += 1
            print(f"  Task {t_idx+1:02d} [{status_str}]: Goal='{task.goal}'", flush=True)
        print(f"Scenario {s_idx + 1} Result: {scen_passed}/{len(scen.tasks)} tasks passed ({(scen_passed/len(scen.tasks))*100:.1f}%)", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(f"PLAYTEST SUITE SUMMARY: {passed_tasks}/{total_tasks} tasks passed ({(passed_tasks/total_tasks)*100:.1f}%)", flush=True)
    print("=" * 80, flush=True)
    return passed_tasks == total_tasks

if __name__ == '__main__':
    from app.scenarios.builtins import SCENARIOS
    
    # Parse CLI argument for scenario range, e.g. "71-80" or "1-5" or "all"
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if '-' in arg:
            start_str, end_str = arg.split('-')
            indices = list(range(int(start_str) - 1, int(end_str)))
        elif arg.isdigit():
            indices = [int(arg) - 1]
        elif arg.lower() == 'all':
            indices = list(range(len(SCENARIOS)))
        else:
            indices = [0]
    else:
        indices = [0]
        
    run_playtest_suite(indices)
