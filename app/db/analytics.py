"""What a learner's history adds up to — the queries behind the dashboard.

Read-only, one learner (a user_profiles row) at a time. Written for
PostgreSQL on purpose: generate_series fills the weeks nobody played so a
chart shows the gap instead of hiding it, FILTER counts several outcomes in
one pass, and the streak is a gaps-and-islands window query. Timestamps are
ISO TEXT (see schema.py) and are cast with ::timestamptz where time
arithmetic is needed.

Every day and week boundary is in the database server's time zone — for the
Homebrew install that is the learner's own clock. The streak once used UTC
while active days and the weekly chart did not, so a Tokyo learner playing at
08:00 two days running saw the streak reset.
"""
import psycopg

from .mistakes import repeated_mistakes


def summary(conn: psycopg.Connection, user_id: int) -> dict:
    """The headline numbers."""
    row = conn.execute(
        """
        WITH s AS (
            -- every session started, as the weekly chart counts them: counting
            -- only finished ones read "2 sessions · 5 active days"
            SELECT COUNT(*)                                       AS sessions,
                   COUNT(DISTINCT (started_at::timestamptz)::date)  AS active_days
            FROM sessions WHERE user_id = %(u)s
        ), t AS (
            SELECT COUNT(*)                                       AS attempted,
                   COUNT(*) FILTER (WHERE outcome = 'completed')  AS completed
            FROM task_logs WHERE user_id = %(u)s
        ), v AS (
            SELECT COUNT(*)                                       AS taught,
                   COUNT(*) FILTER (WHERE times_correct >= 3)     AS learned
            FROM vocab_log WHERE user_id = %(u)s
        ), m AS (
            SELECT COUNT(*) AS repeated_classes FROM (
                SELECT normalized_key FROM mistakes WHERE user_id = %(u)s
                GROUP BY normalized_key HAVING COUNT(*) > 1) k
        )
        SELECT s.sessions, s.active_days, t.attempted, t.completed,
               v.taught, v.learned, m.repeated_classes
        FROM s, t, v, m
        """, {'u': user_id}).fetchone()
    out = {k: row[k] for k in row.keys()}
    out['completion_rate'] = round(100 * out['completed'] / out['attempted']) if out['attempted'] else 0
    out['due'] = out['taught'] - out['learned']
    out['streak_days'] = streak_days(conn, user_id)
    return out


def streak_days(conn: psycopg.Connection, user_id: int) -> int:
    """Consecutive days with a session, ending today or yesterday — the
    classic gaps-and-islands query: a day minus its row number is constant
    along a run of consecutive days."""
    row = conn.execute(
        """
        WITH days AS (
            SELECT DISTINCT (started_at::timestamptz)::date AS d
            FROM sessions WHERE user_id = %s
        ), runs AS (
            SELECT d, d - (ROW_NUMBER() OVER (ORDER BY d))::int AS island FROM days
        ), latest AS (
            SELECT island, MAX(d) AS last_day, COUNT(*) AS length
            FROM runs GROUP BY island ORDER BY MAX(d) DESC LIMIT 1
        )
        SELECT length FROM latest
        WHERE last_day >= current_date - 1
        """, (user_id,)).fetchone()
    return row[0] if row else 0


def weekly(conn: psycopg.Connection, user_id: int, weeks: int = 12) -> list:
    """One row per week for the last `weeks` weeks, empty weeks included."""
    return [dict(zip(r.keys(), r)) for r in conn.execute(
        """
        WITH wk AS (
            SELECT generate_series(date_trunc('week', now()) - (%(n)s - 1) * interval '1 week',
                                   date_trunc('week', now()), interval '1 week') AS week
        ), s AS (
            SELECT date_trunc('week', started_at::timestamptz) AS week, COUNT(*) AS sessions
            FROM sessions WHERE user_id = %(u)s GROUP BY 1
        ), t AS (
            SELECT date_trunc('week', finished_at::timestamptz) AS week,
                   COUNT(*) AS attempted,
                   COUNT(*) FILTER (WHERE outcome = 'completed') AS completed
            FROM task_logs WHERE user_id = %(u)s GROUP BY 1
        )
        SELECT to_char(wk.week, 'YYYY-MM-DD') AS week,
               COALESCE(s.sessions, 0)  AS sessions,
               COALESCE(t.attempted, 0) AS attempted,
               COALESCE(t.completed, 0) AS completed
        FROM wk LEFT JOIN s USING (week) LEFT JOIN t USING (week)
        ORDER BY wk.week
        """, {'u': user_id, 'n': weeks})]


