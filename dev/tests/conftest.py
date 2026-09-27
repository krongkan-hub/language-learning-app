"""Every test runs against the PostgreSQL test database, never the real one.

db.init_db(path) maps each path to its own schema (app/db/connection.py), so
tests stay isolated exactly as separate SQLite files kept them; the schemas
are dropped when the run ends. Point $LANGUAGE_COACH_TEST_DSN elsewhere (CI
does) to use another server.
"""
import os

os.environ['LANGUAGE_COACH_DSN'] = os.environ.get(
    'LANGUAGE_COACH_TEST_DSN', 'dbname=language_coach_test')


def pytest_sessionfinish(session, exitstatus):
    import psycopg
    from app.db.connection import TEST_SCHEMA_PREFIX
    try:
        with psycopg.connect(os.environ['LANGUAGE_COACH_DSN'], autocommit=True) as conn:
            names = [r[0] for r in conn.execute(
                "SELECT nspname FROM pg_namespace WHERE nspname LIKE %s",
                (TEST_SCHEMA_PREFIX + '%',))]
            for name in names:
                conn.execute(f'DROP SCHEMA "{name}" CASCADE')
    except psycopg.Error:
        pass
