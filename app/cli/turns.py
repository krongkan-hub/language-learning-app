"""Everything that calls the model: the greeting, a learner turn
(judge -> actor -> coach), the explain-mode pair, and the summary.

Each reports through Session.emit(). Tests patch the model functions on THIS
module (app.cli.turns.<name>), where they are looked up.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from .. import db
from .. import retrieval
from ..coach import (call_coach, coach_system, correction_targets,
                     describe_situation, is_clean_verdict)
from ..coach.verdict import _CORRECTION_BULLET
from ..explain import listen
from ..i18n import speaker_label, t
from ..judge import evaluate_task
from ..llm import (DEBUG, MLX_ERRORS, call_actor, describe_llm_error, prefill,
                   sanitize, stop_prefill, stream_actor, translate_hints)
from ..llm.guards import reads_as_chinese
from ..session import (ACTOR_MAX_SENTENCES, GREETING_MAX_SENTENCES, actor_view,
                       build_actor_system_prompt, build_greeting_system_prompt,
                       produce_actor_turn, produce_greeting_turn, recent_history)
from ..telemetry import tracer
from ..vocab_card import _not_in_dialogue, extract_and_format_vocab, parse_vocab, words_used
from .state import (AWAITING_INPUT, BUSY, DRILL, FINISHED, JAPANESE_SCRIPT,
                    MAX_TASK_ATTEMPTS, Session, _database)

WRAP_UP = ('The customer has just completed their final interaction. '
           'Wrap up the conversation naturally in 1-2 sentences.')


def _report(sess: Session, exc: Exception):
    """What the learner is told when a turn fails: that it was not processed,
    not the raw exception (an OSError's message is a local path). Under
    DEBUG the traceback is what the developer needs, so it goes through."""
    if DEBUG:
        raise exc
    logging.getLogger(__name__).exception('turn failed: %s', describe_llm_error(exc)
                                          if isinstance(exc, MLX_ERRORS) else exc)
    detail = 'MLX Engine Error' if isinstance(exc, MLX_ERRORS) else exc.__class__.__name__
    sess.emit('error', message=t('msg_not_processed', sess.language), detail=detail)


def _run_greeting(sess: Session):
    try:
        sess.emit('stage', name='preparing')
        sess.review_words = _retrieve_review_words(sess)
        sess.hint_translations = translate_hints(sess.tasks, sess.language)
        sess.emit('stage', name='greeting')
        system_prompt = build_greeting_system_prompt(
            sess.scenario, sess.current_task, language=sess.language,
            mood=sess.mood, complication=sess.complication,
            review_words=sess.review_words)
        greeting = produce_greeting_turn(
            [{'role': 'user', 'content': 'Hello.'}], system_prompt,
            speaker=sess.scenario.speaker, max_sentences=GREETING_MAX_SENTENCES,
            actor_fn=call_actor, language=sess.language)
        _deliver_actor_turn(sess, greeting)
    except Exception as exc:
        _report(sess, exc)
    sess.set_state(AWAITING_INPUT)
    _warm_next_turn(sess)


def _explain_opening(sess: Session):
    """Explain mode opens with no model call: there is nothing for the
    listener to react to yet, and the topic and its points are authored."""
    sess.say(t('explain_opening', sess.language, topic=sess.topic.title(sess.language)),
             speaker=sess.topic.listener_short(sess.language))
    sess.set_state(AWAITING_INPUT)
    _warm_next_turn(sess)


def _run_scene_turn(sess: Session):
    """After a skip, the NPC sets up the next task (BL-22 / BUG-030):
    otherwise it carries on with the one the learner just gave up on while
    the objective on screen has moved on."""
    try:
        sess.emit('stage', name='replying')
        system = build_actor_system_prompt(
            sess.scenario, sess.current_task, language=sess.language, mood=sess.mood,
            complication=sess.complication, review_words=sess.review_words)
        raw = _traced('actor', produce_actor_turn, actor_view(sess.messages), system,
                      speaker=sess.scenario.speaker, max_sentences=ACTOR_MAX_SENTENCES,
                      actor_fn=call_actor, language=sess.language)
        _deliver_actor_turn(sess, raw)
    except Exception as exc:
        _report(sess, exc)
    _warm_next_turn(sess)


def _listen_through_points(sess: Session, point: str, text: str) -> str:
    """Grant the current point and every following one the message also
    made clear; return what the listener says.

    Playtest 2026-09-27: one message covering two points was credited one,
    and the listener — asked only for a verdict — said nothing. Walking on to
    the next point fixes both: it is granted if already covered, and if not,
    the listener's question about it is the natural reply.

    A following point is judged on this message ALONE: with the conversation
    as history the model granted "why you started" to "I play every Tuesday
    and Friday" 3/3; on the message alone it scored 12/12. The history-free
    check can only under-grant, and a missed point is asked about next turn.
    """
    history = recent_history(sess.messages[:-1])
    lenient = True                   # only the point the learner was asked about
    said = ''
    while point is not None:
        clear, said = _traced('listen', listen, sess.topic, point, text, sess.language,
                              history if lenient else None, lenient=lenient)
        if not clear:
            break
        sess.emit('task_result', done=True, index=sess.task_idx)
        sess.task_idx += 1
        sess.tasks_done += 1
        point, lenient = sess.current_task, False
    return said or t('explain_ack', sess.language)


def _run_explain_turn(sess: Session, text: str):
    """listen (once per point it walks through) -> coach. The listener's
    verdict IS the grading, so there is no task judge here."""
    try:
        point = sess.current_task
        if point is None:
            _finish(sess)
            return
        sess.emit('stage', name='replying')
        said = _listen_through_points(sess, point, text)
        sess.say(said, speaker=sess.topic.listener_short(sess.language))
        sess.emit('stage', name='coaching')
        feedback = _traced('coach', call_coach, text, sess.language)
        _after_coach(sess, text, feedback)
    except Exception as exc:
        _report(sess, exc)
        sess.set_state(AWAITING_INPUT)
    _warm_next_turn(sess)


_HIRAGANA = re.compile(r'[\u3041-\u3096]')
_LATIN_WORD = re.compile('[A-Za-z]{3,}')


def _card_for_history(parsed, spoken: str, language: str):
    """The vocabulary block to keep beside the NPC line for the actor's
    history (actor_view), or None.

    The actor copies its history (#38): a card handed back in English made
    every later Japanese card "X means ...". So only a card written the way
    the next one should be goes back — both prose fields in the language
    being practised (Japanese: hiragana in each, no Latin word, not read as
    Chinese; English: no CJK), cleaned like the line, and about a word the
    NPC actually said.
    """
    if not parsed:
        return None
    word, exp, enc = (sanitize(x).strip() for x in parsed)
    if not (word and exp and enc) or _not_in_dialogue(word, spoken, language):
        return None
    if language == 'Japanese':
        if (not (_HIRAGANA.search(exp) and _HIRAGANA.search(enc)) or _LATIN_WORD.search(exp + enc)
                or reads_as_chinese(exp)):
            return None
    elif JAPANESE_SCRIPT.search(exp + enc):
        return None
    return f'<vocab>\nword: {word}\nexplanation: {exp}\nencourage: {enc}\n</vocab>'


def _deliver_actor_turn(sess: Session, raw: str) -> Optional[str]:
    """Split one actor turn into what the learner sees, and log the card.
    Returns the word the card taught for the first time this session, if any."""
    spoken, vocab_box = extract_and_format_vocab(raw, sess.language, sess.scenario)
    parsed = parse_vocab(raw)
    card = _card_for_history(parsed, spoken, sess.language)
    sess.say(spoken, card=card, speaker=speaker_label(sess.scenario.speaker, sess.language))
    if vocab_box and parsed:
        word = parsed[0].strip()
        repeat = word.lower() in sess.taught_words
        sess.taught_words.setdefault(word.lower(), word)
        sess.emit('vocab', box=vocab_box, word=word, repeat=repeat)
        with _database() as conn:
            db.log_vocab(conn, sess.user_id, sess.language,
                         parsed[0], parsed[1], sess.scenario.name,
                         embedding=retrieval.embed_vocab(parsed[0], parsed[1]))
        return None if repeat else word
    return None


def _advance_after_judge(sess: Session, is_done: bool, hint: Optional[str]):
    task = sess.current_task
    now = db._utcnow()
    if is_done:
        sess.emit('task_result', done=True, index=sess.task_idx)
        with _database() as conn:
            db.log_task(conn, sess.db_session_id, sess.scenario.name,
                        sess.user_id, sess.task_idx, task.goal, task.done_when,
                        task.difficulty, task.phase, 'completed',
                        sess.attempts + 1, now, now)
            if sess.review_keys:
                db.log_mistake_review(conn, sess.user_id, sess.language,
                                      sess.review_keys[sess.task_idx], sess.db_session_id)
        sess.tasks_done += 1
        sess.task_idx += 1
        sess.attempts = 0
        sess.task_start_idx = len(sess.messages)
        return
    sess.attempts += 1
    if sess.attempts >= MAX_TASK_ATTEMPTS:
        with _database() as conn:
            db.log_task(conn, sess.db_session_id, sess.scenario.name,
                        sess.user_id, sess.task_idx, task.goal, task.done_when,
                        task.difficulty, task.phase, 'failed', sess.attempts,
                        now, now)
        goal = sess.hint_translations.get((sess.task_idx, task.goal), task.goal)
        sess.emit('task_result', done=False, moved_on=True, index=sess.task_idx,
                  attempts=sess.attempts, goal=goal)
        # Counted with the skips: the summary line is "Skipped/Failed", and a
        # session where every task ran out of attempts once reported zero of
        # everything (OPEN-25).
        sess.tasks_skipped += 1
        sess.task_idx += 1
        sess.attempts = 0
        sess.task_start_idx = len(sess.messages)
    else:
        # The judge's note says what was missing; the task's strategy hint
        # says how to get there.
        strategy = (sess.hint_translations.get((sess.task_idx, task.hint), task.hint)
                    if task.hint else None)
        sess.emit('task_result', done=False, moved_on=False,
                  attempts=sess.attempts, max_attempts=MAX_TASK_ATTEMPTS,
                  hint=hint, strategy=strategy)


# LANGUAGE_COACH_TRACE=<path> appends, per NPC turn, what stream_actor did with
# every sentence it produced (shown / rejected and why / salvage appended) as
# one JSON line. Off by default (OPEN-52).
_TRACE_FILE = os.environ.get('LANGUAGE_COACH_TRACE', '')


def _write_trace(sess: Session, trace) -> None:
    if not trace:
        return
    try:
        with open(_TRACE_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'scenario': sess.scenario.name, 'language': sess.language,
                                'trace': trace}, ensure_ascii=False) + '\n')
    except OSError:
        pass


def _credit_vocab_use(sess: Session, text: str, feedback: str,
                      taught_now: Optional[str] = None) -> list:
    """Count each taught word the learner just used as one practice.

    This is what moves a word toward learned (times_correct >= 3); without it
    every word stays due forever. A word inside a phrase the coach just
    marked ❌ is not credited: using it wrongly is not practice. Nor is
    `taught_now`, the word the NPC's reply to THIS message introduced — the
    learner wrote before seeing it. Never raises.
    """
    try:
        wrong = ' '.join(said for said, _ in _CORRECTION_BULLET.findall(feedback)).lower()
        with _database() as conn:
            due = db.get_vocab_for_review(conn, sess.user_id, sess.language, limit=None)
            counts = {row['word']: row['times_correct'] for row in due}
            fresh = (taught_now or '').lower()
            used = [w for w in words_used(text, list(counts), sess.language)
                    if w.lower() not in wrong and w.lower() != fresh]
            for w in used:
                db.mark_vocab_reviewed(conn, sess.user_id, sess.language, w, correct=True)
        return [{'word': w, 'count': counts[w] + 1} for w in used]
    except Exception:
        return []


def _record_mistakes(sess: Session, feedback: str) -> list:
    """Persist this turn's corrections so a repeat can be recognised later;
    return which of them the learner has made before. Never raises: a
    logging failure must not cost a turn that already happened."""
    try:
        name = (sess.topic.title(sess.language) if sess.explaining
                else sess.scenario.name)
        with _database() as conn:
            ids = db.log_mistakes(conn, sess.user_id, sess.language,
                                  sess.db_session_id, name, feedback)
            return db.repeats_among(conn, ids)
    except Exception:
        return []


def _retrieve_review_words(sess: Session, limit: int = 3) -> list:
    """Due words that fit the scenario the learner just started.

    The scenario — its place, role and first few goals — is the query; the
    learner's own unpractised vocabulary is the corpus. No embedder, no
    vectors, or an embedder that throws all end at least-recently-seen. A
    session must never die for a spaced-repetition nicety.
    """
    if sess.explaining:          # no scenario to be the query, no NPC to offer words to
        return []
    try:
        goals = [task.goal for task in sess.tasks[:5]]
        query = retrieval.embed(retrieval.scenario_query(
            sess.scenario.place, sess.scenario.role, goals))
    except Exception:
        query = None
    try:
        with _database() as conn:
            rows = db.due_words_for(conn, sess.user_id, sess.language,
                                    query_vector=query, limit=limit)
        return [r['word'] for r in rows]
    except Exception:
        return []


def _after_coach(sess: Session, text: str, feedback: str, taught_now: Optional[str] = None):
    """Show the coach's verdict, record it, credit vocabulary, and open the
    drill when there is something to retype."""
    repeats = _record_mistakes(sess, feedback)
    targets = [] if is_clean_verdict(feedback, sess.language) else correction_targets(feedback)
    sess.emit('coach', text=feedback, repeats=repeats)
    used = _credit_vocab_use(sess, text, feedback, taught_now)
    if used:
        sess.emit('vocab_used', words=used)
    if targets:
        sess.drill_targets = list(targets)
        sess.set_state(DRILL)
    elif sess.current_task is None:
        _finish(sess)
    else:
        sess.set_state(AWAITING_INPUT)


def _whats_next(conn, sess: Session) -> dict:
    """The earned facts the summary ends on: how far this scenario is from
    its next mastery rung (an explain topic has no ladder), how many words
    wait to be practised, and the mistakes that keep coming back."""
    progress = (None if sess.explaining
                else db.next_rank_hint(conn, sess.user_id, sess.scenario.name))
    return dict(progress=progress,
                words_due=db.count_vocab_due(conn, sess.user_id, sess.language),
                repeats=db.repeated_mistakes(conn, sess.user_id, sess.language, limit=2))


def _finish(sess: Session):
    """End the session with a summary — by finishing the last task, or by
    quitting early, which reaches the same summary."""
    with _database() as conn:
        db.finish_session(conn, sess.db_session_id, sess.tasks_done, sess.tasks_skipped)
        nxt = _whats_next(conn, sess)
    sess.set_state(FINISHED)
    sess.emit('finished', tasks_done=sess.tasks_done, tasks_total=sess.total_tasks,
              tasks_missed=sess.tasks_skipped, **nxt)


def _run_turn(sess: Session, text: str):
    """judge -> actor -> coach.

    The judge precedes the actor because the actor's system prompt depends
    on its verdict (a completed task steers the NPC toward the next one); the
    coach follows the actor so the NPC's reply reaches the learner first.
    """
    try:
        task = sess.current_task
        if task is None:
            # reached when an error after the last task left the input open
            _finish(sess)
            return

        sess.emit('stage', name='judging')
        vocab_targets = (getattr(task, 'vocab_translations', {}) or {}).get(sess.language)
        is_done, hint = _traced('judge', evaluate_task, text, task.done_when,
                                sess.messages[sess.task_start_idx:],
                                sess.language, vocab_targets)
        _advance_after_judge(sess, is_done, hint)

        actor_system = build_actor_system_prompt(
            sess.scenario, sess.current_task or WRAP_UP, language=sess.language,
            mood=sess.mood, complication=sess.complication,
            review_words=sess.review_words)

        sess.emit('stage', name='replying')
        trace = [] if _TRACE_FILE else None
        raw = _traced('actor', produce_actor_turn,
                      actor_view(sess.messages), actor_system,
                      speaker=sess.scenario.speaker, max_sentences=ACTOR_MAX_SENTENCES,
                      actor_fn=stream_actor,
                      callback=lambda s: sess.emit('sentence', text=s),
                      language=sess.language, **({'trace': trace} if trace is not None else {}))
        _write_trace(sess, trace)
        taught_now = _deliver_actor_turn(sess, raw)

        sess.emit('stage', name='coaching')
        feedback = _traced('coach', call_coach, text, sess.language, situation=_situation(sess))
        _after_coach(sess, text, feedback, taught_now)
    except Exception as exc:
        _report(sess, exc)
        sess.set_state(AWAITING_INPUT)
    _warm_next_turn(sess)


# ── warming the next turn's prompts (client.prefill) ────────────────────────
# While the learner reads and types, the model is idle. Everything in the next
# turn's prompts except the learner's message is already known, so it is run
# into the prompt caches now and the turn only processes what was typed. The
# first turn gains most: its coach prompts (~3,800 tokens) were cold.

def _situation(sess: Session):
    return describe_situation(sess.scenario.place, sess.scenario.role, sess.scenario.speaker)


def _warm_next_turn(sess: Session):
    if sess.state not in (AWAITING_INPUT, DRILL):
        return
    jobs = [([{'role': 'system', 'content': coach_system(sess.language, None)},
              {'role': 'user', 'content': ''}], 'coach')]
    if not sess.explaining:
        jobs.append(([{'role': 'system', 'content': coach_system(sess.language, _situation(sess))},
                      {'role': 'user', 'content': ''}], 'coach_situation'))
    prefill(jobs)


# ── tracing (app/telemetry.py) ──────────────────────────────────────────────
# Each turn is one trace with a child span per stage. The model functions are
# still looked up on this module at call time, so tests that patch them work.

def _traced(stage: str, fn, *args, **kwargs):
    with tracer.start_as_current_span(stage):
        return fn(*args, **kwargs)


def _turn_attributes(sess: Session) -> dict:
    return {'coach.language': sess.language,
            'coach.kind': 'explain' if sess.explaining else 'scenario',
            'coach.scenario': (sess.topic.title(sess.language) if sess.explaining
                               else sess.scenario.name)}


def open_session(sess: Session):
    """The first turn: the NPC's greeting, or the listener's question."""
    if sess.explaining:
        _explain_opening(sess)
        return
    with tracer.start_as_current_span('greeting', attributes=_turn_attributes(sess)):
        _run_greeting(sess)


def after_skip(sess: Session):
    """The NPC's turn after a skip, one trace like any other turn."""
    stop_prefill()
    with tracer.start_as_current_span('turn', attributes=_turn_attributes(sess)):
        _run_scene_turn(sess)


def take_turn(sess: Session, text: str):
    """One learner message, already sanitized and non-empty."""
    stop_prefill()
    sess.messages.append({'role': 'user', 'content': text})
    sess.set_state(BUSY)
    with tracer.start_as_current_span('turn', attributes=_turn_attributes(sess)):
        if sess.explaining:
            _run_explain_turn(sess, text)
        else:
            _run_turn(sess, text)
