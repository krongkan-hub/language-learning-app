"""main(): set up, then the session loop, printing each event the turn
logic in turns.py emits as it happens.
"""
import argparse
import logging
import os
import re
import signal
import sys

from .. import db
from ..i18n import mood_label, scenario_name, scenario_place, speaker_label, t, normalize_language
from ..llm import (BASE_MODEL, DEBUG, MLX_ERRORS, _ensure_model, describe_llm_error,
                   reset_prompt_caches, sanitize_learner_input)
from ..telemetry import setup as setup_tracing
from . import turns
from .menus import (choose_language, choose_mode, print_stats_report, select_scenario,
                    select_topic)
from .state import (AWAITING_INPUT, DRILL, FINISHED, check_drill, skip_task,
                    start_explain_session, start_review_session, start_scenario_session,
                    _database)
from .terminal import Spinner, safe_input


# One message is at most this long (security review, 45e1687): every turn runs
# the judge, the actor and the coach over it.
MAX_INPUT_CHARS = 1000


def _squeezed(text: str) -> str:
    return re.sub(r'\s+', '', text)


class Renderer:
    """Prints a session's events. A spinner runs while a stage is working
    and stops on the next event, so nothing is ever written over it."""

    def __init__(self, language: str, speaker: str):
        self.language = language
        self.speaker = speaker
        self.spinner = None
        self.streaming = False
        self.streamed = []

    def _stop_spinner(self):
        if self.spinner is not None:
            self.spinner.stop()
            self.spinner = None

    def __call__(self, ev: dict):
        self._stop_spinner()
        getattr(self, 'on_' + ev['type'], lambda ev: None)(ev)

    def on_stage(self, ev):
        name = ev['name']
        label = {'preparing': t('preparing_session', self.language),
                 'greeting': t('spinner_connecting_model', self.language),
                 'replying': t('spinner_thinking', self.language, speaker=self.speaker),
                 }.get(name, t('spinner_analyzing', self.language))
        self.spinner = Spinner(label)
        self.spinner.start()

    def on_sentence(self, ev):
        if not self.streaming:
            sys.stdout.write(f"\n[{self.speaker}]: {ev['text']}")
            self.streaming = True
            self.streamed = [ev['text']]
        else:
            # Japanese is written without spaces between sentences.
            sep = '' if self.language == 'Japanese' else ' '
            sys.stdout.write(f"{sep}{ev['text']}")
            self.streamed.append(ev['text'])
        sys.stdout.flush()

    def on_npc(self, ev):
        # A streamed reply is already on screen sentence by sentence — unless
        # the stream failed partway and the actor fell back to a whole new
        # reply, which is what the transcript records, so it is shown too.
        if self.streaming:
            print()
            self.streaming = False
            if _squeezed(''.join(self.streamed)) == _squeezed(ev['text']):
                return
        print(f"\n[{ev.get('speaker') or self.speaker}]: {ev['text']}")

    def on_vocab(self, ev):
        print(ev['box'])

    def on_task_result(self, ev):
        lang = self.language
        if ev['done']:
            print(f"\n{t('task_completed', lang)}")
        elif ev.get('moved_on'):
            print(f"\n{t('moving_on_failed', lang, n=ev['attempts'], goal=ev['goal'])}")
        else:
            print(f"\n{t('task_not_completed', lang, n=ev['attempts'], max=ev['max_attempts'])}")
            if ev.get('strategy'):
                print(t('strategy_hint', lang, hint=ev['strategy']))
            if ev.get('hint'):
                print(t('judge_note', lang, hint=ev['hint']))

    def on_coach(self, ev):
        print(f"\n{ev['text']}")
        for r in ev['repeats']:
            print(t('mistake_repeat', self.language, n=r['occurrences'],
                    quoted=r['quoted'], correction=r['correction']))

    def on_vocab_used(self, ev):
        for w in ev['words']:
            key = 'vocab_learned' if w['count'] >= 3 else 'vocab_used'
            print(t(key, self.language, word=w['word'], n=w['count']))

    def on_error(self, ev):
        # A turn can fail after streaming a sentence or two: end that line, or
        # the next unstreamed NPC line is swallowed and the next streamed one
        # loses its speaker label.
        if self.streaming:
            print()
            self.streaming = False
        print(f"\n[⚠️  {ev['detail']}] {ev['message']}")

    def on_finished(self, ev):
        lang = self.language
        total, done = ev['tasks_total'], ev['tasks_done']
        print('\n' + '=' * 50)
        print(t('session_summary_header', lang))
        print('=' * 50)
        print(t('summary_total_tasks', lang, n=total))
        print(t('summary_tasks_completed', lang, n=done))
        print(t('summary_tasks_failed', lang, n=ev['tasks_missed']))
        pct = (done / total * 100) if total else 0
        print(t('summary_completion_score', lang, pct=f'{pct:.1f}'))
        progress = ev.get('progress')
        if progress and progress.get('next_rank'):
            rank = t(progress['next_rank'], lang)
            if progress.get('plays_needed'):
                print(t('next_plays', lang, n=progress['plays_needed'], rank=rank))
            elif progress.get('pct_needed'):
                print(t('next_pct', lang, p=progress['pct_needed'], rank=rank))
        if ev.get('words_due'):
            print(t('words_due', lang, n=ev['words_due']))
        for m in ev.get('repeats') or []:
            print(t('stats_mistake_item', lang, n=m['occurrences'],
                    quoted=m['example_quoted'], correction=m['example_correction']))
        print('=' * 50 + '\n')


