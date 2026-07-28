"""Tests for db.py and scenario_generator.py.

All tests use an in-memory SQLite DB and never touch the network.
"""

import json
import os
import sqlite3
import pytest
from unittest.mock import patch

import db
from app.scenarios.models import Task, Scenario
from app.scenarios import generator as scenario_generator
from app.scenarios.generator import (
    validate_scenario_json,
    parse_scenario_dict,
    _extract_json,
)


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
    assert 'dynamic_scenarios' in tables
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
# db.py — dynamic_scenarios
# ---------------------------------------------------------------------------

def test_save_and_load_scenario(conn):
    uid = db.get_or_create_user(conn, target_lang='English')
    data = _valid_scenario_dict()
    sid = db.save_scenario(conn, uid, 'train station', data, source='generated')
    assert sid >= 1

    scenario = db.load_scenario_as_object(conn, sid)
    assert isinstance(scenario, Scenario)
    assert scenario.name == 'Train Station'
    assert scenario.speaker == 'Clerk'
    assert len(scenario.tasks) == 15
    assert all(isinstance(t, Task) for t in scenario.tasks)
    assert scenario.tasks[0].goal == 'Task 0 goal'
    assert scenario.complications == ['printer is jammed', 'sold out of express tickets']


def test_load_nonexistent_scenario_raises(conn):
    with pytest.raises(ValueError, match="not found"):
        db.load_scenario_as_object(conn, 9999)


# ---------------------------------------------------------------------------
# db.py — sessions + task_logs
# ---------------------------------------------------------------------------

def test_create_session(conn):
    uid = db.get_or_create_user(conn, target_lang='English')
    sid = db.save_scenario(conn, uid, 'test', _valid_scenario_dict())
    sess = db.create_session(conn, uid, sid, 'English', 'chatty', None, 10)
    assert sess >= 1
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sess,)).fetchone()
    assert row['tasks_total'] == 10
    assert row['complication'] is None


