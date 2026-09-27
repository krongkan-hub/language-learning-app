"""The dashboard queries (app/db/analytics.py), on data whose answers are known."""
from datetime import datetime, timedelta, timezone

from app import db
from app.db import analytics


def _iso(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime('%Y-%m-%dT%H:%M:%SZ')


def _setup(tmp_path):
    conn = db.init_db(str(tmp_path / 'a.db'))
    uid = db.get_or_create_user(conn, 'learner', 'English')
    return conn, uid


def _session(conn, uid, name, days_ago, outcomes, kind='scenario'):
    sid = db.create_session(conn, uid, name, 'English', 'm', None, len(outcomes) or 1, kind=kind)
    conn.execute('UPDATE sessions SET started_at = %s, finished_at = %s WHERE id = %s',
                 (_iso(days_ago), _iso(days_ago), sid))
    for i, (outcome, tries) in enumerate(outcomes):
        db.log_task(conn, sid, name, uid, i, f'goal {i}', 'dw', 'standard', 1, outcome, tries,
                    _iso(days_ago), _iso(days_ago))
    conn.commit()
    return sid


def test_summary_counts_outcomes_words_and_repeats(tmp_path):
    conn, uid = _setup(tmp_path)
    sid = _session(conn, uid, 'Cafe', 0, [('completed', 1), ('failed', 4), ('completed', 2)])
    db.log_vocab(conn, uid, 'English', 'napkin', 'x', 'Cafe')
    db.mark_vocab_reviewed(conn, uid, 'English', 'napkin', True)
    db.log_vocab(conn, uid, 'English', 'sommelier', 'x', 'Cafe')
    for _ in range(3):
        db.mark_vocab_reviewed(conn, uid, 'English', 'sommelier', True)
    for n in ('two', 'three'):
        db.log_mistakes(conn, uid, 'English', sid, 'Cafe', f'- ❌ "{n} bottle" → ✅ "{n} bottles" (plural)')
    s = analytics.summary(conn, uid)
    assert (s['sessions'], s['attempted'], s['completed'], s['completion_rate']) == (1, 3, 2, 67)
    assert (s['taught'], s['learned'], s['due'], s['repeated_classes']) == (2, 1, 1, 1)


def test_weekly_includes_the_weeks_nobody_played(tmp_path):
    conn, uid = _setup(tmp_path)
    _session(conn, uid, 'Cafe', 0, [('completed', 1)])
    _session(conn, uid, 'Cafe', 21, [('failed', 4)])
    weeks = analytics.weekly(conn, uid, weeks=6)
    assert len(weeks) == 6
    assert sum(w['sessions'] for w in weeks) == 2
    assert any(w['sessions'] == 0 for w in weeks)
    assert weeks[-1]['completed'] == 1


def test_streak_counts_consecutive_days_ending_today(tmp_path):
    conn, uid = _setup(tmp_path)
    for d in (0, 1, 2, 5):
        _session(conn, uid, 'Cafe', d, [])
    assert analytics.streak_days(conn, uid) == 3
    conn2, uid2 = _setup(tmp_path / 'old')
    _session(conn2, uid2, 'Cafe', 9, [])
    assert analytics.streak_days(conn2, uid2) == 0          # a run that ended long ago


def test_by_scenario_puts_the_hardest_first_and_skips_explain(tmp_path):
    conn, uid = _setup(tmp_path)
    _session(conn, uid, 'Easy Cafe', 1, [('completed', 1), ('completed', 1)])
    _session(conn, uid, 'Hard Hotel', 1, [('failed', 4), ('completed', 3)])
    _session(conn, uid, 'how you get to work', 1, [('completed', 1)], kind='explain')
    rows = analytics.by_scenario(conn, uid)
    assert [r['scenario_name'] for r in rows] == ['Hard Hotel', 'Easy Cafe']
    assert rows[0]['completion_rate'] == 50 and rows[0]['avg_attempts'] == 3.5


def test_performance_reports_p50_and_p95_per_stage(tmp_path):
    conn, _ = _setup(tmp_path)
    for ms in (100, 200, 300, 400, 10_000):
        conn.execute("INSERT INTO spans (trace_id, span_id, name, started_at, duration_ms) "
                     "VALUES ('t', 's', 'actor', now(), %s)", (ms,))
    conn.execute("INSERT INTO spans (trace_id, span_id, name, started_at, duration_ms) "
                 "VALUES ('t', 's', 'actor', now() - interval '30 days', 99999)")
    conn.commit()
    rows = {r['name']: r for r in analytics.performance(conn)}
    assert rows['actor']['count'] == 5                  # the old span is outside the window
    assert rows['actor']['p50_ms'] == 300
    assert rows['actor']['p95_ms'] > 2000               # the slow turn shows in the tail
