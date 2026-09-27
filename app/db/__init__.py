"""PostgreSQL persistence for practice sessions (psycopg 3 + pgvector).

Every function takes an explicit connection, so callers control the
transaction; init_db() opens one (creating the tables the first time a
process touches a schema) and returns it. Callers write db.<name> and never
import the modules below directly:

    connection.py  finding the server ($LANGUAGE_COACH_DSN), rows, schemas
    schema.py      the tables, as PostgreSQL DDL
    sessions.py    learner profiles and practice sessions
    progress.py    task results, per-scenario stats, mastery rank
    vocab.py       vocabulary taught, its spaced review, pgvector retrieval
    mistakes.py    coach corrections grouped by shape, for repeats
    common.py      the timestamp helper they all share

Moved from SQLite on 2026-09-27. A learner's old ~/.language-coach/sessions.db
comes across once with app/db/import_sqlite.py.
"""
import os
import threading
from pathlib import Path

from .common import _utcnow
from .connection import Row, connect, dsn, schema_for
from .schema import _SCHEMA, TABLES, backfill_explain_kind
from .sessions import (get_or_create_user, create_session, finish_session, abandon_stale_sessions)
from .progress import (log_task, _mastery_rank, next_rank_hint,
                       get_scenario_stats, get_all_scenario_stats,
                       get_all_topic_stats, get_overall_stats, get_vocab_stats,
                       get_seen_task_goals, get_unfinished_task_goals)
from .vocab import (log_vocab, due_words_for, count_vocab_due,
                    get_vocab_for_review, mark_vocab_reviewed)
from .mistakes import (_CARDINAL_WORDS, _SUBJECT_PRONOUNS, _PUNCT_RE,
                       _DIGIT_RUN_RE, _normalize_mistake_text, _mistake_key,
                       log_mistakes, repeats_among, repeated_mistakes)

DB_DIR = os.path.join(Path.home(), '.language-coach')


# (dsn, schema) pairs whose tables this process has already created. The web
# app opens a connection per unit of work, so the DDL runs once, not per turn.
_READY = set()
_CREATE_LOCK = threading.Lock()


def init_db(db_path: 'str | None' = None):
    """A connection to the app's schema, with its tables in place.

    `db_path` (or $LANGUAGE_COACH_DB) names a separate schema, as it named a
    separate SQLite file before; with neither, the learner's real data.
    """
    if db_path is None:
        db_path = os.environ.get('LANGUAGE_COACH_DB') or None
    schema = schema_for(db_path)
    conn = connect(schema)
    if (dsn(), schema) not in _READY:
        # Two threads (or processes) creating the same schema at once collide
        # even with IF NOT EXISTS — seen as a UniqueViolation on
        # pg_namespace when two web sessions started together. One creator
        # at a time: a lock per process, an advisory lock across processes.
        with _CREATE_LOCK:
            if (dsn(), schema) not in _READY:
                conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (schema,))
                conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                conn.execute(_SCHEMA)
                conn.commit()
                _READY.add((dsn(), schema))
    return conn


# Everything the single-file version exposed, so callers keep writing db.<name>.
__all__ = [
    '_utcnow',
    'Row',
    'connect',
    'dsn',
    'schema_for',
    '_SCHEMA',
    'TABLES',
    'backfill_explain_kind',
    'get_or_create_user',
    'create_session',
    'finish_session',
    'abandon_stale_sessions',
    'log_task',
    '_mastery_rank',
    'next_rank_hint',
    'get_scenario_stats',
    'get_all_scenario_stats',
    'get_all_topic_stats',
    'get_overall_stats',
    'get_vocab_stats',
    'get_seen_task_goals',
    'get_unfinished_task_goals',
    'log_vocab',
    'due_words_for',
    'count_vocab_due',
    'get_vocab_for_review',
    'mark_vocab_reviewed',
    '_CARDINAL_WORDS',
    '_SUBJECT_PRONOUNS',
    '_PUNCT_RE',
    '_DIGIT_RUN_RE',
    '_normalize_mistake_text',
    '_mistake_key',
    'log_mistakes',
    'repeats_among',
    'repeated_mistakes',
    'DB_DIR',
    'init_db',
]
