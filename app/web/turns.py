"""Everything that calls the model, one worker per kind of turn.

Greeting, learner turn (judge -> actor -> coach), and the explain-mode pair.
Each runs on its own thread and reports through Session.emit(). Tests patch
the model functions on THIS module (app.web.turns.<name>), where they are
looked up.
"""
from __future__ import annotations

import json
import os
from typing import Optional
from .. import db
from .. import retrieval
from ..coach.verdict import _CORRECTION_BULLET
from ..telemetry import tracer
from ..vocab_card import extract_and_format_vocab, parse_vocab, words_used
from ..coach import (call_coach, correction_targets, describe_situation,
                     is_clean_verdict)
from ..explain import listen
from ..i18n import speaker_label, t
from ..judge import evaluate_task
from ..llm import call_actor, stream_actor, translate_hints
from ..session import (ACTOR_MAX_SENTENCES, GREETING_MAX_SENTENCES,
                      build_actor_system_prompt, build_greeting_system_prompt,
                      produce_actor_turn, produce_greeting_turn, recent_history)
from .state import (AWAITING_INPUT, DRILL, FINISHED, MAX_TASK_ATTEMPTS, Session, _database)
from .payloads import (_report, _task_payload, _whats_next)


def _run_greeting(sess: Session):
    """First turn. Runs off the request thread so the browser can open the
    stream and watch it arrive rather than waiting on a ~10s response."""
    try:
        sess.emit('stage', name='preparing')
        sess.review_words = _retrieve_review_words(sess)
        sess.hint_translations = translate_hints(sess.tasks, sess.language)
        sess.emit('stage', name='greeting')
        sess.emit('tasks', tasks=_task_payload(sess))
        system_prompt = build_greeting_system_prompt(
            sess.scenario, sess.tasks[0], language=sess.language,
            mood=sess.mood, complication=sess.complication,
            review_words=sess.review_words)
        greeting = produce_greeting_turn(
            [{'role': 'user', 'content': 'Hello.'}], system_prompt,
            speaker=sess.scenario.speaker, max_sentences=GREETING_MAX_SENTENCES,
            actor_fn=call_actor, language=sess.language)
        _deliver_actor_turn(sess, greeting)
        sess.set_state(AWAITING_INPUT)
    except Exception as exc:  # surfaced to the learner rather than swallowed
        _report(sess, exc)
        sess.set_state(AWAITING_INPUT)


def _explain_opening_worker(sess: Session):
    """Explain mode opens with no model call at all.

    There is nothing for the listener to react to yet, and the topic and its
    points are authored text. So the learner sees the screen immediately
    instead of waiting ~10s for a greeting that could only be small talk.
    """
    try:
        sess.emit('tasks', tasks=_task_payload(sess))
        sess.emit('npc', text=t('explain_opening', sess.language,
                                topic=sess.topic.title(sess.language)),
                  speaker=sess.topic.listener_short(sess.language))
        sess.set_state(AWAITING_INPUT)
    except Exception as exc:
        _report(sess, exc)
        sess.set_state(AWAITING_INPUT)


def _listen_through_points(sess: Session, point: str, text: str) -> str:
    """Grant the current point and every following one the message also
    made clear; return what the listener says.

    Playtest 2026-09-27: "It is played by two or four people, and you win
    when you get 21 points first" covered two points and was credited one,
    and the listener said nothing at all — asked only for a verdict, the
    model answers a bare CLEAR. Walking on to the next point fixes both: it
    is granted if already covered, and if not, the listener's question about
    it is the natural reply ("So how do you win?").

    A following point is judged on this message ALONE. With the conversation
    as history the model granted "why you started" to "I play every Tuesday
    and Friday" 3/3; on the message alone it scored 12/12 on six covered and
    uncovered cases. The history-free check can only under-grant, and a point
    it misses is asked about next turn — with history — as before.
    """
    history = recent_history(sess.messages[:-1])
    lenient = True                   # only the point the learner was asked about
    said = ''
    while point is not None:
        clear, said = _traced('listen', listen, sess.topic, point, text, sess.language,
                              history if lenient else None, lenient=lenient)
        if not clear:
            break
        sess.task_idx += 1
        sess.tasks_done += 1
        point, lenient = sess.current_task, False
    return said or t('explain_ack', sess.language)


