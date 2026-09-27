"""The SQLite schema and migrations, kept ONLY for importing old databases.

The app runs on PostgreSQL since 2026-09-27. A learner's SQLite file may be
any shape this project ever wrote — from the dynamic_scenarios era on — and
these migrations, tested against every one of those shapes, bring it to the
last SQLite schema before app/db/import_sqlite.py copies it across.
Nothing in the running app imports this module.
"""
import sqlite3


_SCHEMA = """\
CREATE TABLE IF NOT EXISTS user_profiles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name  TEXT    NOT NULL DEFAULT 'learner',
    target_lang   TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    last_active   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES user_profiles(id),
    scenario_name TEXT    NOT NULL,
    language      TEXT    NOT NULL,
    mood          TEXT    NOT NULL,
    complication  TEXT,
    tasks_total   INTEGER NOT NULL,
    tasks_done    INTEGER NOT NULL DEFAULT 0,
    tasks_skipped INTEGER NOT NULL DEFAULT 0,
    started_at    TEXT    NOT NULL,
    finished_at   TEXT,
    -- 'scenario' (one of the 80 roleplay scenarios) or 'explain' (one of the
    -- explain-mode topics). Both kinds park their display name in
    -- scenario_name, which is fine for storage but not for a learner reading
    -- the Progress table: "Coffee Shop" and "how to get from home to work"
    -- are not the same kind of thing, and a shared mastery ladder implies
    -- they are. This column is what lets stats queries and the UI tell them
    -- apart again.
    kind          TEXT    NOT NULL DEFAULT 'scenario'
);
CREATE INDEX IF NOT EXISTS idx_sess_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS task_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id),
    scenario_name   TEXT    NOT NULL,
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

CREATE TABLE IF NOT EXISTS vocab_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES user_profiles(id),
    language        TEXT    NOT NULL,
    word            TEXT    NOT NULL,
    explanation     TEXT    NOT NULL,
    scenario_name   TEXT    NOT NULL,
    times_taught    INTEGER NOT NULL DEFAULT 1,
    times_correct   INTEGER NOT NULL DEFAULT 0,
    first_taught_at TEXT    NOT NULL,
    last_seen_at    TEXT    NOT NULL,
    -- The word's embedding, JSON, or NULL when it was logged without the
    -- optional embedder installed. Nullable on purpose: retrieval degrades to
    -- least-recently-seen rather than failing, and a row written today can be
    -- backfilled tomorrow.
    embedding       TEXT
);
CREATE INDEX IF NOT EXISTS idx_vl_user_lang ON vocab_log(user_id, language);

-- One row per ❌/✅ correction bullet the coach produced. Nothing else in this
-- database records a correction at all, so this table is what lets a stats
-- query answer "is this learner still making the same mistake?" — see
-- log_mistakes and repeated_mistakes below.
CREATE TABLE IF NOT EXISTS mistakes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES user_profiles(id),
    language        TEXT    NOT NULL,
    session_id      INTEGER NOT NULL REFERENCES sessions(id),
    scenario_name   TEXT    NOT NULL,
    quoted_text     TEXT    NOT NULL,
    correction      TEXT    NOT NULL,
    -- see _mistake_key: groups "two bottle"/"three bottle" and
    -- "I go yesterday"/"he go yesterday" into the same repeated class.
    normalized_key  TEXT    NOT NULL,
    created_at      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mistakes_user_lang_key ON mistakes(user_id, language, normalized_key);
"""


