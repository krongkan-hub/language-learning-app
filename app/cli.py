from .i18n import t, scenario_name, scenario_place
from .llm import call_actor, stream_actor, translate_hints, describe_llm_error, NPC_MOODS, MLX_ERRORS, BASE_MODEL, GREETING_SYS, ACTOR_SYS, build_task_setup_block, sanitize_learner_input, DEBUG, _ensure_model, reset_prompt_caches
from .coach import call_coach
from .judge import evaluate_task
from .scenarios.builtins import SCENARIOS
import random
import sys
import argparse
from . import db
import re

MAX_TASK_ATTEMPTS = 4

import threading
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


# Languages that capitalize every common noun, where a mid-sentence capital
# carries no proper-noun signal and _is_name would reject every valid tip.
NOUN_CAPITALIZING_LANGUAGES = {'german', 'deutsch', 'de', 'luxembourgish'}


def _is_name(word: str, dialogue: str, language: str) -> bool:
    """True when the vocab word is a proper noun rather than reusable vocabulary.

    A name — the venue, the NPC, a brand, a city — teaches the learner nothing
    they can carry to another conversation. The actor prompt forbids picking
    one; this is the backstop for when the model does it anyway. Capitalization
    alone is too weak a signal, since the model also capitalizes ordinary words
    in the vocab field, so we additionally require the word to appear
    capitalized mid-sentence in the NPC's own dialogue — which only an
    inherently capitalized word does. Scripts without letter case (Japanese,
    Chinese) never match and are unaffected.
    """
    if language.strip().lower() in NOUN_CAPITALIZING_LANGUAGES:
        return False
    tokens = re.findall(r'[^\W\d_]+', word)
    if not tokens or not all(t[0].isupper() for t in tokens):
        return False
    return bool(re.search(r'[^.!?]\s+' + re.escape(word), dialogue))


from typing import Optional