def _print_banner(sess):
    lang = sess.language
    if sess.explaining:
        print(f"\n{t('explain_banner', lang, name=sess.topic.title(lang), listener=sess.topic.listener(lang))}")
        return
    print(f"\n{t('session_banner', lang, name=scenario_name(sess.scenario, lang), place=scenario_place(sess.scenario, lang), speaker=speaker_label(sess.scenario.speaker, lang), mood=mood_label(sess.mood, lang))}")
    if sess.retried:
        print(t('retried_tasks_included', lang, n=sess.retried))


def _speaker(sess) -> str:
    lang = sess.language
    return (sess.topic.listener_short(lang) if sess.explaining
            else speaker_label(sess.scenario.speaker, lang))


def _goal_text(sess) -> str:
    if sess.explaining:
        return sess.current_task
    task = sess.current_task
    return sess.hint_translations.get((sess.task_idx, task.goal), task.goal)


def _run_drill(sess):
    """One prompt per correction, and no way past a wrong one: the drill is
    the one place the learner is meant to be held. `quit` still ends the
    session, as it does at the main prompt."""
    lang = sess.language
    while sess.drill_targets:
        target = sess.drill_targets[0]
        print(f"\n{t('drill_intro', lang, correction=target)}")
        while True:
            typed = safe_input(t('drill_prompt', lang), language=lang,
                               on_exit=lambda: turns._finish(sess))
            if check_drill(sess, typed):          # first: a correction may BE "exit"
                break
            if typed.strip().lower() in ('quit', 'exit'):
                print(t('exiting', lang))
                turns._finish(sess)
                return
            print(t('drill_retry', lang, correction=target))
        print(t('drill_correct', lang))
    if sess.current_task is None:
        turns._finish(sess)
    else:
        sess.set_state(AWAITING_INPUT)