def _migrate_legacy_schema(conn: sqlite3.Connection) -> None:
    """Upgrade pre-existing databases that still key sessions/task_logs on a
    dynamic_scenarios foreign key.

    Older schemas stored ``scenario_id INTEGER NOT NULL REFERENCES
    dynamic_scenarios(id)``.  That table has since been removed and both tables
    now carry ``scenario_name TEXT`` directly.  A live database therefore needs
    rebuilding: the column cannot simply be added, because the legacy
    ``scenario_id`` is NOT NULL and new inserts no longer supply it.

    Scenario names are recovered by joining the old dynamic_scenarios rows
    before that table is dropped, so existing history is preserved.
    """
    have = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if 'sessions' not in have:
        return  # brand-new database; _SCHEMA already created it correctly

    cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)")}
    if 'scenario_name' in cols:
        return  # already migrated

    has_ds = 'dynamic_scenarios' in have
    name_expr = ("COALESCE((SELECT ds.name FROM dynamic_scenarios ds "
                 "WHERE ds.id = t.scenario_id), 'Unknown Scenario')"
                 if has_ds else "'Unknown Scenario'")

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("BEGIN")
    try:
        conn.execute("""
            CREATE TABLE sessions_new (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES user_profiles(id),
                scenario_name TEXT    NOT NULL,
                language      TEXT    NOT NULL,
                mood          TEXT    NOT NULL,
                complication  TEXT,
                tasks_total   INTEGER NOT NULL,
                tasks_done    INTEGER NOT NULL DEFAULT 0,
                tasks_skipped INTEGER NOT NULL DEFAULT 0,
                started_at    TEXT    NOT NULL,
                finished_at   TEXT
            )""")
        conn.execute(f"""
            INSERT INTO sessions_new
            SELECT t.id, t.user_id, {name_expr}, t.language, t.mood,
                   t.complication, t.tasks_total, t.tasks_done,
                   t.tasks_skipped, t.started_at, t.finished_at
            FROM sessions t""")
        conn.execute("DROP TABLE sessions")
        conn.execute("ALTER TABLE sessions_new RENAME TO sessions")

        conn.execute("""
            CREATE TABLE task_logs_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      INTEGER NOT NULL REFERENCES sessions(id),
                scenario_name   TEXT    NOT NULL,
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
            )""")
        conn.execute(f"""
            INSERT INTO task_logs_new
            SELECT t.id, t.session_id, {name_expr}, t.user_id, t.task_index,
                   t.goal, t.done_when, t.difficulty, t.phase, t.outcome,
                   t.attempts_used, t.started_at, t.finished_at
            FROM task_logs t""")
        conn.execute("DROP TABLE task_logs")
        conn.execute("ALTER TABLE task_logs_new RENAME TO task_logs")

        if has_ds:
            conn.execute("DROP TABLE dynamic_scenarios")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def _migrate_add_kind_column(conn: sqlite3.Connection) -> None:
    """Add sessions.kind to a database that predates explain mode.

    The ADD COLUMN default is 'scenario', which is right for every session
    older than explain mode. It is NOT right for every existing row: explain
    mode shipped before this column did, and those sessions were written with
    the topic title in the scenario_name column — 4 of them in the author's own
    database, which is how this was caught. So the rows are backfilled by name.

    Matching on name is safe because the two namespaces do not overlap and
    cannot: a scenario name is a place ("Coffee Shop"), a topic title is a
    sentence ("how you get from home to work"), and the backfill excludes
    anything the scenario catalogue claims, so a future collision resolves
    toward leaving the row alone.

    This also has to run after ``_migrate_legacy_schema``: that rebuild's own
    CREATE TABLE statement is frozen to the pre-explain-mode shape and does not
    know about `kind` either, so a database that goes through both migrations
    still needs this one afterward.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)")}
    if 'kind' not in cols:
        conn.execute(
            "ALTER TABLE sessions ADD COLUMN kind TEXT NOT NULL DEFAULT 'scenario'")

    # The backfill runs on EVERY startup, not only the one that adds the
    # column. My first version returned early when the column already existed,
    # so a database that had been migrated once — by a run that predated this
    # backfill — kept its explain sessions filed as scenarios forever. It is a
    # cheap idempotent UPDATE; there is no reason to gate it on the schema step.
    try:
        from ..explain import load_topics
        from ..scenarios.builtins import load_scenarios
        scenario_names = {sc.name for sc in load_scenarios()}
        titles = {t.title(lang) for t in load_topics()
                  for lang in ('English', 'Japanese')} - scenario_names
    except Exception:
        titles = set()      # a backfill is a nicety; never fail startup for it
    for title in titles:
        conn.execute("UPDATE sessions SET kind = 'explain' WHERE scenario_name = ?",
                     (title,))
    conn.commit()


def _migrate_add_vocab_embedding(conn: sqlite3.Connection) -> None:
    """Add vocab_log.embedding to a database that predates semantic retrieval.

    No backfill: computing it needs the embedder, which is an optional extra,
    and a NULL simply means this word is ranked by recency until something
    embeds it. Doing it at startup would also load a model inside init_db,
    which every test and every CLI start goes through.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(vocab_log)")}
    if 'embedding' not in cols:
        conn.execute("ALTER TABLE vocab_log ADD COLUMN embedding TEXT")
        conn.commit()


def _migrate_add_mistakes_table(conn: sqlite3.Connection) -> None:
    """Add the mistakes table to a database that predates repeat-mistake tracking.

    Unlike _migrate_add_kind_column / _migrate_add_vocab_embedding, this isn't
    an ALTER TABLE on existing rows — `mistakes` is a brand-new table with no
    prior column to add, so _SCHEMA's own CREATE TABLE IF NOT EXISTS would
    already create it on any init_db call. This function exists anyway, in
    the same style as the other migrations, so the addition is explicit,
    named, and independently testable rather than an incidental side effect
    of the schema re-apply at the end of init_db.
    """
    have = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if 'mistakes' not in have:
        conn.executescript(_SCHEMA)
        conn.commit()


def open_upgraded(db_path: str) -> sqlite3.Connection:
    """Open an old SQLite database and bring it to the final SQLite shape —
    exactly what init_db() did before the move to PostgreSQL."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    _migrate_legacy_schema(conn)
    _migrate_add_kind_column(conn)
    _migrate_add_vocab_embedding(conn)
    _migrate_add_mistakes_table(conn)
    conn.executescript(_SCHEMA)  # re-apply so indexes exist on rebuilt tables
    conn.commit()
    return conn
