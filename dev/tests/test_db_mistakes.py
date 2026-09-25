"""The mistakes table: logging coach corrections and grouping repeats.

See app.db._normalize_mistake_text for the normalization rule's reasoning.
"""
import sqlite3

from app import db


def _setup(tmp_path, name='mistakes.db'):
    conn = db.init_db(str(tmp_path / name))
    uid = db.get_or_create_user(conn, 'tester', 'English')
    sid = db.create_session(conn, uid, 'Coffee Shop', 'English', 'friendly', None, 5)
    return conn, uid, sid


FEEDBACK_TWO_BULLETS = (
    '💡 Feedback:\n'
    '- ❌ "two bottle" → ✅ "two bottles" (after a number, use the plural)\n'
    '- ❌ "Is it prohibit" → ✅ "Is it prohibited" (use the past participle)'
)


# --- logging -----------------------------------------------------------------

def test_log_mistakes_stores_one_row_per_bullet(tmp_path):
    conn, uid, sid = _setup(tmp_path)
    ids = db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop', FEEDBACK_TWO_BULLETS)
    assert len(ids) == 2

    rows = conn.execute("SELECT * FROM mistakes ORDER BY id").fetchall()
    assert len(rows) == 2
    assert rows[0]['quoted_text'] == 'two bottle'
    assert rows[0]['correction'] == 'two bottles'
    assert rows[0]['user_id'] == uid
    assert rows[0]['session_id'] == sid
    assert rows[0]['scenario_name'] == 'Coffee Shop'
    assert rows[0]['language'] == 'English'
    assert rows[0]['created_at']
    assert rows[1]['quoted_text'] == 'Is it prohibit'
    assert rows[1]['correction'] == 'Is it prohibited'


def test_log_mistakes_ignores_level_up_bullets(tmp_path):
    conn, uid, sid = _setup(tmp_path)
    feedback = (
        '💡 Feedback: Perfectly natural!\n\n'
        '⬆️ Level up:\n'
        '- "I want a coffee" → "I would like a coffee" (more polite)'
    )
    ids = db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop', feedback)
    assert ids == []
    assert conn.execute("SELECT COUNT(*) AS n FROM mistakes").fetchone()['n'] == 0


def test_log_mistakes_is_empty_for_a_clean_verdict(tmp_path):
    conn, uid, sid = _setup(tmp_path)
    ids = db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop',
                          '💡 Feedback: Perfectly natural!')
    assert ids == []


# --- normalization -------------------------------------------------------

def test_normalize_mistake_text_collapses_digits_and_number_words():
    from app.db import _normalize_mistake_text
    assert _normalize_mistake_text('two bottle') == _normalize_mistake_text('three bottle')
    assert _normalize_mistake_text('two bottle') == _normalize_mistake_text('2 bottle')


def test_normalize_mistake_text_collapses_subject_pronouns():
    from app.db import _normalize_mistake_text
    assert _normalize_mistake_text('I go yesterday') == _normalize_mistake_text('he go yesterday')
    assert _normalize_mistake_text('I go yesterday') == _normalize_mistake_text('She Go Yesterday')


def test_normalize_mistake_text_does_not_collapse_unrelated_mistakes():
    from app.db import _normalize_mistake_text
    assert _normalize_mistake_text('two bottle') != _normalize_mistake_text('Is it prohibit')
    assert (_normalize_mistake_text('I go yesterday')
            != _normalize_mistake_text('I goes yesterday'))


def test_normalize_mistake_text_strips_punctuation_and_case():
    from app.db import _normalize_mistake_text
    assert _normalize_mistake_text('Is it prohibit?') == _normalize_mistake_text('is it PROHIBIT')


# --- grouping repeats ------------------------------------------------------

def test_repeated_mistakes_groups_same_class_across_number_words(tmp_path):
    conn, uid, sid = _setup(tmp_path)
    db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop',
                    '- ❌ "two bottle" → ✅ "two bottles" (after a number, use the plural)')
    db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop',
                    '- ❌ "three bottle" → ✅ "three bottles" (after a number, use the plural)')

    results = db.repeated_mistakes(conn, uid, 'English')
    assert len(results) == 1
    assert results[0]['occurrences'] == 2
    assert results[0]['example_quoted'] == 'three bottle'
    assert results[0]['example_correction'] == 'three bottles'


def test_repeated_mistakes_groups_same_class_across_subject_pronouns(tmp_path):
    conn, uid, sid = _setup(tmp_path)
    db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop',
                    '- ❌ "I go yesterday" → ✅ "I went yesterday" (past tense)')
    db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop',
                    '- ❌ "he go yesterday" → ✅ "he went yesterday" (past tense)')

    results = db.repeated_mistakes(conn, uid, 'English')
    assert len(results) == 1
    assert results[0]['occurrences'] == 2