def test_log_task_and_finish_session(conn):
    uid = db.get_or_create_user(conn, target_lang='English')
    sid = db.save_scenario(conn, uid, 'test', _valid_scenario_dict())
    sess = db.create_session(conn, uid, sid, 'English', 'chatty', None, 10)

    now = db._utcnow()
    db.log_task(conn, sess, sid, uid, 0, 'goal', 'done_when', 'standard',
                2, 'completed', 1, now, now)
    db.log_task(conn, sess, sid, uid, 1, 'goal2', 'done_when2', 'advanced',
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
# scenario_generator.py — validate_scenario_json
# ---------------------------------------------------------------------------

def test_validate_valid_scenario():
    data = _valid_scenario_dict()
    validate_scenario_json(data)  # should not raise


def test_validate_missing_name():
    data = _valid_scenario_dict()
    del data['name']
    with pytest.raises(ValueError, match="name"):
        validate_scenario_json(data)


def test_validate_empty_speaker():
    data = _valid_scenario_dict()
    data['speaker'] = ''
    with pytest.raises(ValueError, match="speaker"):
        validate_scenario_json(data)


def test_validate_too_few_tasks():
    data = _valid_scenario_dict(num_tasks=5, num_advanced=5)
    with pytest.raises(ValueError, match="at least 10 tasks"):
        validate_scenario_json(data)


def test_validate_bad_difficulty():
    data = _valid_scenario_dict()
    data['tasks'][0]['difficulty'] = 'expert'
    with pytest.raises(ValueError, match="invalid difficulty"):
        validate_scenario_json(data)


def test_validate_bad_done_when():
    data = _valid_scenario_dict()
    data['tasks'][0]['done_when'] = 'The student asked for help.'
    with pytest.raises(ValueError, match="done_when must start with 'Learner'"):
        validate_scenario_json(data)


def test_validate_too_few_advanced():
    data = _valid_scenario_dict(num_tasks=15, num_advanced=3)
    with pytest.raises(ValueError, match="at least 7 advanced"):
        validate_scenario_json(data)


def test_validate_missing_phase_1():
    data = _valid_scenario_dict()
    for t in data['tasks']:
        t['phase'] = 2
    with pytest.raises(ValueError, match="phase-1"):
        validate_scenario_json(data)


def test_validate_missing_phase_3():
    data = _valid_scenario_dict()
    for t in data['tasks']:
        if t['phase'] == 3:
            t['phase'] = 2
    with pytest.raises(ValueError, match="phase-3"):
        validate_scenario_json(data)


# ---------------------------------------------------------------------------
# scenario_generator.py — _extract_json
# ---------------------------------------------------------------------------

def test_extract_json_plain():
    raw = '{"name": "test"}'
    assert _extract_json(raw) == {'name': 'test'}


def test_extract_json_with_fences():
    raw = '```json\n{"name": "test"}\n```'
    assert _extract_json(raw) == {'name': 'test'}


def test_extract_json_with_think_tags():
    raw = '<think>reasoning</think>{"name": "test"}'
    assert _extract_json(raw) == {'name': 'test'}


def test_extract_json_with_preamble():
    raw = 'Here is the scenario:\n\n{"name": "test"}'
    assert _extract_json(raw) == {'name': 'test'}


def test_extract_json_no_json_raises():
    with pytest.raises(ValueError, match="No JSON"):
        _extract_json("no json here")


# ---------------------------------------------------------------------------
# scenario_generator.py — parse_scenario_dict
# ---------------------------------------------------------------------------

def test_parse_scenario_creates_objects():
    data = _valid_scenario_dict()
    scenario = parse_scenario_dict(data)
    assert isinstance(scenario, Scenario)
    assert scenario.name == 'Train Station'
    assert len(scenario.tasks) == 15
    assert scenario.tasks[0].difficulty == 'advanced'
    assert scenario.tasks[-1].phase == 3


def test_parse_scenario_integrates_with_session_builder():
    data = _valid_scenario_dict()
    scenario = parse_scenario_dict(data)
    tasks = scenario.get_session_tasks(num_tasks=10)
    assert len(tasks) == 10
    # Phase ordering must hold
    phases = [t.phase for t in tasks]
    assert phases == sorted(phases)
    # First phase-2 task must not be reactive
    first_mid = next((t for t in tasks if t.phase == 2), None)
    if first_mid is not None:
        assert not first_mid.reactive


# ---------------------------------------------------------------------------
# scenario_generator.py — generate_scenario (mocked LLM)
# ---------------------------------------------------------------------------

def test_generate_scenario_success(conn):
    uid = db.get_or_create_user(conn, target_lang='English')
    data = _valid_scenario_dict()
    fake_response = {'message': {'content': json.dumps(data)}}

    def fake_llm(messages, options):
        return fake_response

    scenario, sid = scenario_generator.generate_scenario(
        topic='train station', language='English', user_id=uid,
        conn=conn, llm_chat_fn=fake_llm
    )
    assert isinstance(scenario, Scenario)
    assert scenario.name == 'Train Station'
    assert sid >= 1

    # Verify it was persisted
    loaded = db.load_scenario_as_object(conn, sid)
    assert loaded.name == 'Train Station'


def test_generate_scenario_retries_on_bad_json(conn):
    uid = db.get_or_create_user(conn, target_lang='English')
    data = _valid_scenario_dict()
    call_count = [0]

    def flaky_llm(messages, options):
        call_count[0] += 1
        if call_count[0] <= 2:
            return {'message': {'content': 'not json at all'}}
        return {'message': {'content': json.dumps(data)}}

    scenario, sid = scenario_generator.generate_scenario(
        topic='test', language='English', user_id=uid,
        conn=conn, llm_chat_fn=flaky_llm
    )
    assert call_count[0] == 3  # failed twice, succeeded on third
    assert scenario.name == 'Train Station'


def test_generate_scenario_raises_after_max_attempts(conn):
    uid = db.get_or_create_user(conn, target_lang='English')

    def bad_llm(messages, options):
        return {'message': {'content': 'garbage'}}

    with pytest.raises(RuntimeError, match="Failed to generate"):
        scenario_generator.generate_scenario(
            topic='test', language='English', user_id=uid,
            conn=conn, llm_chat_fn=bad_llm, max_attempts=3
        )


if __name__ == '__main__':
    pytest.main(['-v', __file__])
