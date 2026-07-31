import sys
import os
import re

# Add parent dir to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.judge import evaluate_task
from app.llm import call_actor, GREETING_SYS, ACTOR_SYS, build_task_setup_block, _llm_chat

LEARNER_SYS = """\
You are a language learner role-playing as a customer/guest in a scenario.
SCENARIO PLACE: {place}
YOUR GOAL: {goal}

You must speak in English to the NPC to achieve your goal.
Keep your responses short, natural, and conversational (1-2 sentences).
Do not break character. Do not include asterisks or actions, just say the words you would speak.
"""

def clean_msg(msg: str) -> str:
    msg = msg.strip().replace('"', '')
    msg = re.sub(r'\*.*?\*', '', msg).strip()
    return msg

def playtest_task(scenario, task, max_attempts=3):
    """
    Simulates a conversation where an AI Learner tries to achieve the task.
    Returns (True, history) if the task is achieved within max_attempts, else (False, history).
    """
    mood = "neutral"
    
    # 1. Get NPC Greeting
    greeting_system = GREETING_SYS.format(
        place=scenario.place, 
        role=scenario.role, 
        language='English', 
        mood=mood, 
        complication='', 
        task_setup=build_task_setup_block(task)
    )
    
    seed = [{'role': 'user', 'content': 'Hello.'}]
    try:
        greeting = call_actor(seed, greeting_system, speaker=scenario.speaker, max_sentences=2)
    except Exception as e:
        return False, [f"Error generating greeting: {e}"]
        
    conversation = [{'role': 'assistant', 'content': greeting}]
    learner_sys = LEARNER_SYS.format(place=scenario.place, goal=task.goal)
    
    for attempt in range(max_attempts):
        # 2. Learner speaks
        try:
            response = _llm_chat(
                messages=[{'role': 'system', 'content': learner_sys}] + conversation,
                options={'temperature': 0.6, 'max_tokens': 150}
            )
            raw_learner_msg = response['message']['content']
            raw_learner_msg = re.sub(r'<think>.*?</think>', '', raw_learner_msg, flags=re.DOTALL)
            learner_msg = clean_msg(raw_learner_msg)
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
                task_setup=build_task_setup_block(task)
            )
            try:
                npc_msg = call_actor(conversation, actor_sys, speaker=scenario.speaker, max_sentences=2)
                conversation.append({'role': 'assistant', 'content': npc_msg})
            except Exception:
                break
                
    return False, conversation

if __name__ == '__main__':
    from app.scenarios.builtins import SCENARIOS
    scen = SCENARIOS[0]
    task = scen.tasks[0]
    print(f"Testing Task: {task.goal}")
    success, hist = playtest_task(scen, task)
    print(f"Success: {success}")
    for h in hist:
        print(f"{h['role'].upper()}: {h['content']}")
