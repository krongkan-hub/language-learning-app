"""SQLite persistence for practice sessions. Standard library only.

Every function takes an explicit connection, so callers control the
transaction; init_db() opens the database (creating and migrating it if
needed) and returns one. Callers write db.<name> and never import the
modules below directly:

    schema.py    the tables, and migrations for an older database
    sessions.py  learner profiles and practice sessions
    progress.py  task results, per-scenario stats, mastery rank
    vocab.py     vocabulary taught, and its spaced review
    mistakes.py  coach corrections grouped by shape, for repeats
    common.py    the timestamp helper they all share

Location: ~/.language-coach/sessions.db, or $LANGUAGE_COACH_DB.
"""
import os
import sqlite3
from pathlib import Path

from .common import _utcnow
from .schema import (_SCHEMA, _migrate_legacy_schema, _migrate_add_kind_column,
                     _migrate_add_vocab_embedding, _migrate_add_mistakes_table)
from .sessions import (get_or_create_user, create_session, finish_session,
                       get_resumable_session, abandon_stale_sessions,
                       get_logged_goals_for_session)
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
DB_PATH = os.environ.get('LANGUAGE_COACH_DB', os.path.join(DB_DIR, 'sessions.db'))


def init_db(db_path: 'str | None' = None) -> sqlite3.Connection:
    """Create the DB directory + file if needed, apply schema, return a conn."""
    if db_path is None:
        db_path = os.environ.get('LANGUAGE_COACH_DB', os.path.join(DB_DIR, 'sessions.db'))
    db_dir = os.path.dirname(db_path)
    if db_dir:  # skip for ':memory:' or other in-memory paths
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    _migrate_legacy_schema(conn)
    _migrate_add_kind_column(conn)
    _migrate_add_vocab_embedding(conn)
    _migrate_add_mistakes_table(conn)
    conn.executescript(_SCHEMA)  # re-apply so indexes exist on rebuilt tables
    conn.commit()
    return conn


# Everything the single-file version exposed, so callers keep writing db.<name>.
__all__ = [
    '_utcnow',
    '_SCHEMA',
    '_migrate_legacy_schema',
    '_migrate_add_kind_column',
    '_migrate_add_vocab_embedding',
    '_migrate_add_mistakes_table',
    'get_or_create_user',
    'create_session',
    'finish_session',
    'get_resumable_session',
    'abandon_stale_sessions',
    'get_logged_goals_for_session',
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
    'DB_PATH',
    'init_db',
]
