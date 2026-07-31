import os
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scenarios.builtins import SCENARIOS
from app.llm import call_actor, GREETING_SYS, ACTOR_SYS, build_task_setup_block
from app.coach import call_coach
from app.judge import evaluate_task
from app.cli import extract_and_format_vocab

def main():
    s70 = [s for s in SCENARIOS if s.name == "Apartment Neighbor Conversation"][0]
    print(f"Playtesting Scenario: {s70.name}")
    print(f"Place: {s70.place} | Role: {s70.role}")
    print("=" * 80)

    language = "English"
    mood = "chatty and friendly, happy to chat while you work"
    messages = []
    
    # 1. Greet
    greeting_sys = GREETING_SYS.format(
        place=s70.place,
        role=s70.role,
        language=language,
        mood=mood,
        complication="",
        task_setup=build_task_setup_block(s70.tasks[0])
    )
    raw_greeting = call_actor([{'role': 'user', 'content': 'Hello!'}], greeting_sys, speaker=s70.speaker, max_sentences=4)
    clean_greeting, vocab = extract_and_format_vocab(raw_greeting)
    messages.append({'role': 'assistant', 'content': clean_greeting})
    print(f"\n[{s70.speaker}]: {clean_greeting}")
    if vocab:
        print(vocab)

    # Simulate turns for first 4 tasks
    sample_turns = [
        "Hi Alex, I'm your new neighbor from 4B, just moved in yesterday!",
        "By the way, did you notice the elevator maintenance finally finished today?",
        "Have you by any chance seen my package? I think it was left in the hallway.",
        "It's nice meeting you here in the hallway."
    ]

    for idx, user_msg in enumerate(sample_turns):
        task = s70.tasks[idx]
        print(f"\n--- Task {idx + 1}: {task.goal} ---")
        print(f"Learner: {user_msg}")
        messages.append({'role': 'user', 'content': user_msg})

        # Coach & Judge
        feedback = call_coach(user_msg, language)
        is_done, hint = evaluate_task(user_msg, task.done_when, messages, language)
        print(f"Coach Feedback: {feedback}")
        print(f"Judge Verdict: Done={is_done}, Hint={hint}")

        # Actor response
        next_task = s70.tasks[idx + 1] if idx + 1 < len(s70.tasks) else task
        actor_sys = ACTOR_SYS.format(
            place=s70.place,
            role=s70.role,
            language=language,
            mood=mood,
            complication="",
            task_setup=build_task_setup_block(next_task)
        )
        raw_reply = call_actor(messages, actor_sys, speaker=s70.speaker)
        clean_reply, actor_vocab = extract_and_format_vocab(raw_reply)
        messages.append({'role': 'assistant', 'content': clean_reply})
        print(f"[{s70.speaker}]: {clean_reply}")
        if actor_vocab:
            print(actor_vocab)

    print("\n" + "=" * 80)
    print("✅ Scenario 70 Live Playtest Completed Successfully!")

if __name__ == "__main__":
    main()