def _run_explain_turn(sess: Session, text: str):
    """listen (once per point it walks through) -> coach.

    The listener's verdict replaces the task judge: deciding whether the point
    landed IS the grading, so there is nothing left for a judge to do.
    """
    try:
        point = sess.current_task
        if point is None:
            _finish(sess)
            return

        sess.emit('stage', name='replying')
        said = _listen_through_points(sess, point, text)
        sess.messages.append({'role': 'assistant', 'content': said})
        sess.emit('npc', text=said, speaker=sess.topic.listener_short(sess.language))
        sess.emit('tasks', tasks=_task_payload(sess))

        sess.emit('stage', name='coaching')
        feedback = _traced('coach', call_coach, text, sess.language)
        repeats = _record_mistakes(sess, feedback)
        targets = [] if is_clean_verdict(feedback, sess.language) else correction_targets(feedback)
        sess.emit('coach', text=feedback, clean=not targets, targets=targets,
                  repeats=repeats)
        used = _credit_vocab_use(sess, text, feedback)
        if used:
            sess.emit('vocab_used', words=used)

        if targets:
            sess.drill_targets = list(targets)
            sess.emit('drill', target=targets[0], remaining=len(targets))
            sess.set_state(DRILL)
        elif sess.current_task is None:
            _finish(sess)
        else:
            sess.set_state(AWAITING_INPUT)
    except Exception as exc:
        _report(sess, exc)
        sess.set_state(AWAITING_INPUT)


def _deliver_actor_turn(sess: Session, raw: str) -> Optional[str]:
    """Split one actor turn into what the learner sees, and log the card.
    Returns the word the card taught for the first time this session, if any."""
    spoken, vocab_box = extract_and_format_vocab(raw, sess.language, sess.scenario)
    sess.messages.append({'role': 'assistant', 'content': spoken})
    sess.emit('npc', text=spoken,
              speaker=speaker_label(sess.scenario.speaker, sess.language))
    parsed = parse_vocab(raw)
    if vocab_box and parsed:
        word = parsed[0].strip()
        # The card still goes into the transcript on a repeat — the NPC really
        # did teach it again, and hiding that would misrepresent the
        # conversation. It is the collected list and the word count that must
        # not double.
        repeat = word.lower() in sess.taught_words
        sess.taught_words.setdefault(word.lower(), word)
        sess.emit('vocab', word=word, explanation=parsed[1].strip(),
                  encourage=parsed[2].strip(), repeat=repeat)
        with _database() as conn:
            db.log_vocab(conn, sess.user_id, sess.language,
                         parsed[0], parsed[1], sess.scenario.name,
                         embedding=retrieval.embed_vocab(parsed[0], parsed[1]))
        return None if repeat else word
    return None


def _advance_after_judge(sess: Session, is_done: bool, hint: Optional[str]):
    """Mirrors the CLI's task bookkeeping, including counting a FAILED task —
    which was missed for the whole life of the CLI (OPEN-25)."""
    task = sess.current_task
    now = db._utcnow()
    if is_done:
        sess.emit('task_result', done=True, index=sess.task_idx)
        with _database() as conn:
            db.log_task(conn, sess.db_session_id, sess.scenario.name,
                        sess.user_id, sess.task_idx, task.goal, task.done_when,
                        task.difficulty, task.phase, 'completed',
                        sess.attempts + 1, now, now)
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
        sess.tasks_skipped += 1
        sess.missed_idx.add(sess.task_idx)
        sess.task_idx += 1
        sess.attempts = 0
        sess.task_start_idx = len(sess.messages)
    else:
        # The task's own strategy hint, as the CLI prints it after a miss.
        # The judge's note says what was missing; this says how to get there.
        task = sess.current_task
        strategy = (sess.hint_translations.get((sess.task_idx, task.hint), task.hint)
                    if task is not None and task.hint else None)
        sess.emit('task_result', done=False, moved_on=False,
                  attempts=sess.attempts, max_attempts=MAX_TASK_ATTEMPTS,
                  hint=hint, strategy=strategy)


