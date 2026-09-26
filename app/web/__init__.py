"""The web app: the language coach's only front end.

    state.py     a live session: state machine, registry, request bodies
    payloads.py  the JSON the page is sent
    turns.py     every call into the model, one worker per kind of turn
    routes.py    the HTTP API and serve()

The core below — session, llm, coach, judge, db, i18n — knows nothing about
this package. The model functions turns.py uses, and routes.py's
ORPHAN_GRACE_SECONDS, are deliberately NOT re-exported: a test must patch
them where they are looked up, and a name missing here makes a wrongly aimed
patch fail loudly instead of silently patching nothing.

Why a browser: coach feedback scrolls away in a terminal, a turn costs ~9-11s
so the NPC's reply streams sentence by sentence (SSE), and Japanese renders
properly. The turn order is judge -> actor -> coach: the actor's prompt
depends on the judge's verdict, and the coach runs last so the reply reaches
the learner first.
"""
from .state import (AWAITING_INPUT, BUSY, DRILL, FINISHED, Session, _database,
                    SESSIONS, MAX_TASK_ATTEMPTS, NewSession, Utterance,
                    _scenarios_for)
from .payloads import (_report, _task_payload, _header, _whats_next,
                       _resume_next)
from .turns import (_greeting_worker, _explain_opening_worker,
                    _explain_turn_worker, _deliver_actor_turn,
                    _advance_after_judge, _record_mistakes,
                    _retrieve_review_words, _finish, _turn_worker)
from .routes import (STATIC, app, index, list_scenarios, stats, strings,
                     resume_session, _random_scenario,
                     _create_explain_session, list_topics, create_session,
                     _close_orphan, stream, submit_turn, submit_drill,
                     skip_task, end_session, serve)

__all__ = [
    'AWAITING_INPUT',
    'BUSY',
    'DRILL',
    'FINISHED',
    'Session',
    '_database',
    'SESSIONS',
    'MAX_TASK_ATTEMPTS',
    'NewSession',
    'Utterance',
    '_scenarios_for',
    '_report',
    '_task_payload',
    '_header',
    '_whats_next',
    '_resume_next',
    '_greeting_worker',
    '_explain_opening_worker',
    '_explain_turn_worker',
    '_deliver_actor_turn',
    '_advance_after_judge',
    '_record_mistakes',
    '_retrieve_review_words',
    '_finish',
    '_turn_worker',
    'STATIC',
    'app',
    'index',
    'list_scenarios',
    'stats',
    'strings',
    'resume_session',
    '_random_scenario',
    '_create_explain_session',
    'list_topics',
    'create_session',
    '_close_orphan',
    'stream',
    'submit_turn',
    'submit_drill',
    'skip_task',
    'end_session',
    'serve',
]
