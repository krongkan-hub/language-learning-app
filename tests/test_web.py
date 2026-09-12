"""Web front end: the state machine, and the rules it has to enforce."""
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import db, web


GREETING = ("Good afternoon, welcome in. What can I do for you today?\n\n"
            "word: sommelier\nexplanation: the staff member who advises on wine\n"
            "encourage: Ask the sommelier for a pairing.")
NPC_REPLY = "Certainly, right this way."
CLEAN = '💡 Feedback: Perfectly natural!'
CORRECTION = '💡 Feedback:\n- ❌ "two bottle" → ✅ "two bottles" (after a number, use the plural)'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('LANGUAGE_COACH_DB', str(tmp_path / 'web.db'))
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'web.db'))
    web.SESSIONS.clear()
    with TestClient(web.app) as c:
        yield c


def _patched(coach=CLEAN, judge=(True, None), actor=NPC_REPLY):
    def fake_stream(messages, system_prompt, **kw):
        cb = kw.get('callback')
        if cb:
            cb(actor.split('.')[0] + '.')
        return actor

    return (
        patch.object(web, 'translate_hints',
                     side_effect=lambda tasks, lang: {(i, t.goal): t.goal
                                                      for i, t in enumerate(tasks)}),
        patch.object(web, 'call_actor', side_effect=lambda *a, **k: GREETING),
        patch.object(web, 'stream_actor', side_effect=fake_stream),
        patch.object(web, 'call_coach', side_effect=lambda *a, **k: coach),
        patch.object(web, 'evaluate_task', side_effect=lambda *a, **k: judge),
    )


def _start(client, **kw):
    patches = _patched(**kw)
    for p in patches:
        p.start()
    scenarios = client.get('/api/scenarios?language=English').json()['scenarios']
    r = client.post('/api/session', json={'language': 'English',
                                          'scenario': scenarios[0]['name'],
                                          'tasks': 3})
    assert r.status_code == 200, r.text
    sid = r.json()['session']
    sess = web.SESSIONS[sid]
    for _ in range(200):                       # greeting runs off-thread
        if sess.state == web.AWAITING_INPUT:
            break
        time.sleep(0.01)
    return sid, sess, patches


def _stop(patches):
    for p in patches:
        p.stop()


def _drain(sess):
    out = []
    while not sess.events.empty():
        out.append(sess.events.get())
    return out


def test_a_session_starts_with_a_greeting_and_then_waits(client):
    sid, sess, patches = _start(client)
    try:
        kinds = [e['type'] for e in _drain(sess)]
        assert 'tasks' in kinds and 'npc' in kinds
        assert sess.state == web.AWAITING_INPUT
    finally:
        _stop(patches)


def test_the_drill_cannot_be_bypassed_by_posting_a_turn(client):
    """The CLI drill is a `while True` with no skip. Enforcing that by
    disabling an input box would leave it bypassable from the browser console,
    so the server refuses a turn while a drill is open — the rule lives where
    the learner cannot reach it."""
    sid, sess, patches = _start(client, coach=CORRECTION)
    try:
        client.post(f'/api/turn/{sid}', json={'text': 'Can I get two bottle of water?'})
        for _ in range(300):
            if sess.state == web.DRILL:
                break
            time.sleep(0.01)
        assert sess.state == web.DRILL

        blocked = client.post(f'/api/turn/{sid}', json={'text': 'moving on anyway'})
        assert blocked.status_code == 409, blocked.text

        wrong = client.post(f'/api/drill/{sid}', json={'text': 'two bottle'})
        assert wrong.json()['correct'] is False
        assert sess.state == web.DRILL           # still stuck, as intended

        right = client.post(f'/api/drill/{sid}', json={'text': 'two bottles'})
        assert right.json() == {'correct': True, 'remaining': 0}
        assert sess.state == web.AWAITING_INPUT

        assert client.post(f'/api/turn/{sid}', json={'text': 'thank you'}).status_code == 200
    finally:
        _stop(patches)


def test_a_clean_verdict_runs_no_drill(client):
    sid, sess, patches = _start(client, coach=CLEAN)
    try:
        client.post(f'/api/turn/{sid}', json={'text': 'A table for two, please.'})
        for _ in range(300):
            if sess.state in (web.AWAITING_INPUT, web.FINISHED):
                break
            time.sleep(0.01)
        assert sess.state != web.DRILL
        assert client.post(f'/api/drill/{sid}', json={'text': 'x'}).status_code == 409
    finally:
        _stop(patches)


def test_the_npc_speaks_before_the_coach(client):
    """Same ordering the CLI was given in 7e312f0, for the same reason: the
    learner should have the reply on screen before the feedback arrives."""
    sid, sess, patches = _start(client, coach=CORRECTION)
    try:
        _drain(sess)
        client.post(f'/api/turn/{sid}', json={'text': 'Can I get two bottle of water?'})
        for _ in range(300):
            if sess.state == web.DRILL:
                break
            time.sleep(0.01)
        kinds = [e['type'] for e in _drain(sess)]
        assert 'npc' in kinds and 'coach' in kinds
        assert kinds.index('npc') < kinds.index('coach'), kinds
        # And the judge ran before the actor, because the actor prompt needs it.
        assert kinds.index('tasks') < kinds.index('npc'), kinds
    finally:
        _stop(patches)


def test_a_failed_task_is_counted(client):
    """OPEN-25 parity: the CLI counted a skipped task and not a failed one for
    its whole life. The web front end must not reintroduce that."""
    sid, sess, patches = _start(client, judge=(False, 'not yet'), coach=CLEAN)
    try:
        for i in range(web.MAX_TASK_ATTEMPTS):
            client.post(f'/api/turn/{sid}', json={'text': f'attempt {i}'})
            for _ in range(300):
                if sess.state in (web.AWAITING_INPUT, web.FINISHED):
                    break
                time.sleep(0.01)
        assert sess.tasks_skipped == 1, (sess.tasks_skipped, sess.task_idx)
        assert sess.tasks_done == 0
    finally:
        _stop(patches)


def test_stats_and_strings_follow_the_requested_language(client):
    """UI labels come from the same 71 i18n keys the CLI uses, in the language
    being studied — no parallel translation table for the web."""
    en = client.get('/api/strings?language=English').json()
    ja = client.get('/api/strings?language=Japanese').json()
    assert en['strings'] != ja['strings']
    assert ja['language'] == 'Japanese'

    s = client.get('/api/stats?language=Japanese').json()
    assert s['language'] == 'Japanese'
    assert 'overall' in s and 'vocab' in s


def test_unknown_session_and_language_are_refused(client):
    assert client.get('/api/stream/nope').status_code == 404
    assert client.post('/api/turn/nope', json={'text': 'hi'}).status_code == 404
    r = client.post('/api/session', json={'language': 'Klingon', 'scenario': 'x'})
    assert r.status_code == 400
