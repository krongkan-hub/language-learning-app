"""Learner profiles and practice sessions: create, finish, resume, abandon."""
import psycopg
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


# ── sessions ─────────────────────────────────────────────────────────────────

def create_session(conn: psycopg.Connection, user_id: int, scenario_name: str,
                   language: str, mood: str, complication: 'str | None',
                   tasks_total: int, kind: str = 'scenario') -> int:
    """Start a new session and return its id.

    `kind` defaults to 'scenario' so the CLI's call site (and every existing
    test) is unaffected; the web front end's explain-mode session creator is
    the only caller that passes 'explain'.
    """
    cur = conn.execute(
        "INSERT INTO sessions "
        "(user_id, scenario_name, language, mood, complication, tasks_total, started_at, kind) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (user_id, scenario_name, language, mood, complication, tasks_total, _utcnow(), kind)
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


