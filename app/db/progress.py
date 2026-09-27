"""Task results and what they add up to: per-scenario stats, mastery rank, overall totals."""
import psycopg


# ── task_logs ────────────────────────────────────────────────────────────────

def log_task(conn: psycopg.Connection, session_id: int, scenario_name: str,
             user_id: int, task_index: int, goal: str, done_when: str,
             difficulty: str, phase: int, outcome: str,
             attempts_used: int, started_at: str, finished_at: str) -> int:
    """Record the outcome of a single task attempt."""
    cur = conn.execute(
        "INSERT INTO task_logs "
        "(session_id, scenario_name, user_id, task_index, goal, done_when, "
        " difficulty, phase, outcome, attempts_used, started_at, finished_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (session_id, scenario_name, user_id, task_index, goal, done_when,
         difficulty, phase, outcome, attempts_used, started_at, finished_at)
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def _mastery_rank(plays: int, best_pct: int) -> str:
    """The mastery ladder, in one place.

    It was written out twice — once here and once in get_all_scenario_stats —
    byte-identical and free to diverge. The chooser and the progress report read
    from the two different copies, so a change to one would have silently
    disagreed with the other about the same scenario (OPEN-34).
    """
    if plays == 0:
        return "newbie"
    if plays >= 5 and best_pct >= 80:
        return "mastered"
    if plays >= 2 or best_pct >= 50:
        return "experienced"
    return "apprentice"


def next_rank_hint(conn: psycopg.Connection, user_id: int, scenario_name: str) -> dict:
    """What the learner needs for the NEXT rung of the mastery ladder.

    The ladder (_mastery_rank) is the one thing this app already knows about a
    learner's progress that is earned rather than awarded — no points, no
    streak, nothing invented. Saying "one more play at this score and this
    scenario is mastered" at the end of a session is that fact, shown at the
    moment it is worth something. Duolingo has to print an XP number here
    because it cannot measure the learning; this project can, so it does not
    have to.

    Returns rank, and `plays_needed`/`pct_needed` for the next rung, either of
    which is None when that rung does not ask for it. At the top, next_rank is
    None and nothing should be shown.
    """
    stats = get_scenario_stats(conn, user_id, scenario_name)
    plays, best = stats['plays'], stats['best_pct']
    rank = stats['mastery']
    if rank == 'mastered':
        return dict(rank=rank, next_rank=None, plays_needed=None, pct_needed=None)
    if rank in ('newbie', 'apprentice'):
        # experienced needs plays >= 2 OR best_pct >= 50, so name the nearer one.
        return dict(rank=rank, next_rank='experienced',
                    plays_needed=max(0, 2 - plays),
                    pct_needed=None if best >= 50 else 50 - best)
    return dict(rank=rank, next_rank='mastered',
                plays_needed=max(0, 5 - plays),
                pct_needed=None if best >= 80 else 80 - best)


def get_scenario_stats(conn: psycopg.Connection, user_id: int, scenario_name: str) -> dict:
    """Return playthrough count, best completion rate, and mastery rank key for a user and scenario.

    Restricted to kind='scenario' so an explain topic can never be counted
    against a roleplay scenario of the same name.

    No production caller: the CLI and the web both read whole tables through
    get_all_scenario_stats, and this one is reached only from the tests, which
    use it as the single-scenario probe for the mastery ladder. Kept rather
    than deleted — OPEN-34 proposed deleting it as a byte-identical copy of the
    ladder in get_all_scenario_stats, and that reason is gone: both now call
    _mastery_rank, so there is nothing left here to diverge.
    """
    cur = conn.execute(
        "SELECT COUNT(*) as plays, MAX(tasks_done) as max_done, MAX(tasks_total) as max_total "
        "FROM sessions WHERE user_id = %s AND scenario_name = %s AND kind = 'scenario' "
        "AND finished_at IS NOT NULL",
        (user_id, scenario_name)
    )
    row = cur.fetchone()
    plays = row['plays'] if row and row['plays'] else 0
    max_done = row['max_done'] if row and row['max_done'] is not None else 0
    max_total = row['max_total'] if row and row['max_total'] else 10
    best_pct = int((max_done / max_total) * 100) if max_total > 0 else 0
    
    mastery = _mastery_rank(plays, best_pct)
        
    return {
        "plays": plays,
        "best_pct": best_pct,
        "mastery": mastery
    }


def get_all_scenario_stats(conn: psycopg.Connection, user_id: int) -> dict:
    """Return scenario stats for all played ROLEPLAY scenarios of a user, keyed by scenario_name.

    Filtered to kind='scenario': explain sessions store their topic title in
    the same scenario_name column, and without this filter they showed up in
    the Progress page's 80-scenario table indistinguishable from a real
    scenario, with a mastery ladder that means something different for a
    topic than for a scenario. See get_all_topic_stats for the explain-mode
    equivalent.
    """
    cur = conn.execute(
        "SELECT scenario_name, COUNT(*) as plays, MAX(tasks_done) as max_done, "
        "MAX(tasks_total) as max_total, MAX(finished_at) as last_played "
        "FROM sessions WHERE user_id = %s AND kind = 'scenario' AND finished_at IS NOT NULL "
        "GROUP BY scenario_name "
        "ORDER BY MAX(finished_at) DESC",
        (user_id,)
    )
    results = {}
    for row in cur.fetchall():
        plays = row['plays'] if row['plays'] else 0
        max_done = row['max_done'] if row['max_done'] is not None else 0
        max_total = row['max_total'] if row['max_total'] else 10
        best_pct = int((max_done / max_total) * 100) if max_total > 0 else 0

        mastery = _mastery_rank(plays, best_pct)

        results[row['scenario_name']] = {
            "scenario_name": row['scenario_name'],
            "plays": plays,
            "best_pct": best_pct,
            "mastery": mastery,
            "last_played": row['last_played']
        }
    return results


