import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from app import db

temp_db_path = os.path.abspath('scratch/temp_test_sessions.db')
if os.path.exists(temp_db_path):
    os.remove(temp_db_path)

conn = db.init_db(temp_db_path)
uid = db.get_or_create_user(conn, 'learner', 'English')
now = db._utcnow()

s1 = db.create_session(conn, uid, 'Hotel Check-in', 'English', 'polite', None, 10)
db.log_task(conn, s1, 'Hotel Check-in', uid, 0, 'Confirm reservation', 'Done', 'standard', 1, 'completed', 1, now, now)
db.log_task(conn, s1, 'Hotel Check-in', uid, 1, 'Ask for high floor', 'Done', 'standard', 1, 'completed', 1, now, now)
db.finish_session(conn, s1, tasks_done=8, tasks_skipped=2)

s2 = db.create_session(conn, uid, 'Hotel Check-in', 'English', 'polite', None, 10)
db.finish_session(conn, s2, tasks_done=7, tasks_skipped=3)

s3 = db.create_session(conn, uid, 'Car Rental Agency', 'English', 'polite', None, 10)
db.log_task(conn, s3, 'Car Rental Agency', uid, 0, 'Choose vehicle type', 'Done', 'standard', 1, 'completed', 1, now, now)
db.finish_session(conn, s3, tasks_done=6, tasks_skipped=4)

db.log_vocab(conn, uid, 'English', 'reservation', 'an arrangement to secure a room', 'Hotel Check-in')
db.log_vocab(conn, uid, 'English', 'upgrade', 'raise to a higher grade or standard', 'Hotel Check-in')
db.log_vocab(conn, uid, 'English', 'deposit', 'a sum payable as a first installment', 'Car Rental Agency')

db.mark_vocab_reviewed(conn, uid, 'English', 'reservation', True)
db.mark_vocab_reviewed(conn, uid, 'English', 'reservation', True)
db.mark_vocab_reviewed(conn, uid, 'English', 'reservation', True)

db.mark_vocab_reviewed(conn, uid, 'English', 'upgrade', True)

conn.close()
print(f"Seeded temporary DB at {temp_db_path}")
