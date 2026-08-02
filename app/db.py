"""Lightweight SQLite persistence for language-learning sessions.

Uses stdlib sqlite3 — no external dependencies.  All functions take an
explicit connection so callers control transaction scope.  The module-level
``init_db()`` creates/opens the database and returns a connection ready to use.

DB location: ``~/.language-coach/sessions.db``
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .scenarios.models import Task, Scenario

DB_DIR = os.path.join(Path.home(), '.language-coach')
DB_PATH = os.path.join(DB_DIR, 'sessions.db')

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS user_profiles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name  TEXT    NOT NULL DEFAULT 'learner',
    target_lang   TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    last_active   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS dynamic_scenarios (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES user_profiles(id),
    source         TEXT    NOT NULL DEFAULT 'generated',
    topic          TEXT    NOT NULL,
    name           TEXT    NOT NULL,
    place          TEXT    NOT NULL,
    role           TEXT    NOT NULL,
    speaker        TEXT    NOT NULL,
    complications  TEXT    NOT NULL DEFAULT '[]',
    tasks_json     TEXT    NOT NULL,
    model_used     TEXT    NOT NULL DEFAULT 'qwen3:8b',
    created_at     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ds_user  ON dynamic_scenarios(user_id);
CREATE INDEX IF NOT EXISTS idx_ds_topic ON dynamic_scenarios(topic);

CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES user_profiles(id),
    scenario_id   INTEGER NOT NULL REFERENCES dynamic_scenarios(id),
    language      TEXT    NOT NULL,
    mood          TEXT    NOT NULL,
    complication  TEXT,
    tasks_total   INTEGER NOT NULL,
    tasks_done    INTEGER NOT NULL DEFAULT 0,
    tasks_skipped INTEGER NOT NULL DEFAULT 0,
    started_at    TEXT    NOT NULL,
    finished_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_sess_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS task_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id),
    scenario_id     INTEGER NOT NULL REFERENCES dynamic_scenarios(id),
    user_id         INTEGER NOT NULL REFERENCES user_profiles(id),
    task_index      INTEGER NOT NULL,
    goal            TEXT    NOT NULL,
    done_when       TEXT    NOT NULL,
    difficulty      TEXT    NOT NULL,
    phase           INTEGER NOT NULL,
    outcome         TEXT    NOT NULL,
    attempts_used   INTEGER NOT NULL,
    started_at      TEXT    NOT NULL,
    finished_at     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tl_session ON task_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_tl_user    ON task_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_tl_outcome ON task_logs(outcome);
"""


def _utcnow() -> str:
    """ISO-8601 UTC timestamp, no microseconds."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Create the DB directory + file if needed, apply schema, return a conn."""
    db_dir = os.path.dirname(db_path)
    if db_dir:  # skip for ':memory:' or other in-memory paths
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


# ── user_profiles ────────────────────────────────────────────────────────────

def get_or_create_user(conn: sqlite3.Connection,
                       display_name: str = 'learner',
                       target_lang: str = 'English') -> int:
    """Return the user id, creating the row if it doesn't exist."""
    row = conn.execute(
        "SELECT id FROM user_profiles WHERE display_name = ? AND target_lang = ?",
        (display_name, target_lang)
    ).fetchone()
    if row:
        conn.execute("UPDATE user_profiles SET last_active = ? WHERE id = ?",
                     (_utcnow(), row['id']))
        conn.commit()
        return row['id']
    now = _utcnow()
    cur = conn.execute(
        "INSERT INTO user_profiles (display_name, target_lang, created_at, last_active) "
        "VALUES (?, ?, ?, ?)",
        (display_name, target_lang, now, now)
    )
    conn.commit()
    return cur.lastrowid


# ── dynamic_scenarios ────────────────────────────────────────────────────────

def save_scenario(conn: sqlite3.Connection, user_id: int, topic: str,
                  scenario_dict: dict, source: str = 'generated',
                  model: str = 'qwen3:8b') -> int:
    """Persist a scenario dict and return the row id."""
    cur = conn.execute(
        "INSERT INTO dynamic_scenarios "
        "(user_id, source, topic, name, place, role, speaker, "
        " complications, tasks_json, model_used, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id, source, topic,
            scenario_dict['name'],
            scenario_dict['place'],
            scenario_dict['role'],
            scenario_dict['speaker'],
            json.dumps(scenario_dict.get('complications', []), ensure_ascii=False),
            json.dumps(scenario_dict['tasks'], ensure_ascii=False),
            model, _utcnow()
        )
    )
    conn.commit()
    return cur.lastrowid