def test_repeated_mistakes_excludes_singletons(tmp_path):
    conn, uid, sid = _setup(tmp_path)
    db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop', FEEDBACK_TWO_BULLETS)
    assert db.repeated_mistakes(conn, uid, 'English') == []


def test_repeated_mistakes_orders_by_occurrences_then_recency(tmp_path):
    conn, uid, sid = _setup(tmp_path)
    # "two bottle" class: 3 occurrences
    for phrase in ('two', 'three', 'four'):
        db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop',
                        f'- ❌ "{phrase} bottle" → ✅ "{phrase} bottles" (plural)')
    # "go yesterday" class: 2 occurrences
    for who in ('I', 'he'):
        db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop',
                        f'- ❌ "{who} go yesterday" → ✅ "{who} went yesterday" (past tense)')

    results = db.repeated_mistakes(conn, uid, 'English', limit=3)
    assert [r['occurrences'] for r in results] == [3, 2]


def test_repeated_mistakes_respects_limit(tmp_path):
    conn, uid, sid = _setup(tmp_path)
    # Three distinct mistake classes (distinct even after normalization —
    # different verbs/objects, not just a different number or pronoun),
    # each repeated twice.
    classes = [
        ('two bottle', 'two bottles', 'three bottle', 'three bottles'),
        ('he go store', 'he goes store', 'she go store', 'she goes store'),
        ('I eat apple', 'I ate apple', 'he eat apple', 'he ate apple'),
    ]
    for said1, better1, said2, better2 in classes:
        for said, better in ((said1, better1), (said2, better2)):
            db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop',
                            f'- ❌ "{said}" → ✅ "{better}" (correction)')
    results = db.repeated_mistakes(conn, uid, 'English', limit=2)
    assert len(results) == 2


def test_repeated_mistakes_scoped_to_user_and_language(tmp_path):
    conn, uid, sid = _setup(tmp_path)
    other_uid = db.get_or_create_user(conn, 'other', 'English')
    other_sid = db.create_session(conn, other_uid, 'Coffee Shop', 'English', 'friendly', None, 5)
    for uid_, sid_ in ((uid, sid), (other_uid, other_sid)):
        db.log_mistakes(conn, uid_, 'English', sid_, 'Coffee Shop',
                        '- ❌ "two bottle" → ✅ "two bottles" (plural)')
        db.log_mistakes(conn, uid_, 'English', sid_, 'Coffee Shop',
                        '- ❌ "three bottle" → ✅ "three bottles" (plural)')

    results = db.repeated_mistakes(conn, uid, 'English')
    assert len(results) == 1  # not double-counted across users

    ja_results = db.repeated_mistakes(conn, uid, 'Japanese')
    assert ja_results == []  # not leaking across languages


def test_repeated_mistakes_empty_for_user_with_no_mistakes(tmp_path):
    conn, uid, sid = _setup(tmp_path)
    assert db.repeated_mistakes(conn, uid, 'English') == []


# --- migration ---------------------------------------------------------------

def test_migration_adds_mistakes_table_to_a_pre_existing_database(tmp_path):
    """A database created before this feature shipped had no `mistakes`
    table. init_db must add it in place, without losing existing data."""
    db_path = str(tmp_path / 'legacy.db')
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL DEFAULT 'learner',
            target_lang TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_active TEXT NOT NULL
        );
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES user_profiles(id),
            scenario_name TEXT NOT NULL,
            language TEXT NOT NULL,
            mood TEXT NOT NULL,
            complication TEXT,
            tasks_total INTEGER NOT NULL,
            tasks_done INTEGER NOT NULL DEFAULT 0,
            tasks_skipped INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            kind TEXT NOT NULL DEFAULT 'scenario'
        );
    """)
    conn.execute(
        "INSERT INTO user_profiles (display_name, target_lang, created_at, last_active) "
        "VALUES ('legacy', 'English', 't', 't')"
    )
    conn.commit()
    conn.close()

    have = {r[0] for r in sqlite3.connect(db_path).execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert 'mistakes' not in have

    conn = db.init_db(db_path)
    have = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert 'mistakes' in have

    # existing data survived the migration
    row = conn.execute("SELECT display_name FROM user_profiles").fetchone()
    assert row['display_name'] == 'legacy'

    # and the new table is fully usable
    uid = conn.execute("SELECT id FROM user_profiles").fetchone()['id']
    sid = db.create_session(conn, uid, 'Coffee Shop', 'English', 'friendly', None, 5)
    ids = db.log_mistakes(conn, uid, 'English', sid, 'Coffee Shop', FEEDBACK_TWO_BULLETS)
    assert len(ids) == 2


def test_migration_is_idempotent_on_a_database_that_already_has_the_table(tmp_path):
    db_path = str(tmp_path / 'current.db')
    conn = db.init_db(db_path)
    conn.close()
    # second init_db on the same, already-migrated file must not error
    conn = db.init_db(db_path)
    have = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert 'mistakes' in have
