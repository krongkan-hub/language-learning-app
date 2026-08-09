"""Migration script to purge trivial vocabulary rows from vocab_log.

Removes vocab_log rows where the word matches that scenario's name, place,
role, or speaker.

Usage:
    python3 scratch/migrate_purge_trivial_vocab.py [--dry-run] [--db DB_PATH]
"""

import argparse
import sqlite3
from app.db import DB_PATH
from app.scenarios.builtins import SCENARIOS
from app.cli import _is_trivial_vocab


def purge_trivial_vocab(db_path: str = DB_PATH, dry_run: bool = False) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Map scenario_name -> Scenario object
    sc_by_name = {s.name: s for s in SCENARIOS}

    rows = conn.execute("SELECT id, scenario_name, word, explanation FROM vocab_log").fetchall()

    to_delete = []
    for r in rows:
        sc_obj = sc_by_name.get(r['scenario_name'])
        if sc_obj and _is_trivial_vocab(r['word'], sc_obj):
            to_delete.append(r)

    if not to_delete:
        print("No trivial vocabulary rows found.")
        conn.close()
        return 0

    prefix = "[DRY RUN] Would remove" if dry_run else "Removing"
    for r in to_delete:
        print(f"{prefix} row id={r['id']}: word='{r['word']}' for scenario='{r['scenario_name']}'")

    if not dry_run:
        ids_tuple = tuple(r['id'] for r in to_delete)
        placeholders = ','.join('?' for _ in ids_tuple)
        conn.execute(f"DELETE FROM vocab_log WHERE id IN ({placeholders})", ids_tuple)
        conn.commit()
        print(f"Successfully purged {len(to_delete)} trivial vocabulary row(s).")
    else:
        print(f"[DRY RUN] {len(to_delete)} row(s) would be removed.")

    conn.close()
    return len(to_delete)


def main():
    parser = argparse.ArgumentParser(description="Purge trivial vocabulary entries from database.")
    parser.add_argument("--dry-run", action="store_true", help="Print rows to be deleted without committing changes")
    parser.add_argument("--db", type=str, default=DB_PATH, help="Path to SQLite database")
    args = parser.parse_args()

    purge_trivial_vocab(db_path=args.db, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
