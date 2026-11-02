"""Learner profiles and practice sessions: create, finish, resume, abandon."""
import psycopg
from psycopg.types.json import Jsonb
from datetime import datetime, timezone, timedelta
from .common import _utcnow


# ── user_profiles ────────────────────────────────────────────────────────────

def get_or_create_user(conn: psycopg.Connection,
                       display_name: str = 'learner',
                       target_lang: str = 'English') -> int:
    """Return the user id, creating the row if it doesn't exist."""
    row = conn.execute(
        "SELECT id FROM user_profiles WHERE display_name = %s AND target_lang = %s",
        (display_name, target_lang)
    ).fetchone()
    if row:
        conn.execute("UPDATE user_profiles SET last_active = %s WHERE id = %s",
                     (_utcnow(), row['id']))
        conn.commit()
        return row['id']
    now = _utcnow()
    cur = conn.execute(
        "INSERT INTO user_profiles (display_name, target_lang, created_at, last_active) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (display_name, target_lang, now, now)
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def find_user(conn: psycopg.Connection, display_name: str = 'learner',
              target_lang: str = 'English') -> 'int | None':
    """The user id, or None — reading only. For pages that just look: a GET
    used to create a profile row and bump last_active."""
    row = conn.execute(
        "SELECT id FROM user_profiles WHERE display_name = %s AND target_lang = %s",
        (display_name, target_lang)
    ).fetchone()
    return row['id'] if row else None


# No learner has this id: what a read for someone who never played returns.
NO_USER = -1


# ── sessions ─────────────────────────────────────────────────────────────────

def create_session(conn: psycopg.Connection, user_id: int, scenario_name: str,
                   language: str, mood: str, complication: 'str | None',
                   tasks_total: int, kind: str = 'scenario',
                   scene: 'dict | None' = None) -> int:
    """Start a new session and return its id.

    `kind` defaults to 'scenario'; explain mode's session creator
    (app/cli/state.py) is the only caller that passes 'explain'. `scene` is a
    composed scene's SceneSpec.as_dict(); None means the default composition.
    """
    cur = conn.execute(
        "INSERT INTO sessions "
        "(user_id, scenario_name, language, mood, complication, tasks_total, started_at, kind, scene) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (user_id, scenario_name, language, mood, complication, tasks_total, _utcnow(), kind,
         None if scene is None else Jsonb(scene))
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def finish_session(conn: psycopg.Connection, session_id: int,
                   tasks_done: int, tasks_skipped: int) -> None:
    """Mark a session as finished with final counts."""
    conn.execute(
        "UPDATE sessions SET tasks_done = %s, tasks_skipped = %s, finished_at = %s "
        "WHERE id = %s",
        (tasks_done, tasks_skipped, _utcnow(), session_id)
    )
    conn.commit()


def get_resumable_session(conn: psycopg.Connection, user_id: int, language: str):
    """The newest roleplay session in `language` that was never finished, with
    the goals its task_logs hold (in task order) and their counts — or None.
    Its `scene` is the stored SceneSpec dict, or None for a default scene.

    Every way out of the CLI finishes a session, so one is left open only
    when the process is killed (an out-of-memory kill, a power cut). Run
    after abandon_stale_sessions, which closes anything older than 7 days.
    """
    row = conn.execute(
        "SELECT * FROM sessions "
        "WHERE user_id = %s AND language = %s AND kind = 'scenario' AND finished_at IS NULL "
        "ORDER BY started_at DESC, id DESC LIMIT 1",
        (user_id, language)
    ).fetchone()
    if not row:
        return None
    logs = conn.execute(
        "SELECT goal, outcome FROM task_logs WHERE session_id = %s ORDER BY task_index, id",
        (row['id'],)
    ).fetchall()
    return {**{k: row[k] for k in row.keys()},
            'logged_goals': [r['goal'] for r in logs],
            'tasks_done': sum(r['outcome'] == 'completed' for r in logs),
            # skipped and failed together, as abandon_stale_sessions counts them
            'tasks_missed': sum(r['outcome'] in ('skipped', 'failed') for r in logs)}


def abandon_stale_sessions(conn: psycopg.Connection, user_id: int) -> None:
    """Mark every unfinished session older than 7 days as finished,
    and backfill tasks_done and tasks_skipped from task_logs."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    stale_rows = conn.execute(
        "SELECT id FROM sessions "
        "WHERE user_id = %s AND finished_at IS NULL AND started_at < %s",
        (user_id, cutoff)
    ).fetchall()
    now = _utcnow()
    for row in stale_rows:
        sid = row['id']
        counts = conn.execute(
            "SELECT "
            "SUM(CASE WHEN outcome = 'completed' THEN 1 ELSE 0 END) as done, "
            # 'failed' counts here for the same reason the CLI counter does:
            # the column is the "Skipped/Failed" total. Counting only skips let
            # an abandoned or resumed session silently zero out its failures.
            "SUM(CASE WHEN outcome IN ('skipped', 'failed') THEN 1 ELSE 0 END) as skipped "
            "FROM task_logs WHERE session_id = %s",
            (sid,)
        ).fetchone()
        done = counts['done'] if counts and counts['done'] is not None else 0
        skipped = counts['skipped'] if counts and counts['skipped'] is not None else 0
        conn.execute(
            "UPDATE sessions SET finished_at = %s, tasks_done = %s, tasks_skipped = %s WHERE id = %s",
            (now, done, skipped, sid)
        )
    conn.commit()