def run_session(sess):
    """The loop: show the task, read a line, act on it, until the session
    is finished — by the last task, or by `quit`."""
    lang = sess.language
    shown_idx = None
    try:
        turns.open_session(sess)
        while sess.state != FINISHED:
            if sess.state == DRILL:
                _run_drill(sess)
                continue
            if sess.current_task is None:
                turns._finish(sess)
                break
            if shown_idx != sess.task_idx:
                print(f"\n{t('task_header', lang, n=sess.task_idx + 1, total=sess.total_tasks)}")
                print(t('objective_line', lang, hint=_goal_text(sess)))
                shown_idx = sess.task_idx
            raw = safe_input(t('you_prompt', lang), language=lang,
                             on_exit=lambda: turns._finish(sess))
            command = raw.strip().lower()
            if command in ('quit', 'exit'):
                print(t('exiting', lang))
                turns._finish(sess)
                break
            if command == 'skip':
                goal = _goal_text(sess)
                try:
                    skip_task(sess)
                except Exception as exc:        # its DB write; nothing has moved yet
                    turns._report(sess, exc)
                    continue
                print(f"\n{t('skipped_task', lang, goal=goal)}")
                if sess.current_task is not None and not sess.explaining:
                    turns._run_scene_turn(sess)
                continue
            if len(raw) > MAX_INPUT_CHARS:
                print(t('input_too_long', lang, n=len(raw), max=MAX_INPUT_CHARS))
                continue
            text = sanitize_learner_input(raw)
            if not text:
                print(t('empty_input_warning', lang, speaker=_speaker(sess).lower()))
                continue
            turns.take_turn(sess, text)
    finally:
        # Ctrl-C during a model call, or the terminal closing, ends the loop
        # with an exception; the session is finished all the same.
        if sess.state != FINISHED:
            turns._finish(sess)
    reset_prompt_caches()


def _log_to_file() -> str:
    """Send the app's log records to a file. With no handler configured,
    Python's last-resort handler prints them to stderr — a failed turn's
    traceback (turns._report), local paths and all, over the spinner."""
    path = os.environ.get('LANGUAGE_COACH_LOG') or os.path.join(
        os.path.expanduser('~'), '.cache', 'language-coach', 'cli.log')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    handler = logging.FileHandler(path, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
    log = logging.getLogger('app')
    log.addHandler(handler)
    log.propagate = False
    return path


def main():
    parser = argparse.ArgumentParser(description='Language Conversation Coach')
    parser.add_argument('--stats', action='store_true', help='Print progress report and exit')
    parser.add_argument('--lang', type=str, default=None,
                        help='Language to practise (English or Japanese); asked if omitted')
    parser.add_argument('--tasks', type=int, default=10, choices=range(1, 21), metavar='1-20',
                        help='Tasks per roleplay session (default 10)')
    args, _ = parser.parse_known_args()

    language = None
    if args.lang is not None:
        language = normalize_language(args.lang.strip() or 'English')
        if language is None:
            print(t('err_unsupported_language', 'English'))
            sys.exit(1)

    if args.stats:
        with _database() as conn:
            print_stats_report(conn, language or 'English')
        return

    _log_to_file()
    # Closing the terminal sends SIGHUP, which kills the process outright;
    # as SystemExit it unwinds through run_session and finishes the session.
    signal.signal(signal.SIGHUP, lambda *_: sys.exit(0))
    print('========================================')
    print(t('cli_title', 'English'))
    print('========================================')
    try:
        _ensure_model()
    except MLX_ERRORS as e:
        if DEBUG:
            raise
        print(t('err_model_init', 'English', model=BASE_MODEL))
        print(f"[⚠️  {describe_llm_error(e)}]")
        print(t('err_check_mlx', 'English'))
        sys.exit(1)
    setup_tracing()

    language = language or choose_language()
    with _database() as conn:
        user_id = db.get_or_create_user(conn, target_lang=language)
        sess = None
        while sess is None:
            mode = choose_mode(language)
            if mode == 'review':
                sess = start_review_session(conn, user_id, language)
                if sess is None:
                    print(t('review_nothing_yet', language))
            elif mode == 'explain':
                sess = start_explain_session(conn, user_id, language, select_topic(language))
            else:
                scenario = select_scenario(language, conn, user_id)
                sess = start_scenario_session(conn, user_id, language, scenario,
                                              num_tasks=args.tasks)
    sess.sink = Renderer(language, _speaker(sess))
    _print_banner(sess)
    run_session(sess)
