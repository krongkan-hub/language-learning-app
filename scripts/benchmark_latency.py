import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coach import call_coach
from app.judge import evaluate_task

def run_sequential_turn(user_input, goal, language):
    t0 = time.time()
    conv = [{'role': 'user', 'content': user_input}]
    coach_feedback = call_coach(user_input, language)
    is_done, hint = evaluate_task(user_input, goal, conv, language)
    elapsed = time.time() - t0
    return coach_feedback, is_done, hint, elapsed

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
    print("EMPIRICAL LATENCY BENCHMARK: ThreadPoolExecutor vs Sequential Execution")
    print("=" * 80)

    test_turns = [
        ("I would like to ordering a hot black coffee, please.", "Learner ordered a black coffee.", "English"),
        ("Could I get some water and ask where the restroom is?", "Learner asked for restroom location.", "English"),
        ("Is it prohibit to smoke here?", "Learner asked about smoking policy.", "English")
    ]

    total_seq_time = 0
    total_conc_time = 0

    for i, (user_input, goal, lang) in enumerate(test_turns):
        print(f"\n--- Turn {i+1}: '{user_input}' ---")
        
        # Concurrent run
        _, _, _, conc_elapsed = run_concurrent_turn(user_input, goal, lang)
        total_conc_time += conc_elapsed
        print(f"  Concurrent (ThreadPoolExecutor + Lock): {conc_elapsed:.2f}s")
        
        # Sequential run
        _, _, _, seq_elapsed = run_sequential_turn(user_input, goal, lang)
        total_seq_time += seq_elapsed
        print(f"  Sequential (Plain Direct Calls):        {seq_elapsed:.2f}s")

    print("\n" + "=" * 80)
    print("SUMMARY RESULTS:")
    print(f"Total Concurrent Time: {total_conc_time:.2f}s")
    print(f"Total Sequential Time: {total_seq_time:.2f}s")
    diff = total_conc_time - total_seq_time
    print(f"Difference: {diff:+.2f}s")
    if diff > 0:
        print("Verdict: Concurrent execution adds overhead with zero net latency gain.")
    else:
        print("Verdict: Concurrent execution shows speedup.")
    print("=" * 80)

if __name__ == "__main__":
    main()
