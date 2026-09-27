"""Session rows: counters, backfill, and the stale-session sweep."""
from app import db


def test_the_backfill_counts_failed_tasks_too(tmp_path, monkeypatch):
    """abandon_stale_sessions rebuilds the counters from task_logs, so it has to
    agree with the session loop or an interrupted session silently zeroes its failures."""
    monkeypatch.setenv("LANGUAGE_COACH_DB", str(tmp_path / "s.db"))
    conn = db.init_db(str(tmp_path / "s.db"))
    uid = db.get_or_create_user(conn, target_lang="English")
    sid = db.create_session(conn, uid, "Cafe", "English", "neutral", None, 3)
    for idx, outcome in ((0, 'completed'), (1, 'failed'), (2, 'skipped')):
        db.log_task(conn, sid, "Cafe", uid, idx, "g", "d", "standard", 1,
                    outcome, 1, db._utcnow(), db._utcnow())
    # The backfill only touches sessions older than 7 days, so age it.
    conn.execute("UPDATE sessions SET started_at = '2020-01-01T00:00:00Z' WHERE id = %s", (sid,))
    conn.commit()
    db.abandon_stale_sessions(conn, uid)
    row = conn.execute("SELECT tasks_done, tasks_skipped FROM sessions WHERE id=%s", (sid,)).fetchone()
    assert (row["tasks_done"], row["tasks_skipped"]) == (1, 2), dict(row)
    conn.close()