def get_all_topic_stats(conn: psycopg.Connection, user_id: int) -> dict:
    """Return topic stats for all played EXPLAIN topics of a user, keyed by topic_name.

    The explain-mode counterpart to get_all_scenario_stats, kept as a
    separate function rather than a parameter so the two result shapes stay
    obviously distinct at the call site (`scenario_name` vs `topic_name`)
    instead of one dict silently meaning two different things depending on
    who reads it.
    """
    cur = conn.execute(
        "SELECT scenario_name, COUNT(*) as plays, MAX(tasks_done) as max_done, "
        "MAX(tasks_total) as max_total, MAX(finished_at) as last_played "
        "FROM sessions WHERE user_id = %s AND kind = 'explain' AND finished_at IS NOT NULL "
        "GROUP BY scenario_name "
        "ORDER BY MAX(finished_at) DESC",
        (user_id,)
    )
    results = {}
    for row in cur.fetchall():
        plays = row['plays'] if row['plays'] else 0
        max_done = row['max_done'] if row['max_done'] is not None else 0
        max_total = row['max_total'] if row['max_total'] else 10
        best_pct = int((max_done / max_total) * 100) if max_total > 0 else 0

        mastery = _mastery_rank(plays, best_pct)

        results[row['scenario_name']] = {
            "topic_name": row['scenario_name'],
            "plays": plays,
            "best_pct": best_pct,
            "mastery": mastery,
            "last_played": row['last_played']
        }
    return results


def get_overall_stats(conn: psycopg.Connection, user_id: int) -> dict:
    """Return overall session and task counts for a user."""
    row_sess = conn.execute(
        "SELECT COUNT(*) as sessions_played FROM sessions WHERE user_id = %s AND finished_at IS NOT NULL",
        (user_id,)
    ).fetchone()
    sessions_played = row_sess['sessions_played'] if row_sess else 0

    row_tasks = conn.execute(
        "SELECT COUNT(*) as attempted, "
        "SUM(CASE WHEN outcome = 'completed' THEN 1 ELSE 0 END) as completed "
        "FROM task_logs WHERE user_id = %s",
        (user_id,)
    ).fetchone()
    attempted = row_tasks['attempted'] if row_tasks and row_tasks['attempted'] else 0
    completed = row_tasks['completed'] if row_tasks and row_tasks['completed'] else 0
    rate = int((completed / attempted) * 100) if attempted > 0 else 0

    return {
        "sessions_played": sessions_played,
        "sessions": sessions_played,
        "tasks_attempted": attempted,
        "attempted": attempted,
        "tasks_completed": completed,
        "completed": completed,
        "overall_completion_rate": rate,
        "completion_rate": rate
    }


def get_vocab_stats(conn: psycopg.Connection, user_id: int) -> dict:
    """Return total distinct words, learned words (times_correct >= 3), and due words for a user."""
    row = conn.execute(
        "SELECT COUNT(DISTINCT LOWER(word)) as total_words, "
        "SUM(CASE WHEN times_correct >= 3 THEN 1 ELSE 0 END) as learned_words, "
        "SUM(CASE WHEN times_correct < 3 THEN 1 ELSE 0 END) as due_words "
        "FROM vocab_log WHERE user_id = %s",
        (user_id,)
    ).fetchone()
    total = row['total_words'] if row and row['total_words'] else 0
    learned = row['learned_words'] if row and row['learned_words'] else 0
    due = row['due_words'] if row and row['due_words'] else 0

    return {
        "total_words": total,
        "distinct_words": total,
        "learned_words": learned,
        "learned": learned,
        "due_words": due,
        "due": due
    }


def get_seen_task_goals(conn: psycopg.Connection, user_id: int, scenario_name: str) -> set:
    """Goals this user has already been served in this scenario, across all sessions."""
    rows = conn.execute(
        "SELECT DISTINCT goal FROM task_logs "
        "WHERE user_id = %s AND scenario_name = %s",
        (user_id, scenario_name)
    ).fetchall()
    return {row['goal'] for row in rows}


def get_unfinished_task_goals(conn: psycopg.Connection, user_id: int, scenario_name: str) -> set:
    """Goals this user failed or skipped in this scenario and has never since completed."""
    rows = conn.execute(
        "SELECT DISTINCT goal FROM task_logs "
        "WHERE user_id = %s AND scenario_name = %s AND outcome IN ('failed', 'skipped') "
        "EXCEPT "
        "SELECT DISTINCT goal FROM task_logs "
        "WHERE user_id = %s AND scenario_name = %s AND outcome = 'completed'",
        (user_id, scenario_name, user_id, scenario_name)
    ).fetchall()
    return {row['goal'] for row in rows}
