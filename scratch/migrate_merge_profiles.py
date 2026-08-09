#!/usr/bin/env python3
"""Migration script to merge duplicate user profiles caused by language prompt typos.

Usage:
    python3 scratch/migrate_merge_profiles.py [db_path] [--dry-run]
"""

import sys
import os
import argparse
import sqlite3
from typing import Dict, List

# Ensure parent directory is in sys.path so app modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import db
from app.i18n import normalize_language


def plan_and_merge_profiles(db_path: str, dry_run: bool = False) -> Dict:
    """Group user profiles by normalized language and merge duplicates into canonical survivor."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Fetch all user profiles
    profiles = conn.execute(
        "SELECT id, display_name, target_lang, created_at, last_active FROM user_profiles ORDER BY id ASC"
    ).fetchall()

    # Group profiles by normalized language
    groups: Dict[str, List[sqlite3.Row]] = {}
    ignored_profiles: List[sqlite3.Row] = []

    for p in profiles:
        norm = normalize_language(p['target_lang'])
        if norm is None:
            ignored_profiles.append(p)
        else:
            groups.setdefault(norm, []).append(p)

    print("=== MIGRATION PLAN ===")
    if ignored_profiles:
        print("\nIgnored profiles (unrecognized target_lang):")
        for p in ignored_profiles:
            print(f"  Profile id {p['id']}: target_lang={p['target_lang']!r} (display_name={p['display_name']!r})")

    merges = []
    total_sessions_to_move = 0
    total_task_logs_to_move = 0
    total_vocab_log_to_move = 0

    for norm, prof_list in groups.items():
        if len(prof_list) <= 1:
            continue

        # Survivor selection rule:
        # Keep profile whose target_lang is already canonical (i.e. p['target_lang'] == norm),
        # or lowest id if none is.
        survivor = min(prof_list, key=lambda p: (0 if p['target_lang'] == norm else 1, p['id']))
        duplicates = [p for p in prof_list if p['id'] != survivor['id']]

        dup_ids = [p['id'] for p in duplicates]
        dup_ids_str = ", ".join(map(str, dup_ids))

        placeholders = ", ".join("?" for _ in dup_ids)
        num_sessions = conn.execute(f"SELECT COUNT(*) FROM sessions WHERE user_id IN ({placeholders})", dup_ids).fetchone()[0]
        num_task_logs = conn.execute(f"SELECT COUNT(*) FROM task_logs WHERE user_id IN ({placeholders})", dup_ids).fetchone()[0]
        num_vocab_log = conn.execute(f"SELECT COUNT(*) FROM vocab_log WHERE user_id IN ({placeholders})", dup_ids).fetchone()[0]

        total_sessions_to_move += num_sessions
        total_task_logs_to_move += num_task_logs
        total_vocab_log_to_move += num_vocab_log

        merges.append({
            'norm': norm,
            'survivor': survivor,
            'duplicates': duplicates,
            'num_sessions': num_sessions,
            'num_task_logs': num_task_logs,
            'num_vocab_log': num_vocab_log,
        })

        print(f"\nGroup '{norm}':")
        print(f"  Survivor: id {survivor['id']} (target_lang={survivor['target_lang']!r})")
        print(f"  Duplicates to merge into id {survivor['id']}: ids [{dup_ids_str}]")
        print(f"  Rows to move: sessions={num_sessions}, task_logs={num_task_logs}, vocab_log={num_vocab_log}")

    if not merges:
        print("\nNo duplicate profiles to merge. Database is already clean.")

    print(f"\nTotal rows to move: sessions={total_sessions_to_move}, task_logs={total_task_logs_to_move}, vocab_log={total_vocab_log_to_move}")

    if dry_run:
        print("\n[DRY RUN] Plan calculated above. No changes made.")
        conn.close()
        return {
            'dry_run': True,
            'merges_count': len(merges),
            'sessions_moved': total_sessions_to_move,
            'task_logs_moved': total_task_logs_to_move,
            'vocab_log_moved': total_vocab_log_to_move,
        }

    count_sessions_before = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    count_tasks_before = conn.execute("SELECT COUNT(*) FROM task_logs").fetchone()[0]
    count_vocab_before = conn.execute("SELECT COUNT(*) FROM vocab_log").fetchone()[0]

    conn.execute("BEGIN IMMEDIATE")
    try:
        for m in merges:
            survivor_id = m['survivor']['id']
            norm = m['norm']
            dup_ids = [p['id'] for p in m['duplicates']]
            placeholders = ", ".join("?" for _ in dup_ids)

            conn.execute(f"UPDATE sessions SET user_id = ? WHERE user_id IN ({placeholders})", [survivor_id] + dup_ids)
            conn.execute(f"UPDATE task_logs SET user_id = ? WHERE user_id IN ({placeholders})", [survivor_id] + dup_ids)
            conn.execute(f"UPDATE vocab_log SET user_id = ? WHERE user_id IN ({placeholders})", [survivor_id] + dup_ids)

            conn.execute("UPDATE user_profiles SET target_lang = ? WHERE id = ?", (norm, survivor_id))

            conn.execute(f"DELETE FROM user_profiles WHERE id IN ({placeholders})", dup_ids)

        for norm, prof_list in groups.items():
            if len(prof_list) == 1:
                p = prof_list[0]
                if p['target_lang'] != norm:
                    conn.execute("UPDATE user_profiles SET target_lang = ? WHERE id = ?", (norm, p['id']))

        count_sessions_after = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        count_tasks_after = conn.execute("SELECT COUNT(*) FROM task_logs").fetchone()[0]
        count_vocab_after = conn.execute("SELECT COUNT(*) FROM vocab_log").fetchone()[0]

        assert count_sessions_before == count_sessions_after, (
            f"Sessions row count mismatch! Before: {count_sessions_before}, After: {count_sessions_after}"
        )
        assert count_tasks_before == count_tasks_after, (
            f"Task logs row count mismatch! Before: {count_tasks_before}, After: {count_tasks_after}"
        )
        assert count_vocab_before == count_vocab_after, (
            f"Vocab log row count mismatch! Before: {count_vocab_before}, After: {count_vocab_after}"
        )

        conn.commit()
        print("\nMigration committed successfully. All row counts reconciled.")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR during migration: {e}. Transaction rolled back.")
        conn.close()
        raise

    conn.close()
    return {
        'dry_run': False,
        'merges_count': len(merges),
        'sessions_moved': total_sessions_to_move,
        'task_logs_moved': total_task_logs_to_move,
        'vocab_log_moved': total_vocab_log_to_move,
    }


def main():
    parser = argparse.ArgumentParser(description="Merge duplicate user profiles in language coach database.")
    parser.add_argument("db_path", nargs="?", default=db.DB_PATH, help="Path to SQLite database file")
    parser.add_argument("--dry-run", action="store_true", help="Print plan and exit without modifying database")
    args = parser.parse_args()

    plan_and_merge_profiles(args.db_path, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
