"""Tests for db.py.

All tests use an in-memory SQLite DB and never touch the network.
"""

import json
import os
import sqlite3
import pytest
from unittest.mock import patch

from app import db
from app.scenarios.models import Task, Scenario


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """In-memory DB with schema applied."""
    c = db.init_db(db_path=':memory:')
    yield c
    c.close()


def _valid_scenario_dict(num_tasks=15, num_advanced=10):
    """Build a minimal valid scenario dict."""
    tasks = []
    for i in range(num_tasks):
        is_advanced = i < num_advanced
        phase = 1 if i == 0 else (3 if i == num_tasks - 1 else 2)
        reactive = i >= 5 and i < 10
        tasks.append({
            'goal': f'Task {i} goal',
            'hint': f'Task {i} hint',
            'done_when': f'Learner did task {i}.',
            'difficulty': 'advanced' if is_advanced else 'standard',
            'phase': phase,
            'reactive': reactive,
            'scene_hint': '',
        })
    return {
        'name': 'Train Station',
        'place': 'A busy downtown train station',
        'role': 'You are a ticket clerk.',
        'speaker': 'Clerk',
        'complications': ['printer is jammed', 'sold out of express tickets'],
        'tasks': tasks,
    }


# ---------------------------------------------------------------------------
# db.py — init & tables
# ---------------------------------------------------------------------------

def test_db_init_creates_tables(conn):
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert 'user_profiles' in tables
    assert 'sessions' in tables
    assert 'task_logs' in tables


def test_db_foreign_keys_on(conn):
    val = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert val == 1


# ---------------------------------------------------------------------------
# db.py — user_profiles
# ---------------------------------------------------------------------------

def test_create_user(conn):
    uid = db.get_or_create_user(conn, display_name='alice', target_lang='Japanese')
    assert uid >= 1
    row = conn.execute("SELECT * FROM user_profiles WHERE id = ?", (uid,)).fetchone()
    assert row['display_name'] == 'alice'
    assert row['target_lang'] == 'Japanese'


def test_get_existing_user(conn):
    uid1 = db.get_or_create_user(conn, display_name='bob', target_lang='English')
    uid2 = db.get_or_create_user(conn, display_name='bob', target_lang='English')
    assert uid1 == uid2


def test_different_lang_creates_new_user(conn):
    uid1 = db.get_or_create_user(conn, display_name='charlie', target_lang='English')
    uid2 = db.get_or_create_user(conn, display_name='charlie', target_lang='Japanese')
    assert uid1 != uid2


# ---------------------------------------------------------------------------
# db.py — sessions + task_logs
# ---------------------------------------------------------------------------

def test_create_session(conn):
    uid = db.get_or_create_user(conn, target_lang='English')
    sess = db.create_session(conn, uid, 'Train Station', 'English', 'chatty', None, 10)
    assert sess >= 1
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sess,)).fetchone()
    assert row['tasks_total'] == 10
    assert row['complication'] is None


def test_log_task_and_finish_session(conn):
    uid = db.get_or_create_user(conn, target_lang='English')
    sess = db.create_session(conn, uid, 'Train Station', 'English', 'chatty', None, 10)

    now = db._utcnow()
    db.log_task(conn, sess, 'Train Station', uid, 0, 'goal', 'done_when', 'standard',
                2, 'completed', 1, now, now)
    db.log_task(conn, sess, 'Train Station', uid, 1, 'goal2', 'done_when2', 'advanced',
                2, 'skipped', 0, now, now)

    rows = conn.execute("SELECT * FROM task_logs WHERE session_id = ?",
                        (sess,)).fetchall()
    assert len(rows) == 2
    assert rows[0]['outcome'] == 'completed'
    assert rows[1]['outcome'] == 'skipped'

    db.finish_session(conn, sess, tasks_done=1, tasks_skipped=1)
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sess,)).fetchone()
    assert row['tasks_done'] == 1
    assert row['tasks_skipped'] == 1
    assert row['finished_at'] is not None


