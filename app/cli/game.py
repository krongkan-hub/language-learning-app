"""The CLI session loop: greeting, then judge -> actor -> coach every turn.

Everything that calls the model is reached from main() here, so tests patch
the model functions on this module (app.cli.game.<name>).
"""
from ..i18n import t, scenario_name, scenario_place, normalize_language
from ..llm import (call_actor, stream_actor, translate_hints,
                   describe_llm_error, NPC_MOODS, MLX_ERRORS, BASE_MODEL,
                   sanitize_learner_input, DEBUG, _ensure_model,
                   reset_prompt_caches)
from ..session import (
    GREETING_MAX_SENTENCES,
    ACTOR_MAX_SENTENCES,
    build_greeting_system_prompt,
    build_actor_system_prompt,
    produce_greeting_turn,
    produce_actor_turn,
    recent_history,
)
from ..coach import call_coach, describe_situation
from ..judge import evaluate_task
from ..scenarios.builtins import SCENARIOS
from ..scenarios.models import Scenario
import random
import sys
import argparse
from .. import db
from .. import retrieval


from .terminal import Spinner, safe_input
from .menus import (choose_scenario, print_stats_report, run_correction_drill,
                    run_vocab_review)
from ..vocab_card import extract_and_format_vocab, parse_vocab


MAX_TASK_ATTEMPTS = 4


