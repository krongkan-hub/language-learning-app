"""Copy a learner's old SQLite database into PostgreSQL, once.

    python -m app.db.import_sqlite                     # ~/.language-coach/sessions.db
    python -m app.db.import_sqlite path/to/old.db

The SQLite file is first brought to its final shape by the migrations in
legacy_sqlite.py (so any database this project ever wrote imports), then
every table is copied parent-first with its ids kept, the identity sequences
are moved past them, and explain sessions from before sessions.kind existed
are re-labelled. The source file is only read; importing into a schema that
already holds data is refused, so running it twice cannot duplicate history.
"""
import os
import sys

from . import init_db
from .legacy_sqlite import open_upgraded
from .schema import TABLES, backfill_explain_kind

# NOT NULL columns an old file may lack or leave empty, and the SQLite
# expression that fills them: user_profiles had updated_at, not last_active,
# before the dynamic_scenarios era ended, and a display_name could be NULL.
FILL = {
    'user_profiles': {'display_name': "COALESCE(display_name, 'learner')",
                      'target_lang': "COALESCE(target_lang, 'English')",
                      'last_active': 'created_at'},
}

DEFAULT_SOURCE = os.path.join(os.path.expanduser('~'), '.language-coach', 'sessions.db')


def _pg_columns(pg, table: str) -> list:
    return [r[0] for r in pg.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s "
        "ORDER BY ordinal_position", (table,))]


def import_sqlite(source_path: str, pg) -> dict:
    """Copy every row of `source_path` into the schema `pg` is connected to.
    Returns {table: rows copied}."""
    if any(pg.execute(f'SELECT 1 FROM {t} LIMIT 1').fetchone() for t in TABLES):
        raise RuntimeError('the target schema already holds data; refusing to import twice')
    src = open_upgraded(source_path)
    copied = {}
    try:
        for table in TABLES:
            src_cols = [r[1] for r in src.execute(f'PRAGMA table_info({table})')]
            fill = FILL.get(table, {})
            cols = [c for c in _pg_columns(pg, table) if c in src_cols or c in fill]
            exprs = [c if c in src_cols and c not in fill else
                     (fill[c] if c in fill and (c not in src_cols or 'COALESCE' in fill[c]) else c)
                     for c in cols]
            values = ', '.join('%s::vector' if c == 'embedding' else '%s' for c in cols)
            rows = src.execute(f'SELECT {", ".join(exprs)} FROM {table} ORDER BY id').fetchall()
            for row in rows:
                pg.execute(f'INSERT INTO {table} ({", ".join(cols)}) VALUES ({values})', tuple(row))
            if rows:
                pg.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                           f"(SELECT MAX(id) FROM {table}))")
            copied[table] = len(rows)
        pg.commit()
    finally:
        src.close()
    backfill_explain_kind(pg)
    return copied


def main(argv) -> int:
    source = argv[1] if len(argv) > 1 else DEFAULT_SOURCE
    if not os.path.isfile(source):
        print(f'No SQLite database at {source}')
        return 1
    pg = init_db()
    try:
        for table, n in import_sqlite(source, pg).items():
            print(f'  {table:14} {n} rows')
    finally:
        pg.close()
    print('Imported. The SQLite file was not changed.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
