"""Session rows: counters, kinds, the SQLite import, the stale-session sweep,
and the summary's next-rung and words-due counts."""
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


def test_db_create_session_kind_defaults_to_scenario(tmp_path):
    """The CLI (and every pre-existing caller) invokes db.create_session
    without a `kind` argument, so it must keep classifying those sessions as
    'scenario' — the default before explain mode's kind column existed at
    all.
    """
    conn = db.init_db(str(tmp_path / 'kind.db'))
    uid = db.get_or_create_user(conn, target_lang='English')
    sid = db.create_session(conn, uid, 'Cafe', 'English', 'polite', None, 10)
    row = conn.execute('SELECT kind FROM sessions WHERE id = %s', (sid,)).fetchone()
    assert row['kind'] == 'scenario'


def test_legacy_database_without_a_kind_column_still_works(tmp_path):
    """A SQLite database from before explain mode has no `kind` column at
    all. It must import with every session filed as 'scenario' (every session
    that old was a roleplay) and its stats intact.
    """
    import sqlite3
    path = str(tmp_path / 'legacy.db')
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT, display_name TEXT NOT NULL DEFAULT 'learner',
            target_lang TEXT NOT NULL, created_at TEXT NOT NULL, last_active TEXT NOT NULL
        );
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            scenario_name TEXT NOT NULL, language TEXT NOT NULL, mood TEXT NOT NULL,
            complication TEXT, tasks_total INTEGER NOT NULL, tasks_done INTEGER NOT NULL DEFAULT 0,
            tasks_skipped INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL, finished_at TEXT
        );
    """)
    now = '2020-01-01T00:00:00Z'
    conn.execute("INSERT INTO user_profiles (display_name, target_lang, created_at, last_active) "
                "VALUES ('learner','English',?,?)", (now, now))
    conn.execute("INSERT INTO sessions (user_id, scenario_name, language, mood, complication, "
                "tasks_total, tasks_done, tasks_skipped, started_at, finished_at) "
                "VALUES (1,'Old Scenario','English','polite',NULL,10,8,2,?,?)", (now, now))
    conn.commit()
    conn.close()

    from app.db.import_sqlite import import_sqlite
    migrated = db.init_db(path + '.pg')
    import_sqlite(path, migrated)
    row = migrated.execute('SELECT kind FROM sessions').fetchone()
    assert row['kind'] == 'scenario'
    stats = db.get_all_scenario_stats(migrated, 1)
    assert stats['Old Scenario']['plays'] == 1
    assert stats['Old Scenario']['best_pct'] == 80


def test_old_explain_sessions_are_relabelled_on_import(tmp_path):
    """Explain mode shipped before sessions.kind did, so its sessions were
    written with the topic title in scenario_name and kind 'scenario' — 4 in
    the author's real database. The import files them back as 'explain'."""
    from app.db.import_sqlite import import_sqlite
    from app.db.legacy_sqlite import open_upgraded
    from app.explain import load_topics

    path = str(tmp_path / 'old.db')
    title = load_topics()[0].title('English')
    old = open_upgraded(path)
    old.execute("INSERT INTO user_profiles (display_name, target_lang, created_at, last_active) "
                "VALUES ('learner', 'English', 't', 't')")
    old.execute("INSERT INTO sessions (user_id, scenario_name, language, mood, tasks_total, "
                "tasks_done, started_at, finished_at, kind) "
                "VALUES (1, ?, 'English', '', 5, 3, 't', 't', 'scenario')", (title,))
    old.commit()
    old.close()

    conn = db.init_db(path + '.pg')
    import_sqlite(path, conn)
    assert conn.execute('SELECT kind FROM sessions').fetchone()[0] == 'explain'
    assert title not in db.get_all_scenario_stats(conn, 1)
    assert title in db.get_all_topic_stats(conn, 1)


def test_the_backfill_never_reclassifies_a_real_scenario():
    """It matches on name, so the guard is that the two namespaces cannot
    overlap — and anything the catalogue claims is excluded outright."""
    from app.explain import load_topics
    from app.scenarios.builtins import load_scenarios
    scenario_names = {sc.name for sc in load_scenarios()}
    titles = {t.title(lang) for t in load_topics() for lang in ('English', 'Japanese')}
    assert not (titles & scenario_names), titles & scenario_names


def test_the_summary_says_what_the_next_rung_costs():
    """The mastery ladder is the one progress fact this app earns rather than
    awards, and the end of a session is when it is worth showing. newbie needs
    two plays for `experienced`; five and 80% reach `mastered`."""
    import app.db as db

    conn = db.init_db(':memory:')
    try:
        uid = db.get_or_create_user(conn, target_lang='English')
        hint = db.next_rank_hint(conn, uid, 'Cafe')
        assert hint['next_rank'] == 'experienced' and hint['plays_needed'] == 2

        for _ in range(2):
            sid = db.create_session(conn, uid, 'Cafe', 'English', 'neutral', None, 5)
            db.finish_session(conn, sid, 5, 0)
        hint = db.next_rank_hint(conn, uid, 'Cafe')
        assert hint['rank'] == 'experienced'
        assert hint['next_rank'] == 'mastered' and hint['plays_needed'] == 3
        assert hint['pct_needed'] is None          # already at 100%

        for _ in range(3):
            sid = db.create_session(conn, uid, 'Cafe', 'English', 'neutral', None, 5)
            db.finish_session(conn, sid, 5, 0)
        top = db.next_rank_hint(conn, uid, 'Cafe')
        assert top['rank'] == 'mastered' and top['next_rank'] is None
    finally:
        conn.close()


def test_words_due_is_counted_not_capped_by_the_drill_limit():
    """get_vocab_for_review takes a limit because it feeds a three-word drill.
    Counting its rows would have reported 'you have 3 words' forever."""
    import app.db as db

    conn = db.init_db(':memory:')
    try:
        uid = db.get_or_create_user(conn, target_lang='English')
        for i in range(7):
            db.log_vocab(conn, uid, 'English', f'word{i}', 'a definition', 'Cafe')
        assert db.count_vocab_due(conn, uid, 'English') == 7
        assert len(db.get_vocab_for_review(conn, uid, 'English')) == 3
        assert db.count_vocab_due(conn, uid, 'Japanese') == 0
    finally:
        conn.close()
