#!/usr/bin/env python3
import os
import sys
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import db
from scratch.migrate_merge_profiles import plan_and_merge_profiles

temp_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'temp_demo.db'))
if os.path.exists(temp_db_path):
    os.remove(temp_db_path)

conn = db.init_db(temp_db_path)
now = db._utcnow()

# Seed exact five profiles
conn.execute("INSERT INTO user_profiles (id, display_name, target_lang, created_at, last_active) VALUES (1, 'learner', 'en', ?, ?)", (now, now))
conn.execute("INSERT INTO user_profiles (id, display_name, target_lang, created_at, last_active) VALUES (2, 'learner', 'ำen', ?, ?)", (now, now))
conn.execute("INSERT INTO user_profiles (id, display_name, target_lang, created_at, last_active) VALUES (3, 'learner', 'ำ en', ?, ?)", (now, now))
conn.execute("INSERT INTO user_profiles (id, display_name, target_lang, created_at, last_active) VALUES (4, 'learner', 'English', ?, ?)", (now, now))
conn.execute("INSERT INTO user_profiles (id, display_name, target_lang, created_at, last_active) VALUES (5, 'learner', 'Japanese', ?, ?)", (now, now))

# Seed rows spread across profiles
s1 = db.create_session(conn, 1, 'Hotel Check-in', 'English', 'polite', None, 5)
s2 = db.create_session(conn, 2, 'Hotel Check-in', 'English', 'polite', None, 5)
s3 = db.create_session(conn, 3, 'Hotel Check-in', 'English', 'polite', None, 5)
s4 = db.create_session(conn, 4, 'Hotel Check-in', 'English', 'polite', None, 5)
s5 = db.create_session(conn, 5, 'Hotel Check-in', 'Japanese', 'polite', None, 5)

db.log_task(conn, s1, 'Hotel Check-in', 1, 0, 'Goal 1', 'Done 1', 'standard', 1, 'completed', 1, now, now)
db.log_task(conn, s2, 'Hotel Check-in', 2, 0, 'Goal 2', 'Done 2', 'standard', 1, 'completed', 1, now, now)
db.log_task(conn, s3, 'Hotel Check-in', 3, 0, 'Goal 3', 'Done 3', 'standard', 1, 'completed', 1, now, now)
db.log_task(conn, s4, 'Hotel Check-in', 4, 0, 'Goal 4', 'Done 4', 'standard', 1, 'completed', 1, now, now)
db.log_task(conn, s5, 'Hotel Check-in', 5, 0, 'Goal 5', 'Done 5', 'standard', 1, 'completed', 1, now, now)

db.log_vocab(conn, 1, 'English', 'word1', 'exp1', 'Hotel Check-in')
db.log_vocab(conn, 2, 'English', 'word2', 'exp2', 'Hotel Check-in')
db.log_vocab(conn, 3, 'English', 'word3', 'exp3', 'Hotel Check-in')
db.log_vocab(conn, 4, 'English', 'word4', 'exp4', 'Hotel Check-in')
db.log_vocab(conn, 5, 'Japanese', 'word5', 'exp5', 'Hotel Check-in')

conn.commit()

print("--- BEFORE MERGE ---")
profiles_before = conn.execute("SELECT id, target_lang FROM user_profiles ORDER BY id ASC").fetchall()
for p in profiles_before:
    print(f"Profile id {p['id']}: target_lang={p['target_lang']!r}")

c_s_before = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
c_t_before = conn.execute("SELECT COUNT(*) FROM task_logs").fetchone()[0]
c_v_before = conn.execute("SELECT COUNT(*) FROM vocab_log").fetchone()[0]
print(f"Row counts before: sessions={c_s_before}, task_logs={c_t_before}, vocab_log={c_v_before}\n")
conn.close()

print("--- RUNNING WITH --dry-run ---")
plan_and_merge_profiles(temp_db_path, dry_run=True)

print("\n--- RUNNING FOR REAL ---")
plan_and_merge_profiles(temp_db_path, dry_run=False)

conn = db.init_db(temp_db_path)
print("\n--- AFTER MERGE ---")
profiles_after = conn.execute("SELECT id, target_lang FROM user_profiles ORDER BY id ASC").fetchall()
for p in profiles_after:
    print(f"Profile id {p['id']}: target_lang={p['target_lang']!r}")

c_s_after = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
c_t_after = conn.execute("SELECT COUNT(*) FROM task_logs").fetchone()[0]
c_v_after = conn.execute("SELECT COUNT(*) FROM vocab_log").fetchone()[0]
print(f"Row counts after: sessions={c_s_after}, task_logs={c_t_after}, vocab_log={c_v_after}")

sess_users = [r['user_id'] for r in conn.execute("SELECT id, user_id FROM sessions ORDER BY id ASC").fetchall()]
task_users = [r['user_id'] for r in conn.execute("SELECT id, user_id FROM task_logs ORDER BY id ASC").fetchall()]
vocab_users = [r['user_id'] for r in conn.execute("SELECT id, user_id FROM vocab_log ORDER BY id ASC").fetchall()]
print(f"Sessions user_ids: {sess_users}")
print(f"Task logs user_ids: {task_users}")
print(f"Vocab log user_ids: {vocab_users}")
conn.close()
