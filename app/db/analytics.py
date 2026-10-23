"""What a learner's history adds up to, in SQL — the trends half of the
`--stats` report (app/cli/menus.py): weekly activity, the hardest scenarios,
and where a turn's time goes. The headline totals come from progress.py.

Read-only, one learner (a user_profiles row) at a time. Written for
PostgreSQL on purpose: generate_series fills the weeks nobody played so a
gap shows instead of hiding, and FILTER counts several outcomes in one pass.
Timestamps are ISO TEXT (see schema.py) and are cast with ::timestamptz
where time arithmetic is needed.

Every day and week boundary is in the database server's time zone — for the
Homebrew install that is the learner's own clock.
"""
import psycopg


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
