"""The JSON the page is sent: task list, banner, what-next, and error reports.
"""
from __future__ import annotations

from .. import db
from ..i18n import mood_label, scenario_name, scenario_place, speaker_label, t
from ..llm import MLX_ERRORS, describe_llm_error
from .state import (Session, _database)


def _report(sess: Session, exc: Exception):
    """What the learner is told when a turn fails.

    The raw exception used to go straight into the conversation — the learner
    saw "Failed to load model: [Errno 2] No such file or directory:
    '/Users/…/huggingface/hub/…'" sitting where the NPC's reply belongs. That
    leaks local paths and tells them nothing they can act on. `describe_llm_error`
    already exists for this and the CLI has always used it.
    """
    if isinstance(exc, MLX_ERRORS):
        detail = describe_llm_error(exc)
    else:
        detail = exc.__class__.__name__
    sess.emit('error', message=t('msg_not_processed', sess.language), detail=detail)


def _task_payload(sess: Session):
    # In explain mode the checklist is the points the listener has to end up
    # understanding, which are authored per language and need no translation.
    if sess.explaining:
        return [{'index': i, 'goal': point,
                 'done': i < sess.task_idx and i not in sess.missed_idx,
                 'skipped': i in sess.missed_idx,
                 'current': i == sess.task_idx}
                for i, point in enumerate(sess.points)]
    return [{
        'index': i,
        'goal': sess.hint_translations.get((i, task.goal), task.goal),
        'done': i < sess.task_idx and i not in sess.missed_idx,
        'skipped': i in sess.missed_idx,
        'current': i == sess.task_idx,
    } for i, task in enumerate(sess.tasks)]


def _header(sess: Session) -> dict:
    """The banner fields, built from the Session rather than from whatever the
    creating request happened to have in hand — so /api/session/{sid} can
    rebuild a reloaded page with exactly what the first response carried."""
    if sess.explaining:
        return {'language': sess.language, 'mode': 'explain',
                'scenario': sess.topic.title(sess.language),
                'place': sess.topic.title(sess.language),
                'speaker': sess.topic.listener_short(sess.language),
                'total_tasks': len(sess.points),
                'mood': '', 'complication': None}
    return {'language': sess.language, 'mode': 'scenario',
            'scenario': scenario_name(sess.scenario, sess.language),
            'place': scenario_place(sess.scenario, sess.language),
            'speaker': speaker_label(sess.scenario.speaker, sess.language),
            'total_tasks': len(sess.tasks),
            # The actor is given one of six moods and sometimes a
            # complication, and neither ever reached the learner — so every
            # scenario read the same however differently the NPC was actually
            # behaving.
            'mood': mood_label(sess.mood, sess.language),
            'complication': sess.complication}


def _whats_next(conn, sess: Session) -> dict:
    """The two earned facts the summary ends on, wherever it is shown from.

    There are three ways to reach a summary — finishing the last task, ending
    early, and reloading onto a session that already finished — and each one
    built its own payload. This is the one place they all read, so the end
    card cannot silently lose a line on the path that is used most.

    An explain topic has no mastery ladder, so it gets no rung.
    """
    progress = (None if sess.topic is not None
                else db.next_rank_hint(conn, sess.user_id, sess.scenario.name))
    return dict(progress=progress,
                words_due=db.count_vocab_due(conn, sess.user_id, sess.language),
                repeats=db.repeated_mistakes(conn, sess.user_id, sess.language,
                                             limit=2))


def _resume_next(sess: Session) -> dict:
    """_whats_next for the resume path, which has no open connection of its own."""
    with _database() as conn:
        return _whats_next(conn, sess)
