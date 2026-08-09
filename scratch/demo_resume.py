import os
import tempfile
from datetime import datetime, timezone, timedelta
from app import db
from app.scenarios.builtins import SCENARIOS
from app.scenarios.models import Scenario

def run_demo():
    print("=== Demo 1: Unfinished session (<7 days old) with 2 logged tasks ===")
    fd, tmp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = db.init_db(tmp_db_path)
        user_id = db.get_or_create_user(conn, target_lang="English")
        sc = SCENARIOS[0] # Hotel Check-in
        
        # Create unfinished session started 2 days ago
        s1 = db.create_session(conn, user_id, sc.name, "English", "polite", None, len(sc.tasks))
        two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        conn.execute("UPDATE sessions SET started_at = ? WHERE id = ?", (two_days_ago, s1))
        conn.commit()

        # Log two tasks
        g1 = sc.tasks[0].goal
        g2 = sc.tasks[1].goal
        now = db._utcnow()
        db.log_task(conn, s1, sc.name, user_id, 0, g1, "Done 1", "standard", 1, "completed", 1, now, now)
        db.log_task(conn, s1, sc.name, user_id, 1, g2, "Done 2", "standard", 1, "completed", 1, now, now)

        # 1. Check get_resumable_session
        res = db.get_resumable_session(conn, user_id, "English")
        sess_row, count = res
        print(f"get_resumable_session reported session ID {sess_row['id']} for scenario '{sess_row['scenario_name']}'")
        print(f"Logged tasks count reported from task_logs: {count}")
        assert count == 2

        # 2. Check resumed task list
        logged_goals = db.get_logged_goals_for_session(conn, s1)
        available_tasks = [t for t in sc.tasks if t.goal not in logged_goals]
        temp_scenario = Scenario(
            name=sc.name, place=sc.place, role=sc.role, speaker=sc.speaker,
            tasks=available_tasks, complications=sc.complications,
            name_translations=sc.name_translations, place_translations=sc.place_translations
        )
        resumed_tasks = temp_scenario.get_session_tasks(num_tasks=10)
        resumed_goals = [t.goal for t in resumed_tasks]

        print(f"Original task count in scenario: {len(sc.tasks)}")
        print(f"Logged goals excluded: {logged_goals}")
        print(f"Resumed task list count: {len(resumed_tasks)}")
        print(f"Are logged goals in resumed task list? {g1 in resumed_goals or g2 in resumed_goals}")
        assert g1 not in resumed_goals and g2 not in resumed_goals

        conn.close()
    finally:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)

    print("\n=== Demo 2: 30-day-old unfinished session ===")
    fd, tmp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = db.init_db(tmp_db_path)
        user_id = db.get_or_create_user(conn, target_lang="English")
        sc = SCENARIOS[0]

        # Create unfinished session started 30 days ago
        s_stale = db.create_session(conn, user_id, sc.name, "English", "polite", None, len(sc.tasks))
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        conn.execute("UPDATE sessions SET started_at = ? WHERE id = ?", (thirty_days_ago, s_stale))
        conn.commit()

        # Log 1 completed task on stale session
        now = db._utcnow()
        db.log_task(conn, s_stale, sc.name, user_id, 0, sc.tasks[0].goal, "Done 1", "standard", 1, "completed", 1, now, now)

        row_before = conn.execute("SELECT finished_at, tasks_done FROM sessions WHERE id = ?", (s_stale,)).fetchone()
        print(f"Before abandon_stale_sessions: finished_at={row_before['finished_at']}, tasks_done={row_before['tasks_done']}")

        res_before = db.get_resumable_session(conn, user_id, "English")
        print(f"get_resumable_session before cleanup: {res_before}")

        # Run abandon_stale_sessions
        db.abandon_stale_sessions(conn, user_id)

        res_after = db.get_resumable_session(conn, user_id, "English")
        print(f"get_resumable_session after cleanup: {res_after}")
        assert res_after is None

        row_after = conn.execute("SELECT finished_at, tasks_done FROM sessions WHERE id = ?", (s_stale,)).fetchone()
        print(f"After abandon_stale_sessions: finished_at={row_after['finished_at']}, tasks_done={row_after['tasks_done']}")
        assert row_after['finished_at'] is not None
        assert row_after['tasks_done'] == 1

        conn.close()
    finally:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)

if __name__ == '__main__':
    run_demo()
