import time
from app import db

conn = db.init_db(':memory:')
uid = db.get_or_create_user(conn, display_name='demo_user', target_lang='English')

# Log three words with 1.1s delays so timestamps differ by >1s
db.log_vocab(conn, uid, 'English', 'sommelier', 'a wine expert', 'Restaurant')
time.sleep(1.1)
db.log_vocab(conn, uid, 'English', 'surcharge', 'an extra fee', 'Hotel')
time.sleep(1.1)
db.log_vocab(conn, uid, 'English', 'amenity', 'a desirable feature', 'Hotel')
time.sleep(1.1)

# Log surcharge a second time (updating its last_seen_at to the latest)
db.log_vocab(conn, uid, 'English', 'surcharge', 'an extra fee', 'Hotel')

# Fetch words for review
review_words = db.get_vocab_for_review(conn, uid, 'English', limit=3)
print("Review Words Output:")
for row in review_words:
    print(f"Word: {row['word']}, Times Taught: {row['times_taught']}, Last Seen: {row['last_seen_at']}")

conn.close()
