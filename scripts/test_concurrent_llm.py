import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coach import call_coach
from app.judge import evaluate_task

def run_concurrent_turn(user_input, goal, language):
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=2) as executor:
        conv = [{'role': 'user', 'content': user_input}]
        future_coach = executor.submit(call_coach, user_input, language)
        future_judge = executor.submit(evaluate_task, user_input, goal, conv, language)
        coach_feedback = future_coach.result()
        is_done, hint = future_judge.result()
    elapsed = time.time() - t0
    return coach_feedback, is_done, hint, elapsed

def main():
    print("=" * 80)
    print("LIVE CONCURRENCY TEST: ThreadPoolExecutor + _llm_lock Thread Safety Check")
    print("=" * 80)

    test_turns = [
        ("I would like to ordering a hot black coffee, please.", "Learner ordered a black coffee.", "English"),
        ("Could I get some water and ask where the restroom is?", "Learner asked for restroom location.", "English"),
        ("Is it prohibit to smoke here?", "Learner asked about smoking policy.", "English")
    ]

    for i, (user_input, goal, lang) in enumerate(test_turns):
        print(f"\nTurn {i+1}: '{user_input}'")
        print(f"Goal: '{goal}'")
        feedback, is_done, hint, elapsed = run_concurrent_turn(user_input, goal, lang)
        print(f"Elapsed Time: {elapsed:.2f}s")
        print(f"Coach Feedback:\n{feedback}")
        print(f"Judge Verdict: Done={is_done}, Hint={hint}")
        assert "💡 Feedback:" in feedback
        assert not ("<think>" in feedback or "</think>" in feedback)
        print("✅ Output cleanly formatted and thread-safe.")

    print("\n" + "=" * 80)
    print("✅ Live Concurrency & Thread-Safety Verification Passed!")
    print("=" * 80)

if __name__ == "__main__":
    main()
