from .llm import call_actor, translate_hints, describe_ollama_error, NPC_MOODS, OLLAMA_ERRORS, _client, BASE_MODEL, _llm_chat, GREETING_SYS, ACTOR_SYS, build_task_setup_block
from .coach import call_coach
from .judge import evaluate_task
from .scenarios.builtins import SCENARIOS
import ollama
import httpx
import random
import sys
import db

MAX_TASK_ATTEMPTS = 4

import threading
import sys
import time

class Spinner:
    def __init__(self, message="Thinking"):
        self.message = message
        self.running = False
        self.spinner = threading.Thread(target=self._spin)

    def _spin(self):
        chars = "|/-\\"
        idx = 0
        while self.running:
            sys.stdout.write(f"\r[{self.message}... {chars[idx % len(chars)]}] ")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)

    def start(self):
        self.running = True
        self.spinner.start()

    def stop(self):
        self.running = False
        self.spinner.join()
        sys.stdout.write("\r\033[K") # Clear the line
        sys.stdout.flush()


def select_builtin_scenario():
    """Pick from the hardcoded SCENARIOS list (original behaviour)."""
    valid_scenarios = [s for s in SCENARIOS if len(s.tasks) > 0]
    if not valid_scenarios:
        print('Error: No scenarios with tasks found!')
        sys.exit(1)
    random_scenario = random.choice(valid_scenarios)
    print(f'\nRandomly selected scenario: {random_scenario.name}')
    choice = input('Do you want to play this scenario? (y/n): ').strip().lower()
    if choice == 'y' or choice == '':
        return random_scenario
    print('\nAvailable Scenarios:')
    for (i, s) in enumerate(valid_scenarios):
        print(f'{i + 1}. {s.name} ({len(s.tasks)} tasks available)')
    while True:
        try:
            sel = input("\nEnter the number of the scenario you want (or 'quit'): ").strip()
            if sel.lower() in ('quit', 'exit'):
                print('Exiting...')
                sys.exit(0)
            idx = int(sel) - 1
            if 0 <= idx < len(valid_scenarios):
                return valid_scenarios[idx]
            else:
                print('Invalid number. Try again.')
        except ValueError:
            print('Please enter a valid number.')

def choose_scenario(language: str, conn, user_id: int):
    """Let the user pick a built-in scenario or generate one from a topic.

    Returns (scenario, scenario_id).  scenario_id is None for built-in
    scenarios (they aren't persisted unless we decide to later).
    """
    return (select_builtin_scenario(), None)

