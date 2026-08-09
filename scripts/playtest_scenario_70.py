import os
import sys
import re

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scenarios.builtins import SCENARIOS
from app.llm import call_actor, GREETING_SYS, ACTOR_SYS, build_task_setup_block, _llm_chat
from app.coach import call_coach
from app.judge import evaluate_task
from app.cli import extract_and_format_vocab

LEARNER_SYS = """\
You are a language learner role-playing as a resident in an apartment building talking to your neighbor.
SETTING: {place}
YOUR CURRENT GOAL: {goal}
SPECIFICALLY: {done_when}

Speak in natural, conversational {language} (1-2 sentences).
Your sole objective is to satisfy your CURRENT GOAL in your spoken words.
Do not break character. No stage directions, no asterisks, no quotes.
"""

def playtest_all_22_tasks():
    s70 = [s for s in SCENARIOS if s.name == "Apartment Neighbor Conversation"][0]
    print("================================================================================")
    print(f"FULL ADVERSARIAL PLAYTEST: {s70.name} (All {len(s70.tasks)} Tasks)")
    print(f"Place: {s70.place}")
    print(f"Role: {s70.role}")
    print("================================================================================")

    language = "English"
    mood = "chatty and friendly, happy to chat while you work"
    messages = []
    task_results = []

    # Initial Greeting
    greeting_sys = GREETING_SYS.format(
        place=s70.place,
        role=s70.role,
        language=language,
        mood=mood,
        complication="",
        task_setup=build_task_setup_block(s70.tasks[0])
    )
    raw_greeting = call_actor([{'role': 'user', 'content': 'Hello.'}], greeting_sys, speaker=s70.speaker, max_sentences=4)
    clean_greeting, vocab = extract_and_format_vocab(raw_greeting)
    messages.append({'role': 'assistant', 'content': clean_greeting})
    print(f"\n[{s70.speaker}]: {clean_greeting}")

    # Playtest all 22 tasks sequentially
    for idx, task in enumerate(s70.tasks):
        print("\n" + "-"*80)
        print(f"--- Task {idx + 1}/{len(s70.tasks)}: {task.goal} ---")
        print(f"Target Criterion: {task.done_when}")
        
        task_passed = False
        task_attempts = 0
        max_task_attempts = 3
        
        learner_prompt = LEARNER_SYS.format(place=s70.place, goal=task.goal, done_when=task.done_when, language=language)

        while task_attempts < max_task_attempts and not task_passed:
            task_attempts += 1
            # 1. LLM Learner turn
            learner_res = _llm_chat(
                messages=[{'role': 'system', 'content': learner_prompt}] + messages[-6:],
                options={'temperature': 0.7, 'max_tokens': 120}
            )
            raw_learner_msg = learner_res['message']['content']
            raw_learner_msg = re.sub(r'<think>.*?</think>', '', raw_learner_msg, flags=re.DOTALL)
            learner_msg = re.sub(r'\*.*?\*', '', raw_learner_msg).strip().strip('"')

            print(f"Learner (Attempt {task_attempts}): {learner_msg}")
            messages.append({'role': 'user', 'content': learner_msg})

            # 2. Coach & Judge
            coach_feedback = call_coach(learner_msg, language)
            is_done, hint = evaluate_task(learner_msg, task.done_when, messages, language)
            print(f"Coach: {coach_feedback}")
            print(f"Judge: Done={is_done} | Hint={hint}")

            if is_done:
                task_passed = True
                print(f"✅ TASK {idx + 1} PASSED in {task_attempts} turn(s)")
            
            # 3. Actor turn
            next_task = s70.tasks[idx + 1] if idx + 1 < len(s70.tasks) else task
            actor_sys = ACTOR_SYS.format(
                place=s70.place,
                role=s70.role,
                language=language,
                mood=mood,
                complication="",
                task_setup=build_task_setup_block(next_task)
            )
            raw_actor_reply = call_actor(messages, actor_sys, speaker=s70.speaker)
            clean_actor_reply, actor_vocab = extract_and_format_vocab(raw_actor_reply)
            messages.append({'role': 'assistant', 'content': clean_actor_reply})
            print(f"[{s70.speaker}]: {clean_actor_reply}")

        task_results.append({
            'task_num': idx + 1,
            'goal': task.goal,
            'passed': task_passed,
            'attempts': task_attempts
        })

    print("\n" + "="*80)
    print("       🏁 SCENARIO 70 FULL PLAYTEST RESULTS SUMMARY")
    print("="*80)
    passed_count = sum(1 for r in task_results if r['passed'])
    for r in task_results:
        status_str = "✅ PASS" if r['passed'] else "❌ FAIL"
        print(f"Task {r['task_num']:02d}: {status_str} (Turns: {r['attempts']}) | Goal: {r['goal']}")
    print(f"\nFinal Scenario 70 Coverage Score: {(passed_count / len(s70.tasks)) * 100:.1f}% ({passed_count}/{len(s70.tasks)} tasks passed)")
    print("="*80)

if __name__ == "__main__":
    playtest_all_22_tasks()