def parse_vocab(text: str) -> Optional[tuple[str, str, str]]:
    """Parse (word, explanation, encourage) from text with or without <vocab> tags, or return None."""

    if not text:
        return None
    tag_pattern = r'<vocab>\s*word:\s*(.*?)\s+explanation:\s*(.*?)\s+encourage:\s*(.*?)\s*</vocab>'
    match = re.search(tag_pattern, text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        tag_pattern = r'(?:<vocab>\s*)?word:\s*(.*?)\s+explanation:\s*(.*?)\s+encourage:\s*(.*?)(?:\s*</vocab>)?\s*$'
        match = re.search(tag_pattern, text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    return None


def extract_and_format_vocab(text: str, language: str = "") -> tuple[str, str]:
    """Extract vocab blocks from text (with or without <vocab> tags) and return (clean_text, formatted_vocab_box).

    A tip whose word is a proper noun is dropped: the block is still stripped
    from the dialogue, but no box is returned.
    """
    vocab_box = ""
    parsed = parse_vocab(text)
    if parsed:
        word_text, exp_text, enc_text = parsed
        
        # Remove matched block from original text
        tag_pattern = r'<vocab>\s*word:\s*(.*?)\s+explanation:\s*(.*?)\s+encourage:\s*(.*?)\s*</vocab>'
        match = re.search(tag_pattern, text, flags=re.DOTALL | re.IGNORECASE)
        
        if not match:
            tag_pattern = r'(?:<vocab>\s*)?word:\s*(.*?)\s+explanation:\s*(.*?)\s+encourage:\s*(.*?)(?:\s*</vocab>)?\s*$'
            match = re.search(tag_pattern, text, flags=re.DOTALL | re.IGNORECASE)

        if match:
            text = (text[:match.start()] + " " + text[match.end():]).strip()
            text = re.sub(r'</?vocab>', '', text, flags=re.IGNORECASE).strip()
            text = re.sub(r'\s+', ' ', text)

        if not _is_name(word_text, text, language):
            vocab_box = t('vocab_tip_box', language, word=word_text, exp=exp_text, enc=enc_text)

    return text, vocab_box


def run_vocab_review(conn, user_id: int, language: str) -> None:
    """Run a short recall quiz for up to 3 words due for review."""
    words = db.get_vocab_for_review(conn, user_id, language, limit=3)
    if not words:
        return

    print(t('review_header', language))
    for row in words:
        word = row['word']
        exp = row['explanation']
        ans = input(t('review_prompt', language, exp=exp)).strip()
        if ans.lower() == 'skip':
            break
        correct = (ans.lower() == word.strip().lower())
        if correct:
            print(t('review_correct', language, word=word))
        else:
            print(t('review_incorrect', language, word=word))
        db.mark_vocab_reviewed(conn, user_id, language, word, correct)



def print_stats_report(conn, language: str = 'English') -> None:
    """Print progress report for user."""
    row = conn.execute("SELECT id FROM user_profiles ORDER BY last_active DESC, id DESC LIMIT 1").fetchone()
    if row:
        user_id = row['id']
    else:
        user_id = db.get_or_create_user(conn, target_lang=language)

    overall = db.get_overall_stats(conn, user_id)
    vocab = db.get_vocab_stats(conn, user_id)
    scenario_stats = db.get_all_scenario_stats(conn, user_id)

    played = [s for s in scenario_stats.values() if s.get('plays', 0) > 0]
    played.sort(key=lambda x: x.get('last_played') or '', reverse=True)

    sc_by_name = {s.name: s for s in SCENARIOS}

    print('=' * 50)
    print(t('stats_header', language))
    print('=' * 50)

    print(t('stats_overall_header', language))
    print(t('stats_sessions_played', language, n=overall['sessions_played']))
    print(t('stats_tasks_attempted', language, n=overall['tasks_attempted']))
    print(t('stats_tasks_completed', language, n=overall['tasks_completed']))
    print(t('stats_overall_rate', language, pct=overall['completion_rate']))

    print(f"\n{t('stats_scenarios_header', language)}")
    if not played:
        print(t('stats_no_scenarios_played', language))
    else:
        for s_info in played:
            raw_name = s_info['scenario_name']
            sc_obj = sc_by_name.get(raw_name)
            disp_name = scenario_name(sc_obj, language) if sc_obj else raw_name
            mastery_str = t(s_info['mastery'], language)
            print(t('stats_scenario_item', language,
                    name=disp_name,
                    plays=s_info['plays'],
                    best_pct=s_info['best_pct'],
                    mastery=mastery_str))

    print(f"\n{t('stats_vocab_header', language)}")
    print(t('stats_vocab_total', language, n=vocab['total_words']))
    print(t('stats_vocab_learned', language, n=vocab['learned_words']))
    print(t('stats_vocab_due', language, n=vocab['due_words']))
    print('=' * 50 + '\n')


def select_builtin_scenario(language: str = 'English', conn=None, user_id: int = None):
    """Pick from the hardcoded SCENARIOS list (original behaviour)."""
    valid_scenarios = [s for s in SCENARIOS if len(s.tasks) > 0]
    if not valid_scenarios:
        print(t('err_no_scenarios', language))
        sys.exit(1)
    random_scenario = random.choice(valid_scenarios)
    print(f"\n{t('random_scenario', language, name=scenario_name(random_scenario, language))}")
    choice = input(t('prompt_play_scenario', language)).strip().lower()
    if choice == 'y' or choice == '':
        return random_scenario

    stats_map = {}
    if conn is not None and user_id is not None:
        stats_map = db.get_all_scenario_stats(conn, user_id)

    print(f"\n{t('available_scenarios', language)}")
    for (i, s) in enumerate(valid_scenarios):
        s_stats = stats_map.get(s.name) if stats_map else None
        if s_stats and s_stats.get('plays', 0) > 0:
            mastery_key = s_stats.get('mastery', 'newbie')
            mastery_str = t(mastery_key, language)
            print(t('scenario_item_with_mastery', language, i=i + 1, name=scenario_name(s, language), n=len(s.tasks), mastery=mastery_str))
        else:
            print(t('scenario_item', language, i=i + 1, name=scenario_name(s, language), n=len(s.tasks)))
    while True:
        try:
            sel = input(f"\n{t('prompt_select_scenario', language)}").strip()
            if sel.lower() in ('quit', 'exit'):
                print(t('exiting', language))
                sys.exit(0)
            idx = int(sel) - 1
            if 0 <= idx < len(valid_scenarios):
                return valid_scenarios[idx]
            else:
                print(t('invalid_number', language))
        except ValueError:
            print(t('enter_valid_number', language))


def choose_scenario(language: str, conn, user_id: int):
    """Pick a built-in scenario. Sessions are keyed by scenario name, so
    nothing needs persisting up front."""
    return select_builtin_scenario(language, conn=conn, user_id=user_id)


def main():
    parser = argparse.ArgumentParser(description="Language Conversation Coach CLI")
    parser.add_argument("--stats", action="store_true", help="Print progress report and exit")
    parser.add_argument("--lang", type=str, default="English", help="Target/display language")
    args, _ = parser.parse_known_args()

    lang_map = {'en': 'English', 'ja': 'Japanese', 'jp': 'Japanese', 'fr': 'French', 'es': 'Spanish', 'de': 'German', 'zh': 'Chinese', 'ko': 'Korean', 'kr': 'Korean', 'ru': 'Russian', 'it': 'Italian'}

    if args.stats:
        raw_lang = args.lang.strip() if args.lang else 'English'
        language = lang_map.get(raw_lang.lower(), raw_lang.capitalize() if raw_lang else 'English')
        conn = db.init_db()
        print_stats_report(conn, language)
        conn.close()
        sys.exit(0)

    print('========================================')
    print(t('cli_title', 'English'))
    print('========================================')
    # Deliberately broad MLX_ERRORS catch because CLI is top-level user-facing boundary
    try:
        _ensure_model()
    except MLX_ERRORS as e:
        if DEBUG:
            raise
        print(t('err_model_init', 'English', model=BASE_MODEL))
        print(f"[⚠️  {describe_llm_error(e)}]")
        sys.exit(1)
    language = input('Which language do you want to practice? (e.g., English, Japanese): ').strip()
    if not language:
        language = 'English'
    else:
        language = lang_map.get(language.lower(), language.capitalize())
    conn = db.init_db()
    user_id = db.get_or_create_user(conn, target_lang=language)
    scenario = choose_scenario(language, conn, user_id)
    run_vocab_review(conn, user_id, language)
    seen = db.get_seen_task_goals(conn, user_id, scenario.name)
    retry_goals = db.get_unfinished_task_goals(conn, user_id, scenario.name)
    tasks = scenario.get_session_tasks(num_tasks=10, seen_goals=seen, retry_goals=retry_goals)
    speaker = scenario.speaker
    print(t('preparing_session', language))
    retried_count = sum(1 for t_obj in tasks if t_obj.goal in retry_goals)
    if retried_count > 0:
        print(t('retried_tasks_included', language, n=retried_count))
    hint_translations = translate_hints(tasks, language)
    mood = random.choice(NPC_MOODS)
    complication = random.choice(scenario.complications) if scenario.complications else None
    session_id = db.create_session(conn, user_id, scenario.name, language, mood, complication, len(tasks))
    tasks_done = 0
    tasks_skipped = 0
    messages = []
    
    actor_complication_block = f" Also, there is a minor issue today: {complication}." if complication else ""
    
    # 1. Initial Greeting
    greeting_system = GREETING_SYS.format(
        place=scenario.place,
        role=scenario.role,
        language=language,
        mood=mood,
        complication=actor_complication_block,
        task_setup=build_task_setup_block(tasks[0])
    )
    
    # Pass a dummy seed message so standard user/assistant alternation works cleanly
    seed_messages = [{'role': 'user', 'content': 'Hello.'}]
    
    spinner = Spinner(t('spinner_connecting_model', language))
    spinner.start()
    try:
        greeting = call_actor(seed_messages, greeting_system, speaker=speaker, max_sentences=4)
    # Deliberately broad because CLI is top-level user-facing boundary
    except MLX_ERRORS as e:
        if DEBUG:
            raise
        spinner.stop()
        print(f"\n[⚠️  {describe_llm_error(e)}]")
        print(t('err_check_mlx', language))
        sys.exit(1)
    spinner.stop()
    
    parsed_greeting_vocab = parse_vocab(greeting)
    greeting, greeting_vocab = extract_and_format_vocab(greeting, language)
    
    messages.append({'role': 'assistant', 'content': greeting})
    print(f"\n[{speaker}]: {greeting}")
    if greeting_vocab:
        print(greeting_vocab)
        if parsed_greeting_vocab:
            db.log_vocab(conn, user_id, language, parsed_greeting_vocab[0], parsed_greeting_vocab[1], scenario.name)

        
    task_start_idx = 1 # Start index of conversation turns for current task
    prev_task_idx = 0
    total_tasks = len(tasks)
    current_task_idx = 0
    attempts = 0
    task_started_at = db._utcnow()

    # 2. Main Game Loop
    while current_task_idx < total_tasks:
        current_task = tasks[current_task_idx]
        
        # If task changed, update task_start_idx to current message count
        if current_task_idx != prev_task_idx:
            task_start_idx = len(messages)
            prev_task_idx = current_task_idx

        actor_system = ACTOR_SYS.format(
            place=scenario.place,
            role=scenario.role,
            language=language,
            mood=mood,
            complication=actor_complication_block,
            task_setup=build_task_setup_block(current_task)
        )

        print(f"\n{t('task_header', language, n=current_task_idx + 1, total=total_tasks)}")
        translated_goal = hint_translations.get((current_task_idx, current_task.goal), current_task.goal)
        print(t('objective_line', language, hint=translated_goal))
        
        user_input = input(t('you_prompt', language))
        
        if user_input.lower() in ['quit', 'exit']:
            print(t('exiting', language))
            break
            
        if user_input.lower() == 'skip':
            print(f"\n{t('skipped_task', language, goal=translated_goal)}")
            db.log_task(conn, session_id, scenario.name, user_id, current_task_idx, current_task.goal, current_task.done_when, current_task.difficulty, current_task.phase, 'skipped', attempts, task_started_at, db._utcnow())
            tasks_skipped += 1
            current_task_idx += 1
            attempts = 0
            task_started_at = db._utcnow()
            prev_task_idx = current_task_idx
            task_start_idx = len(messages)

            # BL-22 / BUG-030: Generate NPC turn to establish new task premise on skip
            if current_task_idx < total_tasks:
                skip_task = tasks[current_task_idx]
                skip_actor_system = ACTOR_SYS.format(
                    place=scenario.place,
                    role=scenario.role,
                    language=language,
                    mood=mood,
                    complication=actor_complication_block,
                    task_setup=build_task_setup_block(skip_task)
                )
                spinner = Spinner(t('spinner_setting_scene', language, speaker=speaker))
                spinner.start()
                skip_reply = call_actor(messages, skip_actor_system, speaker=speaker)
                spinner.stop()
                parsed_skip_vocab = parse_vocab(skip_reply)
                skip_reply, skip_vocab = extract_and_format_vocab(skip_reply, language)
                messages.append({'role': 'assistant', 'content': skip_reply})
                print(f"\n[{speaker}]: {skip_reply}")
                if skip_vocab:
                    print(skip_vocab)
                    if parsed_skip_vocab:
                        db.log_vocab(conn, user_id, language, parsed_skip_vocab[0], parsed_skip_vocab[1], scenario.name)

            continue
            
        if not user_input.strip():
            print(t('empty_input_warning', language, speaker=speaker.lower()))
            continue
            
        user_input_clean = sanitize_learner_input(user_input)
        messages.append({'role': 'user', 'content': user_input_clean})
        
        try:
            # 1. Coach feedback & Judge evaluation with Spinner
            eval_spinner = Spinner(t('spinner_analyzing', language))
            eval_spinner.start()

            coach_feedback = call_coach(user_input_clean, language)
            (is_done, hint) = evaluate_task(user_input_clean, current_task.done_when, messages[task_start_idx:], language)

            eval_spinner.stop()
            
            print(f"\n{coach_feedback}")
            
            # 2. Handle task completion and state advance
            if is_done:
                print(f"\n{t('task_completed', language)}")
                db.log_task(conn, session_id, scenario.name, user_id, current_task_idx, current_task.goal, current_task.done_when, current_task.difficulty, current_task.phase, 'completed', attempts + 1, task_started_at, db._utcnow())
                tasks_done += 1
                current_task_idx += 1
                attempts = 0
                task_started_at = db._utcnow()
                prev_task_idx = current_task_idx
                task_start_idx = len(messages)
            else:
                attempts += 1
                if attempts >= MAX_TASK_ATTEMPTS:
                    print(f"\n{t('moving_on_failed', language, n=attempts, goal=translated_goal)}")
                    db.log_task(conn, session_id, scenario.name, user_id, current_task_idx, current_task.goal, current_task.done_when, current_task.difficulty, current_task.phase, 'failed', attempts, task_started_at, db._utcnow())
                    current_task_idx += 1
                    attempts = 0
                    task_started_at = db._utcnow()
                    prev_task_idx = current_task_idx
                    task_start_idx = len(messages)
                else:
                    print(f"\n{t('task_not_completed', language, n=attempts, max=MAX_TASK_ATTEMPTS)}")
                    if current_task.hint:
                        translated_strategy_hint = hint_translations.get((current_task_idx, current_task.hint), current_task.hint)
                        print(t('strategy_hint', language, hint=translated_strategy_hint))
                    if hint:
                        print(t('judge_note', language, hint=hint))

            # 3. Generate NPC response
            if current_task_idx == total_tasks:
                actor_system = ACTOR_SYS.format(
                    place=scenario.place,
                    role=scenario.role,
                    language=language,
                    mood=mood,
                    complication=actor_complication_block,
                    task_setup="The customer has just completed their final interaction. Wrap up the conversation naturally in 1-2 sentences."
                )
            else:
                next_task = tasks[current_task_idx]
                actor_system = ACTOR_SYS.format(
                    place=scenario.place,
                    role=scenario.role,
                    language=language,
                    mood=mood,
                    complication=actor_complication_block,
                    task_setup=build_task_setup_block(next_task)
                )
                
            first_sentence = True

            def on_sentence(sentence: str):
                nonlocal first_sentence
                if first_sentence:
                    sys.stdout.write(f"\n[{speaker}]: {sentence}")
                    first_sentence = False
                else:
                    sys.stdout.write(f" {sentence}")
                sys.stdout.flush()

            raw_actor_reply = stream_actor(messages, actor_system, speaker=speaker, callback=on_sentence)
            if not first_sentence:
                sys.stdout.write("\n")
                sys.stdout.flush()

            parsed_actor_vocab = parse_vocab(raw_actor_reply)
            actor_reply, actor_vocab = extract_and_format_vocab(raw_actor_reply, language)
            
            messages.append({'role': 'assistant', 'content': actor_reply})
            if actor_vocab:
                print(actor_vocab)
                if parsed_actor_vocab:
                    db.log_vocab(conn, user_id, language, parsed_actor_vocab[0], parsed_actor_vocab[1], scenario.name)


        # Deliberately broad because CLI is top-level user-facing boundary
        except MLX_ERRORS as e:
            if DEBUG:
                raise
            if 'spinner' in locals() and spinner:
                spinner.stop()
            print(f"\n[⚠️  {describe_llm_error(e)}]")
            print(t('msg_not_processed', language))
            if messages and messages[-1]['content'] == user_input_clean:
                messages.pop()
            continue

    db.finish_session(conn, session_id, tasks_done, tasks_skipped)
    reset_prompt_caches()
    
    # 3. End-of-Session Summary & Review
    print("\n" + "="*50)
    print(t('session_summary_header', language))
    print("="*50)
    print(t('summary_scenario', language, name=scenario_name(scenario, language), place=scenario_place(scenario, language)))
    print(t('summary_target_language', language, language=language))
    print(t('summary_total_tasks', language, n=total_tasks))
    print(t('summary_tasks_completed', language, n=tasks_done))
    print(t('summary_tasks_failed', language, n=tasks_skipped))
    success_rate = (tasks_done / total_tasks * 100) if total_tasks > 0 else 0
    print(t('summary_completion_score', language, pct=f"{success_rate:.1f}"))
    print(t('summary_db_saved', language, path=db.DB_PATH))
    print("="*50 + "\n")
    
    conn.close()