def main():
    print('========================================')
    print('   Language Conversation Coach CLI')
    print('========================================')
    try:
        _client.show(BASE_MODEL)
    except ollama.ResponseError as e:
        if e.status_code == 404:
            print(f"Error: Model '{BASE_MODEL}' not found.")
            print(f'Please run: ollama pull {BASE_MODEL}')
        else:
            print(f'Ollama error: {e}')
        sys.exit(1)
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        print(f'Error: {describe_ollama_error(e)}')
        sys.exit(1)
    language = input('Which language do you want to practice? (e.g., English, Japanese): ').strip()
    if not language:
        language = 'English'
    conn = db.init_db()
    user_id = db.get_or_create_user(conn, target_lang=language)
    (scenario, scenario_id) = choose_scenario(language, conn, user_id)
    tasks = scenario.get_session_tasks(num_tasks=10)
    speaker = scenario.speaker
    if scenario_id is None:
        builtin_dict = {'name': scenario.name, 'place': scenario.place, 'role': scenario.role, 'speaker': scenario.speaker, 'complications': scenario.complications, 'tasks': [{'goal': t.goal, 'hint': t.hint, 'done_when': t.done_when, 'difficulty': t.difficulty, 'scene_hint': t.scene_hint, 'phase': t.phase, 'reactive': t.reactive} for t in scenario.tasks]}
        scenario_id = db.save_scenario(conn, user_id, scenario.name, builtin_dict, source='static')
    print('[Preparing session...]')
    hint_translations = translate_hints(tasks, language)
    mood = random.choice(NPC_MOODS)
    complication = random.choice(scenario.complications) if scenario.complications else None
    session_id = db.create_session(conn, user_id, scenario_id, language, mood, complication, len(tasks))
    tasks_done = 0
    tasks_skipped = 0
    actor_complication_block = f"\nTODAY'S COMPLICATION (applies to this whole conversation, FIRM): {complication}. The FIRST time the learner asks for something this obstacle actually affects, you MUST raise it before agreeing and make them adapt or choose an alternative — do not quietly fulfil that request as if the obstacle weren't there. But this complication is to be ESTABLISHED ONCE and then re-mentioned ONLY when the learner's CURRENT message is actually about the affected item. Look at the conversation so far: if you (or your greeting) have already established it, do NOT state it again — not verbatim, not reworded, not even in passing — UNLESS the learner's latest message is directly about the thing it affects. If the learner just asked for something unrelated (napkins, the wifi password, a receipt, directions) while the complication is about, say, oat milk, then say NOTHING about the complication — just handle exactly what they asked. Above all, actually RESPOND to what the learner just said: acknowledge their specific point first (if they say they already have a booking, confirm you see it) and build on it, rather than ignoring it to repeat this complication. Beyond this and whatever the learner's current goal calls for, do not pile on extra unrelated obstacles." if complication else ''
    greeting_complication_block = f"""\nTODAY'S COMPLICATION (background for the whole conversation): {complication}. IMPORTANT: this is your FIRST line and the customer has NOT said anything yet. You must NOT claim they already asked for, wanted, or complained about any specific item, and you must NOT say a specific item is unavailable relative to a request they haven't made — no request exists yet, so phrases like "the X you were asking about" or "the X you wanted" are forbidden here. Let the complication colour only the ambiance or your manner (you might seem a little apologetic, harried, or frazzled). Save actually raising the obstacle for later, once the learner asks for something it affects.""" if complication else ''
    print(f'\nStarting Scenario: {scenario.name}')
    print(f'Place: {scenario.place}')
    print(f'Role of AI: {scenario.role}')
    print('========================================\n')
    greeting_system = GREETING_SYS.format(place=scenario.place, role=scenario.role, language=language, mood=mood, complication=greeting_complication_block, task_setup=build_task_setup_block(tasks[0]))
    spinner = Spinner(f'{speaker} is getting ready')
    spinner.start()
    try:
        seed = [{'role': 'user', 'content': 'Hello.'}]
        greeting = call_actor(seed, greeting_system, speaker=speaker, max_sentences=4)
        spinner.stop()
    except OLLAMA_ERRORS as e:
        spinner.stop()
        print(f'Failed to communicate with Ollama: {describe_ollama_error(e)}')
        sys.exit(1)
    messages = [{'role': 'assistant', 'content': greeting}]
    print(f'\n[{speaker}]: {greeting}')
    current_task_idx = 0
    total_tasks = len(tasks)
    attempts = 0
    task_started_at = db._utcnow()
    prev_task_idx = -1
    task_start_idx = len(messages)
    while current_task_idx < total_tasks:
        if current_task_idx != prev_task_idx:
            task_start_idx = len(messages)
            prev_task_idx = current_task_idx
        current_task = tasks[current_task_idx]
        actor_system = ACTOR_SYS.format(place=scenario.place, role=scenario.role, language=language, mood=mood, complication=actor_complication_block, task_setup=build_task_setup_block(current_task))
        print(f'\n--- Task {current_task_idx + 1}/{total_tasks} ---')
        translated_hint = hint_translations.get(current_task.goal, current_task.goal)
        print(f"🎯 Objective: {translated_hint} (type 'skip' to move on)")
        user_input = input('\nYou: ')
        if user_input.lower() in ['quit', 'exit']:
            print('Exiting...')
            break
        if user_input.lower() == 'skip':
            print(f'\n⏭️  Skipped: {current_task.goal}')
            db.log_task(conn, session_id, scenario_id, user_id, current_task_idx, current_task.goal, current_task.done_when, current_task.difficulty, current_task.phase, 'skipped', attempts, task_started_at, db._utcnow())
            tasks_skipped += 1
            current_task_idx += 1
            attempts = 0
            task_started_at = db._utcnow()
            prev_task_idx = current_task_idx
            task_start_idx = len(messages)
            continue
        if not user_input.strip():
            print(f"[You didn't type anything — say something to the {speaker.lower()}, or type 'skip'/'quit'.]")
            continue
        messages.append({'role': 'user', 'content': user_input})
        
        try:
            # 1. Coach feedback
            coach_feedback = call_coach(user_input, language)
            print(f'\n{coach_feedback}')
            
            # 2. Judge evaluation
            (is_done, hint) = evaluate_task(user_input, current_task.done_when, messages[task_start_idx:], language)
            
            # 3. Handle task completion and state advance
            if is_done:
                print(f'\n✅ TASK COMPLETED! Moving to next...')
                db.log_task(conn, session_id, scenario_id, user_id, current_task_idx, current_task.goal, current_task.done_when, current_task.difficulty, current_task.phase, 'completed', attempts + 1, task_started_at, db._utcnow())
                tasks_done += 1
                current_task_idx += 1
                attempts = 0
                task_started_at = db._utcnow()
                prev_task_idx = current_task_idx
                task_start_idx = len(messages)
            else:
                attempts += 1
                if attempts >= MAX_TASK_ATTEMPTS:
                    print(f'\n➡️  Moving on after {attempts} tries. Goal was: {current_task.goal}')
                    db.log_task(conn, session_id, scenario_id, user_id, current_task_idx, current_task.goal, current_task.done_when, current_task.difficulty, current_task.phase, 'failed', attempts, task_started_at, db._utcnow())
                    current_task_idx += 1
                    attempts = 0
                    task_started_at = db._utcnow()
                    prev_task_idx = current_task_idx
                    task_start_idx = len(messages)
                else:
                    print(f'\n❌ Task not yet completed. Keep trying! ({attempts}/{MAX_TASK_ATTEMPTS} attempts)')
                    if hint:
                        print(f'💡 Hint: {hint}')
            
            # 4. Generate NPC response
            if current_task_idx == total_tasks:
                actor_system = ACTOR_SYS.format(place=scenario.place, role=scenario.role, language=language, mood=mood, complication=actor_complication_block, task_setup="The customer has just completed their final interaction. Wrap up the conversation naturally in 1-2 sentences.")
            else:
                next_task = tasks[current_task_idx]
                actor_system = ACTOR_SYS.format(place=scenario.place, role=scenario.role, language=language, mood=mood, complication=actor_complication_block, task_setup=build_task_setup_block(next_task))
                
            print('')
            spinner = Spinner(f'{speaker} is thinking')
            spinner.start()
            actor_reply = call_actor(messages, actor_system, speaker=speaker)
            spinner.stop()
            messages.append({'role': 'assistant', 'content': actor_reply})
            print(f'\n[{speaker}]: {actor_reply}')
            
        except OLLAMA_ERRORS as e:
            spinner.stop()
            print(f'\n[⚠️  {describe_ollama_error(e)}]')
            print("[Your last message wasn't processed — please try again.]")
            if messages and messages[-1]['content'] == user_input:
                messages.pop()
            continue
    db.finish_session(conn, session_id, tasks_done, tasks_skipped)
    conn.close()
    if current_task_idx == total_tasks:
        print('\n========================================')
        print('🎉 CONGRATULATIONS! You completed all tasks! 🎉')
        print('========================================')