# ---------------------------------------------------------------------------
# db.py — legacy schema migration
# ---------------------------------------------------------------------------

LEGACY_SCHEMA = """
CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT, display_name TEXT, target_lang TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE dynamic_scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'generated', topic TEXT NOT NULL,
    name TEXT NOT NULL, place TEXT NOT NULL, role TEXT NOT NULL,
    speaker TEXT NOT NULL, complications TEXT NOT NULL DEFAULT '[]',
    tasks_json TEXT NOT NULL, model_used TEXT NOT NULL DEFAULT 'x',
    created_at TEXT NOT NULL);
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    scenario_id INTEGER NOT NULL REFERENCES dynamic_scenarios(id),
    language TEXT NOT NULL, mood TEXT NOT NULL, complication TEXT,
    tasks_total INTEGER NOT NULL, tasks_done INTEGER NOT NULL DEFAULT 0,
    tasks_skipped INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL,
    finished_at TEXT);
CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL,
    scenario_id INTEGER NOT NULL REFERENCES dynamic_scenarios(id),
    user_id INTEGER NOT NULL, task_index INTEGER NOT NULL, goal TEXT NOT NULL,
    done_when TEXT NOT NULL, difficulty TEXT NOT NULL, phase INTEGER NOT NULL,
    outcome TEXT NOT NULL, attempts_used INTEGER NOT NULL,
    started_at TEXT NOT NULL, finished_at TEXT NOT NULL);
"""


def test_legacy_schema_migrates_and_preserves_history(tmp_path):
    """A database written before dynamic_scenarios was removed must upgrade in
    place, keeping its sessions and task_logs and recovering scenario names."""
    path = str(tmp_path / 'legacy.db')
    raw = sqlite3.connect(path)
    raw.executescript(LEGACY_SCHEMA)
    now = '2026-01-01T00:00:00Z'
    raw.execute("INSERT INTO user_profiles VALUES (1,'pk','English',?,?)", (now, now))
    raw.execute("INSERT INTO dynamic_scenarios "
                "VALUES (7,1,'static','Coffee Shop','Coffee Shop','cafe','role',"
                "'Barista','[]','[]','m',?)", (now,))
    raw.execute("INSERT INTO sessions VALUES (1,1,7,'English','polite',NULL,10,3,0,?,?)",
                (now, now))
    raw.execute("INSERT INTO task_logs VALUES "
                "(1,1,7,1,0,'Order a latte','Learner ordered a latte.','standard',"
                "2,'completed',1,?,?)", (now, now))
    raw.commit()
    raw.close()

    conn = db.init_db(path)

    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert 'dynamic_scenarios' not in tables

    cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)")}
    assert 'scenario_name' in cols and 'scenario_id' not in cols

    # history survives, with the name recovered from the dropped table
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM task_logs").fetchone()[0] == 1
    assert conn.execute("SELECT scenario_name FROM sessions").fetchone()[0] == 'Coffee Shop'
    assert db.get_seen_task_goals(conn, 1, 'Coffee Shop') == {'Order a latte'}

    # writes work against the new schema
    sess = db.create_session(conn, 1, 'Coffee Shop', 'English', 'polite', None, 10)
    db.log_task(conn, sess, 'Coffee Shop', 1, 0, 'Ask for oat milk', 'dw',
                'standard', 2, 'completed', 1, now, now)
    assert db.get_seen_task_goals(conn, 1, 'Coffee Shop') == {'Order a latte', 'Ask for oat milk'}


def test_migration_is_idempotent(tmp_path):
    path = str(tmp_path / 'legacy2.db')
    raw = sqlite3.connect(path)
    raw.executescript(LEGACY_SCHEMA)
    raw.commit(); raw.close()
    db.init_db(path).close()
    conn = db.init_db(path)          # second run must be a no-op
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)")}
    assert 'scenario_name' in cols


if __name__ == '__main__':
    pytest.main(['-v', __file__])