def load_scenario_as_object(conn: sqlite3.Connection,
                            scenario_id: int) -> Scenario:
    """Reconstruct a Scenario + Task objects from a stored row."""
    row = conn.execute(
        "SELECT * FROM dynamic_scenarios WHERE id = ?", (scenario_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"Scenario {scenario_id} not found")
    tasks_raw = json.loads(row['tasks_json'])
    tasks = [
        Task(
            goal=t['goal'],
            hint=t['hint'],
            done_when=t['done_when'],
            difficulty=t.get('difficulty', 'standard'),
            scene_hint=t.get('scene_hint', ''),
            phase=t.get('phase', 2),
            reactive=t.get('reactive', False),
        )
        for t in tasks_raw
    ]
    complications = json.loads(row['complications'])
    return Scenario(
        name=row['name'],
        place=row['place'],
        role=row['role'],
        speaker=row['speaker'],
        tasks=tasks,
        complications=complications,
    )


# ── sessions ─────────────────────────────────────────────────────────────────

def create_session(conn: sqlite3.Connection, user_id: int, scenario_id: int,
                   language: str, mood: str, complication: 'str | None',
                   tasks_total: int) -> int:
    """Start a new session and return its id."""
    cur = conn.execute(
        "INSERT INTO sessions "
        "(user_id, scenario_id, language, mood, complication, tasks_total, started_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, scenario_id, language, mood, complication, tasks_total, _utcnow())
    )
    conn.commit()
    return cur.lastrowid


def finish_session(conn: sqlite3.Connection, session_id: int,
                   tasks_done: int, tasks_skipped: int) -> None:
    """Mark a session as finished with final counts."""
    conn.execute(
        "UPDATE sessions SET tasks_done = ?, tasks_skipped = ?, finished_at = ? "
        "WHERE id = ?",
        (tasks_done, tasks_skipped, _utcnow(), session_id)
    )
    conn.commit()


# ── task_logs ────────────────────────────────────────────────────────────────

def log_task(conn: sqlite3.Connection, session_id: int, scenario_id: int,
             user_id: int, task_index: int, goal: str, done_when: str,
             difficulty: str, phase: int, outcome: str,
             attempts_used: int, started_at: str, finished_at: str) -> int:
    """Record the outcome of a single task attempt."""
    cur = conn.execute(
        "INSERT INTO task_logs "
        "(session_id, scenario_id, user_id, task_index, goal, done_when, "
        " difficulty, phase, outcome, attempts_used, started_at, finished_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (session_id, scenario_id, user_id, task_index, goal, done_when,
         difficulty, phase, outcome, attempts_used, started_at, finished_at)
    )
    conn.commit()
    return cur.lastrowid


def get_scenario_stats(conn: sqlite3.Connection, user_id: int, scenario_id: int) -> dict:
    """Return playthrough count, best completion rate, and mastery rank for a user and scenario."""
    cur = conn.execute(
        "SELECT COUNT(*) as plays, MAX(tasks_done) as max_done, MAX(tasks_total) as max_total "
        "FROM sessions WHERE user_id = ? AND scenario_id = ? AND finished_at IS NOT NULL",
        (user_id, scenario_id)
    )
    row = cur.fetchone()
    plays = row['plays'] if row and row['plays'] else 0
    max_done = row['max_done'] if row and row['max_done'] is not None else 0
    max_total = row['max_total'] if row and row['max_total'] else 10
    best_pct = int((max_done / max_total) * 100) if max_total > 0 else 0
    
    if plays == 0:
        mastery = "⭐ Newbie (Unplayed)"
    elif plays >= 5 and best_pct >= 80:
        mastery = "🏆 Mastered (Level 3)"
    elif plays >= 2 or best_pct >= 50:
        mastery = "🥇 Experienced (Level 2)"
    else:
        mastery = "🥉 Apprentice (Level 1)"
        
    return {
        "plays": plays,
        "best_pct": best_pct,
        "mastery": mastery
    }


def get_seen_task_goals(conn: sqlite3.Connection, user_id: int, scenario_name: str) -> set:
    """Goals this user has already been served in this scenario, across all sessions."""
    rows = conn.execute(
        "SELECT DISTINCT tl.goal "
        "FROM task_logs tl "
        "JOIN dynamic_scenarios ds ON tl.scenario_id = ds.id "
        "WHERE tl.user_id = ? AND ds.name = ?",
        (user_id, scenario_name)
    ).fetchall()
    return {row['goal'] for row in rows}


