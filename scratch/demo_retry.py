import os
import tempfile
from app import db
from app.scenarios.builtins import SCENARIOS

def run_demo():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_db_path = tmp.name

    try:
        conn = db.init_db(tmp_db_path)
        uid = db.get_or_create_user(conn, display_name="demo_user", target_lang="English")
        
        sc = SCENARIOS[0]
        print(f"Scenario: {sc.name}")

        # Seed 2 failed rows and 1 skipped row
        failed_goal_1 = sc.tasks[1].goal
        failed_goal_2 = sc.tasks[2].goal
        skipped_goal = sc.tasks[3].goal

        now = db._utcnow()
        sess_id = db.create_session(conn, uid, sc.name, "English", "polite", None, 10)
        db.log_task(conn, sess_id, sc.name, uid, 0, failed_goal_1, "Done", sc.tasks[1].difficulty, sc.tasks[1].phase, "failed", 3, now, now)
        db.log_task(conn, sess_id, sc.name, uid, 1, failed_goal_2, "Done", sc.tasks[2].difficulty, sc.tasks[2].phase, "failed", 3, now, now)
        db.log_task(conn, sess_id, sc.name, uid, 2, skipped_goal, "Done", sc.tasks[3].difficulty, sc.tasks[3].phase, "skipped", 0, now, now)

        unfinished = db.get_unfinished_task_goals(conn, uid, sc.name)
        print(f"Unfinished goals returned from DB: {unfinished}")

        seen = db.get_seen_task_goals(conn, uid, sc.name)
        session_tasks = sc.get_session_tasks(num_tasks=10, seen_goals=seen, retry_goals=unfinished)
        session_goals = [t.goal for t in session_tasks]
        
        print("\nSession tasks generated:")
        for idx, t in enumerate(session_tasks, 1):
            is_retry = " [RETRY]" if t.goal in unfinished else ""
            print(f"  {idx}. [{t.difficulty}] (phase {t.phase}) {t.goal}{is_retry}")

        retried_in_session = [t.goal for t in session_tasks if t.goal in unfinished]
        print(f"\nRetried tasks present in session: {len(retried_in_session)} / {len(unfinished)}")

    finally:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)

if __name__ == "__main__":
    run_demo()