def _retrieve_review_words(conn, user_id: int, language: str, scenario: Scenario, tasks, limit: int = 3) -> list:
    """Due words that fit the scenario the learner just started.

    Mirrors app.web._retrieve_review_words: the scenario's place, role and
    first few goals become the query, the learner's own unpractised
    vocabulary is the corpus. Everything here degrades rather than fails: no
    embedder, no vectors, or an embedder that throws all end at
    least-recently-seen, which is what the app did before retrieval existed.
    A session must never die for a spaced-repetition nicety.
    """
    try:
        goals = [t_obj.goal for t_obj in tasks[:5]]
        query = retrieval.embed(retrieval.scenario_query(scenario.place, scenario.role, goals))
        rows = db.due_words_for(conn, user_id, language, query_vector=query, limit=limit)
        return [r['word'] for r in rows]
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(description="Language Conversation Coach CLI")
    parser.add_argument("--stats", action="store_true", help="Print progress report and exit")
    parser.add_argument("--lang", type=str, default="English", help="Target/display language")
    args, _ = parser.parse_known_args()

    if args.stats:
        raw_lang = args.lang.strip() if args.lang else 'English'
        if not raw_lang:
            language = 'English'
        else:
            language = normalize_language(raw_lang)
        if language is None:
            print(t('err_unsupported_language', 'English'))
            sys.exit(1)
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

    while True:
        raw_lang = safe_input('Which language do you want to practice? (e.g., English, Japanese): ', language='English').strip()
        if not raw_lang:
            language = 'English'
            break
        norm = normalize_language(raw_lang)
        if norm is not None:
            language = norm
            break
        print(t('err_unsupported_language', 'English'))

    conn = db.init_db()
    user_id = db.get_or_create_user(conn, target_lang=language)
    db.abandon_stale_sessions(conn, user_id)

    sc_by_name = {s.name: s for s in SCENARIOS if len(s.tasks) > 0}
    resumable_session = None

    while True:
        res = db.get_resumable_session(conn, user_id, language)
        if not res:
            break
        sess_row, logged_count = res
        if logged_count == 0:
            db.finish_session(conn, sess_row['id'], 0, 0)
            continue

        sc_name = sess_row['scenario_name']
        sc_obj = sc_by_name.get(sc_name)
        if not sc_obj:
            counts = conn.execute(
                "SELECT SUM(CASE WHEN outcome = 'completed' THEN 1 ELSE 0 END) as done, "
                "SUM(CASE WHEN outcome = 'skipped' THEN 1 ELSE 0 END) as skipped "
                "FROM task_logs WHERE session_id = ?",
                (sess_row['id'],)
            ).fetchone()
            done = counts['done'] if counts and counts['done'] is not None else 0
            skipped = counts['skipped'] if counts and counts['skipped'] is not None else 0
            db.finish_session(conn, sess_row['id'], done, skipped)
            continue

        logged_goals = db.get_logged_goals_for_session(conn, sess_row['id'])
        available_tasks = [t_item for t_item in sc_obj.tasks if t_item.goal not in logged_goals]
        if not available_tasks:
            counts = conn.execute(
                "SELECT SUM(CASE WHEN outcome = 'completed' THEN 1 ELSE 0 END) as done, "
                "SUM(CASE WHEN outcome = 'skipped' THEN 1 ELSE 0 END) as skipped "
                "FROM task_logs WHERE session_id = ?",
                (sess_row['id'],)
            ).fetchone()
            done = counts['done'] if counts and counts['done'] is not None else 0
            skipped = counts['skipped'] if counts and counts['skipped'] is not None else 0
            db.finish_session(conn, sess_row['id'], done, skipped)
            continue

        disp_name = scenario_name(sc_obj, language)
        total_tasks_count = sess_row['tasks_total']

        def _finish_resumable():
            counts = conn.execute(
                "SELECT SUM(CASE WHEN outcome = 'completed' THEN 1 ELSE 0 END) as done, "
                "SUM(CASE WHEN outcome = 'skipped' THEN 1 ELSE 0 END) as skipped "
                "FROM task_logs WHERE session_id = ?",
                (sess_row['id'],)
            ).fetchone()
            done = counts['done'] if counts and counts['done'] is not None else 0
            skipped = counts['skipped'] if counts and counts['skipped'] is not None else 0
            db.finish_session(conn, sess_row['id'], done, skipped)

        choice = safe_input(
            t('prompt_resume_session', language, name=disp_name, done=logged_count, total=total_tasks_count),
            language=language,
            on_exit=_finish_resumable
        ).strip().lower()
        if choice in ('y', 'yes', ''):
            resumable_session = (sess_row, logged_count, sc_obj)
            break
        else:
            _finish_resumable()
            break

    if resumable_session:
        sess_row, logged_count, scenario = resumable_session
        session_id = sess_row['id']
        mood = sess_row['mood']
        complication = sess_row['complication']
        logged_goals = db.get_logged_goals_for_session(conn, session_id)
        available_tasks = [t_item for t_item in scenario.tasks if t_item.goal not in logged_goals]
        temp_scenario = Scenario(
            name=scenario.name,
            place=scenario.place,
            role=scenario.role,
            speaker=scenario.speaker,
            tasks=available_tasks,
            complications=scenario.complications,
            name_translations=scenario.name_translations,
            place_translations=scenario.place_translations
        )
        seen = db.get_seen_task_goals(conn, user_id, scenario.name)
        retry_goals = db.get_unfinished_task_goals(conn, user_id, scenario.name)
        tasks = temp_scenario.get_session_tasks(num_tasks=10, seen_goals=seen, retry_goals=retry_goals)
        counts = conn.execute(
            "SELECT SUM(CASE WHEN outcome = 'completed' THEN 1 ELSE 0 END) as done, "
            "SUM(CASE WHEN outcome = 'skipped' THEN 1 ELSE 0 END) as skipped "
            "FROM task_logs WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        tasks_done = counts['done'] if counts and counts['done'] is not None else 0
        tasks_skipped = counts['skipped'] if counts and counts['skipped'] is not None else 0
    else:
        scenario = choose_scenario(language, conn, user_id)
        seen = db.get_seen_task_goals(conn, user_id, scenario.name)
        retry_goals = db.get_unfinished_task_goals(conn, user_id, scenario.name)
        tasks = scenario.get_session_tasks(num_tasks=10, seen_goals=seen, retry_goals=retry_goals)
        mood = random.choice(NPC_MOODS)
        complication = random.choice(scenario.complications) if scenario.complications else None
        session_id = db.create_session(conn, user_id, scenario.name, language, mood, complication, len(tasks))
        tasks_done = 0
        tasks_skipped = 0

    run_vocab_review(conn, user_id, language, on_exit=lambda: db.finish_session(conn, session_id, tasks_done, tasks_skipped))
    speaker = scenario.speaker
    situation = describe_situation(scenario.place, scenario.role, scenario.speaker)
    print(t('preparing_session', language))
    retried_count = sum(1 for t_obj in tasks if t_obj.goal in retry_goals)
    if retried_count > 0:
        print(t('retried_tasks_included', language, n=retried_count))
    hint_translations = translate_hints(tasks, language)
    review_words = _retrieve_review_words(conn, user_id, language, scenario, tasks)
    messages = []

    # 1. Initial Greeting
    greeting_system = build_greeting_system_prompt(
        scenario, tasks[0], language=language, mood=mood, complication=complication,
        review_words=review_words
    )
    
    # Pass a dummy seed message so standard user/assistant alternation works cleanly
    seed_messages = [{'role': 'user', 'content': 'Hello.'}]
    
    spinner = Spinner(t('spinner_connecting_model', language))
    spinner.start()
    try:
        greeting = produce_greeting_turn(seed_messages, greeting_system, speaker=speaker, max_sentences=GREETING_MAX_SENTENCES, actor_fn=call_actor, language=language)
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
    greeting, greeting_vocab = extract_and_format_vocab(greeting, language, scenario)
    
    messages.append({'role': 'assistant', 'content': greeting})
    print(f"\n[{speaker}]: {greeting}")
    if greeting_vocab:
        print(greeting_vocab)
        if parsed_greeting_vocab:
            db.log_vocab(conn, user_id, language, parsed_greeting_vocab[0], parsed_greeting_vocab[1], scenario.name,
             embedding=retrieval.embed_vocab(parsed_greeting_vocab[0], parsed_greeting_vocab[1]))

        
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

        actor_system = build_actor_system_prompt(
            scenario, current_task, language=language, mood=mood, complication=complication,
            review_words=review_words
        )

        print(f"\n{t('task_header', language, n=current_task_idx + 1, total=total_tasks)}")
        translated_goal = hint_translations.get((current_task_idx, current_task.goal), current_task.goal)
        print(t('objective_line', language, hint=translated_goal))
        
        user_input = safe_input(
            t('you_prompt', language),
            language=language,
            on_exit=lambda: db.finish_session(conn, session_id, tasks_done, tasks_skipped)
        )
        
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
                skip_actor_system = build_actor_system_prompt(
                    scenario, skip_task, language=language, mood=mood, complication=complication,
                    review_words=review_words
                )
                spinner = Spinner(t('spinner_setting_scene', language, speaker=speaker))
                spinner.start()
                skip_reply = produce_actor_turn(recent_history(messages), skip_actor_system, speaker=speaker, max_sentences=ACTOR_MAX_SENTENCES, actor_fn=call_actor, language=language)
                spinner.stop()
                parsed_skip_vocab = parse_vocab(skip_reply)
                skip_reply, skip_vocab = extract_and_format_vocab(skip_reply, language, scenario)
                messages.append({'role': 'assistant', 'content': skip_reply})
                print(f"\n[{speaker}]: {skip_reply}")
                if skip_vocab:
                    print(skip_vocab)
                    if parsed_skip_vocab:
                        db.log_vocab(conn, user_id, language, parsed_skip_vocab[0], parsed_skip_vocab[1], scenario.name,
             embedding=retrieval.embed_vocab(parsed_skip_vocab[0], parsed_skip_vocab[1]))

            continue
            
        if not user_input.strip():
            print(t('empty_input_warning', language, speaker=speaker.lower()))
            continue
            
        user_input_clean = sanitize_learner_input(user_input)
        messages.append({'role': 'user', 'content': user_input_clean})
        
        try:
            # 1. Judge evaluation with Spinner.
            #
            # The judge runs before the actor because the actor's system prompt
            # depends on its verdict: a completed task advances current_task_idx,
            # which selects the NEXT task to steer the NPC toward, or the wrap-up
            # prompt on the final one. The coach does NOT have that dependency,
            # so it moved below the actor — see step 4.
            vocab_targets = (getattr(current_task, 'vocab_translations', {}) or {}).get(language)
            with Spinner(t('spinner_analyzing', language)):
                (is_done, hint) = evaluate_task(user_input_clean, current_task.done_when, messages[task_start_idx:], language, vocab_targets)

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
                    # Counted alongside skips: the summary line and the sessions
                    # row are both labelled "Skipped/Failed", and before OPEN-25
                    # only skips incremented, so a session where every task ran
                    # out of attempts reported zero of everything.
                    tasks_skipped += 1
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
                actor_system = build_actor_system_prompt(
                    scenario,
                    "The customer has just completed their final interaction. Wrap up the conversation naturally in 1-2 sentences.",
                    language=language,
                    mood=mood,
                    complication=complication,
                    review_words=review_words
                )
            else:
                next_task = tasks[current_task_idx]
                actor_system = build_actor_system_prompt(
                    scenario, next_task, language=language, mood=mood, complication=complication,
                    review_words=review_words
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

            raw_actor_reply = produce_actor_turn(
                recent_history(messages), actor_system, speaker=speaker, max_sentences=ACTOR_MAX_SENTENCES, actor_fn=stream_actor, callback=on_sentence, language=language
            )
            if not first_sentence:
                sys.stdout.write("\n")
                sys.stdout.flush()

            parsed_actor_vocab = parse_vocab(raw_actor_reply)
            actor_reply, actor_vocab = extract_and_format_vocab(raw_actor_reply, language, scenario)
            
            messages.append({'role': 'assistant', 'content': actor_reply})
            if actor_vocab:
                print(actor_vocab)
                if parsed_actor_vocab:
                    db.log_vocab(conn, user_id, language, parsed_actor_vocab[0], parsed_actor_vocab[1], scenario.name,
             embedding=retrieval.embed_vocab(parsed_actor_vocab[0], parsed_actor_vocab[1]))

            # 4. Coach feedback, after the NPC has spoken.
            #
            # Measured 2026-09-06: a warm turn spends ~1.5s in the coach, ~3.9s
            # in the judge, and ~3.0s before the actor's first streamed sentence.
            # Running the coach first meant the learner watched a spinner for the
            # whole ~8.4s before any dialogue appeared. Moving it after the actor
            # takes that silent stretch down to ~6.9s and puts the NPC's reply on
            # screen first, which is the part the conversation depends on.
            with Spinner(t('spinner_analyzing', language)):
                coach_feedback = call_coach(user_input_clean, language, situation=situation)

            # Storage only, and deliberately never fatal: a turn that already
            # happened must not be lost to a logging error. The web front end
            # records the same thing at the same point in its own turn.
            repeats = []
            try:
                ids = db.log_mistakes(conn, user_id, language, session_id,
                                      scenario.name, coach_feedback)
                repeats = db.repeats_among(conn, ids)
            except Exception:
                pass

            print(f"\n{coach_feedback}")
            for r in repeats:
                print(t('mistake_repeat', language, n=r['occurrences'],
                        quoted=r['quoted'], correction=r['correction']))

            run_correction_drill(
                coach_feedback,
                language,
                on_exit=lambda: db.finish_session(conn, session_id, tasks_done, tasks_skipped)
            )


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