# LANGUAGE_COACH_TRACE=<path> appends, per NPC turn, what stream_actor did with
# every sentence it produced (shown / rejected and why / salvage appended) as
# one JSON line. Off by default. It exists to answer OPEN-52 from real play:
# which sentences a turn loses, and why the canned question gets appended.
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

    This is what moves a word toward learned (times_correct >= 3) now that
    the CLI's warm-up quiz is gone — without it every word stays due forever.
    A word inside a phrase the coach just marked ❌ is not credited: using it
    wrongly is not practice. Returns [{word, count}] for the page; never
    raises, a turn is not lost to a bookkeeping error.

    `taught_now` is the word the NPC's reply to THIS message introduced. The
    learner wrote before seeing it, so it is not practice of what was taught:
    a playtest turn used ヘッドジョイント, the NPC then made it the card, and
    the transcript said "used 1/3" beneath the card that introduced it.
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
    """Persist this turn's corrections so a repeat can be recognised later.

    Every correction the coach has ever made was shown once and then thrown
    away, which is why the app could answer "how many words have you been
    taught" but not "are you still making the same mistake" — the question a
    learner actually has. Returns which of this turn's corrections the
    learner has made before, for the coach event to flag.

    Never raises. A logging failure must not cost a turn that already
    happened; it returns no repeats instead.
    """
    try:
        # An explain session has no scenario at all — `scenario` is None and
        # the topic carries the title — so reading `.name` unconditionally
        # would raise here and the except below would swallow it, leaving
        # explain mode silently unlogged.
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
    learner's own unpractised vocabulary is the corpus. Everything here
    degrades rather than fails: no embedder, no vectors, or an embedder that
    throws all end at least-recently-seen, which is what the app did before
    retrieval existed. A session must never die for a spaced-repetition
    nicety.
    """
    if sess.topic is not None:
        return []                       # explain mode has no scenario to fit
    try:
        from .. import retrieval
        goals = [t.goal for t in sess.tasks[:5]]
        query = retrieval.embed(retrieval.scenario_query(
            sess.scenario.place, sess.scenario.role, goals))
        with _database() as conn:
            rows = db.due_words_for(conn, sess.user_id, sess.language,
                                    query_vector=query, limit=limit)
        return [r['word'] for r in rows]
    except Exception:
        return []


def _finish(sess: Session):
    """End the session with a summary. A session that simply stops leaves the
    learner with no sense of having finished anything."""
    with _database() as conn:
        db.finish_session(conn, sess.db_session_id,
                          sess.tasks_done, sess.tasks_skipped)
        vocab = db.get_vocab_stats(conn, sess.user_id)
        nxt = _whats_next(conn, sess)
    sess.emit('finished',
              tasks_done=sess.tasks_done,
              tasks_total=len(sess.points) if sess.explaining else len(sess.tasks),
              tasks_missed=sess.tasks_skipped,
              words=(dict(vocab).get('learned_words') or 0)
                    + (dict(vocab).get('due_words') or 0),
              **nxt)
    sess.set_state(FINISHED)


def _run_turn(sess: Session, text: str):
    """judge -> actor -> coach, the same order as the CLI.

    The judge must precede the actor because the actor's system prompt depends
    on its verdict; the coach follows the actor so the NPC's reply reaches the
    learner first (7e312f0).
    """
    try:
        task = sess.current_task
        if task is None:
            sess.set_state(FINISHED)
            return

        # Each stage is announced as it starts. The turn takes 9-11s and the
        # server knows exactly which of the three calls it is in, so the wait
        # can be narrated truthfully instead of hidden behind one spinner.
        sess.emit('stage', name='judging')
        vocab_targets = (getattr(task, 'vocab_translations', {}) or {}).get(sess.language)
        is_done, hint = _traced('judge', evaluate_task, text, task.done_when,
                                      sess.messages[sess.task_start_idx:],
                                      sess.language, vocab_targets)
        _advance_after_judge(sess, is_done, hint)
        sess.emit('tasks', tasks=_task_payload(sess))

        if sess.current_task is None:
            actor_system = build_actor_system_prompt(
                sess.scenario,
                'The customer has just completed their final interaction. '
                'Wrap up the conversation naturally in 1-2 sentences.',
                language=sess.language, mood=sess.mood,
                complication=sess.complication,
                review_words=sess.review_words)
        else:
            actor_system = build_actor_system_prompt(
                sess.scenario, sess.current_task, language=sess.language,
                mood=sess.mood, complication=sess.complication,
                review_words=sess.review_words)

        sess.emit('stage', name='replying')
        chunks = []
        trace = [] if _TRACE_FILE else None
        raw = _traced('actor', produce_actor_turn,
            recent_history(sess.messages), actor_system,
            speaker=sess.scenario.speaker, max_sentences=ACTOR_MAX_SENTENCES,
            actor_fn=stream_actor,
            callback=lambda s: (chunks.append(s), sess.emit('sentence', text=s)),
            language=sess.language, **({'trace': trace} if trace is not None else {}))
        _write_trace(sess, trace)
        taught_now = _deliver_actor_turn(sess, raw)

        sess.emit('stage', name='coaching')
        situation = describe_situation(sess.scenario.place, sess.scenario.role,
                                       sess.scenario.speaker)
        feedback = _traced('coach', call_coach, text, sess.language, situation=situation)
        repeats = _record_mistakes(sess, feedback)
        targets = [] if is_clean_verdict(feedback, sess.language) else correction_targets(feedback)
        sess.emit('coach', text=feedback, clean=not targets, targets=targets,
                  repeats=repeats)
        used = _credit_vocab_use(sess, text, feedback, taught_now)
        if used:
            sess.emit('vocab_used', words=used)

        if targets:
            sess.drill_targets = list(targets)
            sess.emit('drill', target=targets[0], remaining=len(targets))
            sess.set_state(DRILL)
        elif sess.current_task is None:
            with _database() as conn:
                                  db.finish_session(conn, sess.db_session_id,
                                                    sess.tasks_done, sess.tasks_skipped)
            sess.set_state(FINISHED)
        else:
            sess.set_state(AWAITING_INPUT)
    except Exception as exc:
        _report(sess, exc)
        sess.set_state(AWAITING_INPUT)


# ── tracing (app/telemetry.py) ──────────────────────────────────────────────
# The workers the routes start are thin wrappers that open the turn's root
# span; each stage inside it is one child span. The model functions are still
# looked up on this module at call time, so tests that patch them still work.

def _traced(stage: str, fn, *args, **kwargs):
    with tracer.start_as_current_span(stage):
        return fn(*args, **kwargs)


def _turn_attributes(sess: Session) -> dict:
    return {'coach.language': sess.language,
            'coach.kind': 'explain' if sess.explaining else 'scenario',
            'coach.scenario': (sess.topic.title(sess.language) if sess.explaining
                               else sess.scenario.name)}


def _turn_worker(sess: Session, text: str):
    with tracer.start_as_current_span('turn', attributes=_turn_attributes(sess)):
        _run_turn(sess, text)


def _explain_turn_worker(sess: Session, text: str):
    with tracer.start_as_current_span('turn', attributes=_turn_attributes(sess)):
        _run_explain_turn(sess, text)


def _greeting_worker(sess: Session):
    with tracer.start_as_current_span('greeting', attributes=_turn_attributes(sess)):
        _run_greeting(sess)
