"""Opening a PostgreSQL connection, and which schema it works in.

The server is found through $LANGUAGE_COACH_DSN (a libpq connection string,
default "dbname=language_coach"). Inside that database every "database" the
app opens is a SCHEMA:

    init_db()               -> schema "coach", the learner's real data
    init_db("some/path")    -> a schema named after that path

The second form is what keeps the test suite honest. Hundreds of tests open
init_db(tmp_path / "x.db") and expect a fresh, empty database each time —
exactly what a new SQLite file gave them. A schema per path gives the same
isolation without a single test changing, and dev/tests/conftest.py drops
every one of them when the run ends. $LANGUAGE_COACH_DB still names the
namespace the web app uses, as it named the file before.
"""
import hashlib
import os
import uuid

import psycopg
from psycopg.rows import RowMaker

DEFAULT_DSN = 'dbname=language_coach'
DEFAULT_SCHEMA = 'coach'
TEST_SCHEMA_PREFIX = 'ns_'


class Row(tuple):
    """A result row readable as row[0] AND row['column'], like sqlite3.Row —
    so callers and tests written against SQLite keep working unchanged."""

    _keys: tuple = ()

    def __getitem__(self, key):
        if isinstance(key, str):
            return tuple.__getitem__(self, self._keys.index(key))
        return tuple.__getitem__(self, key)

    def keys(self):
        return list(self._keys)

    def get(self, key, default=None):
        return self[key] if key in self._keys else default


def row_factory(cursor) -> RowMaker:
    names = tuple(col.name for col in cursor.description or ())
    cls = type('Row', (Row,), {'_keys': names})
    return lambda values: cls(values)


def dsn() -> str:
    return os.environ.get('LANGUAGE_COACH_DSN', DEFAULT_DSN)


def schema_for(db_path: 'str | None') -> str:
    """The schema a path maps to. No path means the real data."""
    if not db_path:
        return DEFAULT_SCHEMA
    if db_path == ':memory:':
        # SQLite's ":memory:" was a fresh database on every open; so is this.
        return TEST_SCHEMA_PREFIX + uuid.uuid4().hex[:20]
    digest = hashlib.sha1(os.path.abspath(db_path).encode()).hexdigest()[:20]
    return TEST_SCHEMA_PREFIX + digest


def connect(schema: str) -> psycopg.Connection:
    """A connection whose unqualified table names resolve inside `schema`.
    `public` stays on the path because that is where pgvector's type lives."""
    conn = psycopg.connect(dsn(), row_factory=row_factory)
    conn.execute(f'SET search_path TO "{schema}", public')
    # Committed at once: a SET inside a transaction that later rolls back is
    # undone, and every query after it would silently run in the wrong schema.
    conn.commit()
    return conn