def by_scenario(conn: psycopg.Connection, user_id: int) -> list:
    """Per roleplay scenario: plays, task outcomes, and how many tries a task
    took — where the learner finds it hard, hardest first."""
    return [dict(zip(r.keys(), r)) for r in conn.execute(
        """
        WITH plays AS (
            SELECT scenario_name, COUNT(*) AS plays
            FROM sessions WHERE user_id = %(u)s AND kind = 'scenario'
            GROUP BY scenario_name
        ), tasks AS (
            SELECT scenario_name,
                   COUNT(*) AS attempted,
                   COUNT(*) FILTER (WHERE outcome = 'completed') AS completed,
                   ROUND(AVG(attempts_used)::numeric, 1)::float  AS avg_attempts
            FROM task_logs WHERE user_id = %(u)s GROUP BY scenario_name
        )
        SELECT p.scenario_name, p.plays,
               COALESCE(t.attempted, 0) AS attempted,
               COALESCE(t.completed, 0) AS completed,
               CASE WHEN t.attempted > 0
                    THEN ROUND(100.0 * t.completed / t.attempted)::int END AS completion_rate,
               t.avg_attempts
        FROM plays p LEFT JOIN tasks t USING (scenario_name)
        ORDER BY completion_rate ASC NULLS LAST, p.plays DESC, p.scenario_name
        """, {'u': user_id})]


def due_words(conn: psycopg.Connection, user_id: int, language: str, limit: int = 20) -> list:
    """The words still being practised, closest to learned first."""
    return [dict(zip(r.keys(), r)) for r in conn.execute(
        """
        SELECT word, explanation, times_correct, scenario_name
        FROM vocab_log
        WHERE user_id = %s AND language = %s AND times_correct < 3
        ORDER BY times_correct DESC, last_seen_at DESC LIMIT %s
        """, (user_id, language, limit))]


def performance(conn: psycopg.Connection, days: int = 7) -> list:
    """Where the time goes: per traced stage (app/telemetry.py), how many
    and the median / 95th-percentile duration over the last `days` days —
    percentile_cont, because a mean hides the slow turns a learner notices."""
    return [dict(zip(r.keys(), r)) for r in conn.execute(
        """
        SELECT name, COUNT(*) AS count,
               ROUND(percentile_cont(0.5)  WITHIN GROUP (ORDER BY duration_ms)::numeric)::int AS p50_ms,
               ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms)::numeric)::int AS p95_ms
        FROM spans
        WHERE started_at > now() - %s * interval '1 day'
          AND status IS DISTINCT FROM 'ERROR'  -- a failed call is not a timing
          AND name IN ('turn', 'greeting', 'judge', 'actor', 'coach', 'llm.generate')
        GROUP BY name
        ORDER BY p95_ms DESC
        """, (days,))]


def dashboard(conn: psycopg.Connection, user_id: int, language: str) -> dict:
    """Everything the dashboard page shows, in one payload."""
    return {
        'summary': summary(conn, user_id),
        'weekly': weekly(conn, user_id),
        'scenarios': by_scenario(conn, user_id),
        'mistakes': repeated_mistakes(conn, user_id, language, limit=8),
        'words': due_words(conn, user_id, language),
        'performance': performance(conn),
    }
