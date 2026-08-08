import sys
import os
import random

sys.path.insert(0, '/Users/pk/language-learning-app')
import app.llm as llm
from app.scenarios.builtins import SCENARIOS

random.seed(int(os.environ.get("MSEED", "11")))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20

total_llm_calls = 0
orig_llm_chat = llm._llm_chat

def count_llm_chat(*args, **kwargs):
    global total_llm_calls
    total_llm_calls += 1
    return orig_llm_chat(*args, **kwargs)

llm._llm_chat = count_llm_chat

invalid_returned_outputs = 0
reasons = {}

print(f"Running measure_repair.py with N={N}...")
for i in range(N):
    sc = random.choice(SCENARIOS)
    task = random.choice(sc.tasks)
    sysmsg = llm.ACTOR_SYS.format(
        place=sc.place, role=sc.role, language='English', mood='neutral',
        complication='', task_setup=llm.build_task_setup_block(task)
    )
    conv = [
        {'role': 'assistant', 'content': 'Hello, how can I help you today?'},
        {'role': 'user', 'content': 'Hi, I have a few questions about what you offer here.'}
    ]
    
    result = llm.call_actor(messages=conv, system_prompt=sysmsg, speaker=sc.role, max_sentences=3)
    ok, reason = llm.validate(result, max_sentences=3)
    if not ok:
        invalid_returned_outputs += 1
        reasons[reason] = reasons.get(reason, 0) + 1
    print(f"[{i+1}/{N}] ok: {ok}{f' (failed: {reason})' if not ok else ''}")

avg_llm_calls = total_llm_calls / N
print("\n--- RESULTS ---")
print(f"call_actor invocations : {N}")
print(f"invalid returned outputs: {invalid_returned_outputs} ({invalid_returned_outputs/N*100:.1f}%)")
for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
    print(f"   {v:>2}x {k}")
print(f"total LLM calls        : {total_llm_calls}")
print(f"avg LLM calls/invocation: {avg_llm_calls:.2f}")
