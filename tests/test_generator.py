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


if __name__ == '__main__':
    pytest.main(['-v', __file__])
