"""Web front end: the state machine, and the rules it has to enforce."""
import pathlib
import re
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


def test_a_session_can_start_without_naming_a_scenario(client):
    """The scenario is chosen for the learner. Picking from a list of 80 turns
    every session into a decision, and a learner choosing for themselves drifts
    toward the scenarios they already find easy."""
    patches = _patched()
    for p in patches:
        p.start()
    try:
        r = client.post('/api/session', json={'language': 'English', 'tasks': 3})
        assert r.status_code == 200, r.text
        assert r.json()['scenario']
    finally:
        _stop(patches)


def test_the_random_draw_prefers_the_least_played(client):
    """Uniform random keeps re-serving what the learner has already done nine
    times. The draw is restricted to the least-played band, then randomised
    inside it."""
    from app import web as w

    class S:
        def __init__(self, name):
            self.name = name

    catalogue = [S('played'), S('fresh_a'), S('fresh_b')]
    stats = {'played': {'plays': 9}, 'fresh_a': {'plays': 0}, 'fresh_b': {'plays': 0}}
    with patch.object(w.db, 'get_all_scenario_stats', return_value=stats):
        picks = {w._random_scenario(None, 1, catalogue).name for _ in range(40)}
    assert picks <= {'fresh_a', 'fresh_b'}, picks
    assert len(picks) == 2, picks       # still random inside the band


def test_skip_moves_on_but_not_during_a_drill(client):
    """The CLI has had `skip` since the beginning; the web front end had no way
    out of a task, so a learner stuck on one could only reload. It is refused
    mid-drill for the same reason a turn is."""
    sid, sess, patches = _start(client, coach=CORRECTION)
    try:
        before = sess.task_idx
        r = client.post(f'/api/skip/{sid}')
        assert r.status_code == 200, r.text
        assert sess.task_idx == before + 1
        assert sess.tasks_skipped == 1

        client.post(f'/api/turn/{sid}', json={'text': 'Can I get two bottle of water?'})
        for _ in range(300):
            if sess.state == web.DRILL:
                break
            time.sleep(0.01)
        assert client.post(f'/api/skip/{sid}').status_code == 409
    finally:
        _stop(patches)


def test_a_disconnected_stream_finishes_the_session(client):
    """Closing the tab left the session unfinished forever — 13 such rows had
    built up in the real database, one per abandoned tab. The stream ending is
    the best available signal that nobody is watching.

    Driven through the generator rather than TestClient: an SSE response never
    completes, so `client.stream(...)` waits for an end that never comes and
    hangs the suite. Closing the generator is exactly what a dropped client
    does to it.
    """
    sid, sess, patches = _start(client)
    try:
        import asyncio
        body = web.stream(sid).body_iterator   # StreamingResponse makes it async
        loop = asyncio.new_event_loop()
        try:
            sess.emit('ping')
            loop.run_until_complete(body.__anext__())   # one event...
            loop.run_until_complete(body.aclose())      # ...then the client goes
        finally:
            loop.close()

        assert sess.state == web.FINISHED
        assert sid not in web.SESSIONS

        conn = db.init_db()
        row = conn.execute(
            'SELECT finished_at FROM sessions WHERE id = ?',
            (sess.db_session_id,)).fetchone()
        assert row['finished_at'] is not None
        conn.close()
    finally:
        _stop(patches)


def test_a_failed_turn_leaves_the_session_usable(client):
    """MLX can fail mid-turn — a model load error, an out-of-memory. The worker
    catches it, but the question is what the learner is left with: a session
    they can carry on with, or a dead page."""
    sid, sess, patches = _start(client)
    try:
        _drain(sess)
        with patch.object(web, 'evaluate_task', side_effect=RuntimeError('MLX engine error')):
            client.post(f'/api/turn/{sid}', json={'text': 'hello there'})
            for _ in range(300):
                if sess.state == web.AWAITING_INPUT:
                    break
                time.sleep(0.01)

        events = _drain(sess)
        errors = [e for e in events if e['type'] == 'error']
        assert errors, events
        # The learner gets a sentence they can act on, not a traceback. The raw
        # exception used to go into the conversation verbatim — including the
        # local filesystem path out of an MLX model-load failure.
        err = errors[0]
        # The headline is a learner-facing sentence from the i18n table, in the
        # language being studied; the technical text is demoted to `detail`.
        # Before, the whole message WAS the exception — including the local
        # filesystem path out of an MLX model-load failure, printed where the
        # NPC's reply belongs.
        assert err['message'] and 'MLX' not in err['message']
        assert 'Traceback' not in err['message']
        assert 'MLX Engine Error' in err['detail']
        # The learner must be able to try again rather than reload.
        assert sess.state == web.AWAITING_INPUT
        assert client.post(f'/api/turn/{sid}', json={'text': 'trying again'}).status_code == 200
    finally:
        _stop(patches)


def test_two_sessions_run_independently(client):
    """Two tabs are two sessions. `_llm_lock` serialises the model calls, so
    they cannot corrupt each other's turn — but they must not share state
    either: a task ticked in one must not tick in the other."""
    patches = _patched(judge=(True, None))
    for p in patches:
        p.start()
    try:
        scen = client.get('/api/scenarios?language=English').json()['scenarios']
        a = client.post('/api/session', json={'language': 'English',
                                              'scenario': scen[0]['name'], 'tasks': 3}).json()['session']
        b = client.post('/api/session', json={'language': 'English',
                                              'scenario': scen[1]['name'], 'tasks': 3}).json()['session']
        assert a != b
        sa, sb = web.SESSIONS[a], web.SESSIONS[b]
        for _ in range(300):
            if sa.state == web.AWAITING_INPUT and sb.state == web.AWAITING_INPUT:
                break
            time.sleep(0.01)

        client.post(f'/api/turn/{a}', json={'text': 'a table for two'})
        for _ in range(300):
            if sa.tasks_done:
                break
            time.sleep(0.01)
        assert sa.tasks_done == 1
        assert sb.tasks_done == 0, 'sessions are sharing progress'
        assert sa.scenario.name != sb.scenario.name
        assert sa.messages is not sb.messages
    finally:
        _stop(patches)


def test_the_page_is_served_revalidating_not_from_cache(client):
    # index.html IS the front end — markup, style and script in one file — so a
    # cached copy means an edit silently does not reach the browser. It cost me
    # a round of measuring a layout fix that was already on disk.
    r = client.get('/')
    assert r.status_code == 200
    assert r.headers['cache-control'] == 'no-cache'


def test_the_landing_subtitle_cannot_reflow_the_cards():
    # The subtitle starts as a fixed string and is replaced by fetched stats a
    # moment later. Letting it wrap grew each card 24px AFTER the page looked
    # ready, so a click aimed at a card landed where the card no longer was.
    # Pinning it to one line is what keeps the height constant.
    css = (pathlib.Path(web.__file__).parent / 'static' / 'index.html').read_text()
    rule = css.split('.lang span {')[1].split('}')[0]
    assert 'white-space:nowrap' in rule
    assert 'display:block' in rule


def test_every_append_to_the_log_pins_the_scroll():
    # #drill sits in normal flow, so opening it shrinks #log — and a scroll
    # container that shrinks keeps its scrollTop, leaving the newest lines
    # below the fold. Measured: 122px of conversation hidden, including the
    # banker's question the learner was about to answer. One append (the
    # vocabulary card) had never pinned at all.
    page = (pathlib.Path(web.__file__).parent / 'static' / 'index.html').read_text()
    appends = [m for m in re.finditer(r"\$\('log'\)\.appendChild\([^)]*\);", page)]
    assert len(appends) == 3, 'appends moved; this check needs rewriting'
    for m in appends:
        tail = page[m.end():m.end() + 40]
        assert 'pin()' in tail, f'append at offset {m.start()} does not pin the scroll'
    # plus the streaming-sentence handler and both drill transitions, which
    # move or resize #log without appending anything
    assert page.count('pin();') >= len(appends) + 3


def test_a_japanese_session_gets_a_japanese_chrome(client):
    # A Japanese session showed Japanese scenario, tasks and dialogue inside an
    # English chrome: thirteen labels were hardcoded in index.html while
    # /api/strings' docstring claimed the web "adds no parallel translation
    # table". Measured in the running page, not guessed.
    served = client.get('/api/strings?language=Japanese').json()['strings']
    for key in ('web_skip_task', 'web_end', 'web_send', 'web_tasks', 'web_coach',
                'web_vocabulary', 'web_coach_empty', 'web_vocab_empty',
                'web_progress', 'web_browse', 'web_close', 'web_search',
                'web_again', 'web_review', 'web_input_placeholder'):
        assert key in served, key
        assert served[key], key
        assert not re.fullmatch(r'[\x20-\x7E]+', served[key]), (
            f'{key} came back as ASCII in a Japanese session: {served[key]!r}')

    english = client.get('/api/strings?language=English').json()['strings']
    assert english['web_send'] == 'Send'


def test_the_page_has_no_second_translation_table_left():
    # The inline `lang === "Japanese" ? … : …` ternaries were the same bug in
    # a different shape: a label translated in the markup instead of i18n.py.
    page = (pathlib.Path(web.__file__).parent / 'static' / 'index.html').read_text()
    body = page.split('applyStrings')[-1]
    assert "==='Japanese' ?" not in body.replace(' ', '').replace("=== 'Japanese' ?", "==='Japanese' ?")
    for label in ('Skip task', 'Practise again', 'Review conversation'):
        # still present as the HTML default, but must not be set from JS
        assert f"= '{label}'" not in page and f'= "{label}"' not in page


def test_the_summary_colours_the_score_by_the_score():
    # 0/10 was rendered in var(--good), the success green, so a learner who
    # finished nothing got a celebratory zero. Zero is not a rebuke either, so
    # it takes the muted ink rather than the error red.
    page = (pathlib.Path(web.__file__).parent / 'static' / 'index.html').read_text()
    rule = page.split('#doneCard .big {')[1].split('}')[0]
    assert 'var(--good)' not in rule, 'the default is green again'
    assert '#doneCard .big.none { color:var(--dim); }' in page
    assert '#doneCard .big.most { color:var(--good); }' in page
    assert "$('doneScore').className = 'big'" in page


def test_a_normal_end_does_not_tell_the_learner_to_reload():
    # The SSE stream drops when a session ends normally too, and onerror told
    # the learner to reload — beside a "Practise again" button that works.
    page = (pathlib.Path(web.__file__).parent / 'static' / 'index.html').read_text()
    assert 'let endedOnPurpose = false;' in page
    assert 'if(!endedOnPurpose){' in page
    # showSummary is what marks the end expected — source ORDER says nothing
    # here, since both are hoisted, so check it is set inside that function
    body = page.split('function showSummary(')[1].split('\n}')[0]
    assert 'endedOnPurpose = true;' in body
    # and starting another session clears it again
    again = page.split('async function practiseAgain(')[1].split('\n}')[0]
    assert 'endedOnPurpose = false;' in again


def test_the_setup_overlay_can_scroll_to_its_own_top():
    """The Progress table is taller than the viewport, and `align-items:center`
    overflows in BOTH directions — measured with it open, #statsBox sat at
    top:-273px while every scrollTop on the page was 0, so the KPI row at the
    top could not be reached at all. `margin:auto` centres the same way and
    leaves the overflow scrollable.
    """
    page = (pathlib.Path(web.__file__).parent / 'static' / 'index.html').read_text()
    rule = page.split('#setup {')[1].split('}')[0]
    assert 'overflow-y:auto' in rule
    assert 'align-items:center' not in rule, 'centred flex overflows past its own top'
    inner = page.split('#setupInner {')[1].split('}')[0]
    assert 'margin:auto' in inner


def test_every_web_string_the_server_sends_is_actually_applied():
    """`web_progress` and `web_browse` were served and never used: the two
    buttons were hardcoded English with no id, so they stayed English in a
    Japanese session — the exact defect the i18n table was added to fix.

    Serving a key nobody applies looks identical to being localized.
    """
    import inspect
    page = (pathlib.Path(web.__file__).parent / 'static' / 'index.html').read_text()
    served = re.findall(r"'(web_[a-z_]+)'", inspect.getsource(web.strings))
    assert len(served) >= 15, served
    # a key reaches the page either as set('id', 'web_x') or as STR.web_x —
    # matching only the quoted form called four applied keys missing
    missing = [k for k in served if f"'{k}'" not in page and f'STR.{k}' not in page]
    assert not missing, f'served but never applied in the page: {missing}'


def _explain_patches(clear=True, said='I see.', coach=CLEAN):
    return [patch('app.web.listen', return_value=(clear, said)),
            patch('app.web.call_coach', return_value=coach)]


def test_an_explain_session_opens_with_no_model_call(client):
    """There is nothing for the listener to react to yet and the topic is
    authored text, so the learner sees the screen immediately instead of
    waiting ~10s for a greeting that could only be small talk."""
    with patch('app.web.listen', side_effect=AssertionError('must not be called')):
        r = client.post('/api/session', json={'language': 'English', 'mode': 'explain'})
        assert r.status_code == 200
        d = r.json()
        assert d['mode'] == 'explain'
        assert d['total_tasks'] >= 3
        sess = web.SESSIONS[d['session']]
        for _ in range(300):
            if sess.state == web.AWAITING_INPUT:
                break
            time.sleep(0.01)
        assert sess.state == web.AWAITING_INPUT
        assert sess.explaining
        events = _drain(sess)
        assert any(e['type'] == 'npc' for e in events)
        assert any(e['type'] == 'tasks' for e in events)


def test_a_vague_answer_does_not_advance_the_checklist(client):
    sid = client.post('/api/session',
                      json={'language': 'English', 'mode': 'explain',
                            'topic': 'commute'}).json()['session']
    sess = web.SESSIONS[sid]
    for _ in range(300):
        if sess.state == web.AWAITING_INPUT:
            break
        time.sleep(0.01)
    _drain(sess)

    patches = _explain_patches(clear=False, said='Which bus, though?')
    for p in patches:
        p.start()
    try:
        client.post(f'/api/turn/{sid}', json={'text': 'I use transport.'})
        for _ in range(300):
            if sess.state == web.AWAITING_INPUT:
                break
            time.sleep(0.01)
        assert sess.task_idx == 0, 'a vague answer advanced the point'
        assert sess.tasks_done == 0
        assert any(e.get('text') == 'Which bus, though?' for e in _drain(sess))
    finally:
        for p in patches:
            p.stop()


def test_a_clear_answer_advances_and_the_drill_still_applies(client):
    sid = client.post('/api/session',
                      json={'language': 'English', 'mode': 'explain',
                            'topic': 'commute'}).json()['session']
    sess = web.SESSIONS[sid]
    for _ in range(300):
        if sess.state == web.AWAITING_INPUT:
            break
        time.sleep(0.01)
    _drain(sess)

    dirty = '💡 Feedback:\n- ❌ "I takes the bus" → ✅ "I take the bus" (subject agreement)'
    patches = _explain_patches(clear=True, said='Got it.', coach=dirty)
    for p in patches:
        p.start()
    try:
        client.post(f'/api/turn/{sid}', json={'text': 'I takes the bus then the subway.'})
        for _ in range(300):
            if sess.state in (web.DRILL, web.AWAITING_INPUT, web.FINISHED):
                break
            time.sleep(0.01)
        assert sess.task_idx == 1, 'a clear answer did not advance the point'
        assert sess.state == web.DRILL, 'explain mode must enforce the same drill'
        # and the drill is still unskippable here
        assert client.post(f'/api/turn/{sid}',
                           json={'text': 'moving on'}).status_code == 409
    finally:
        for p in patches:
            p.stop()


def test_the_topics_endpoint_serves_both_languages(client):
    en = client.get('/api/topics?language=English').json()['topics']
    ja = client.get('/api/topics?language=Japanese').json()['topics']
    assert len(en) == len(ja) >= 10
    for a, b in zip(en, ja):
        assert a['id'] == b['id']
        assert len(a['points']) == len(b['points'])
        assert not re.fullmatch(r'[\x20-\x7E]+', b['title']), b['title']


def test_the_header_label_is_short_in_explain_mode():
    """The speaker label is uppercase and letter-spaced, designed for BANKER
    and CLERK. The listener DESCRIPTION is written for the prompt — "someone
    who wants to cook it tonight and has never made it" took two lines above
    every single turn."""
    from app.explain import load_topics
    for topic in load_topics():
        for lang in ('English', 'Japanese'):
            short = topic.listener_short(lang)
            assert short, (topic.id, lang)
            assert len(short) <= 28, (topic.id, lang, short)
            # and the descriptive form is still what the prompt gets
            assert len(topic.listener(lang)) >= len(short)


def test_a_word_taught_twice_is_marked_a_repeat(client):
    """A playtest watched the NPC teach 「お取り寄せ」 twice in one session and
    counted it twice — in the live panel and again in the end-of-session chips.
    The database had it right all along (log_vocab increments times_taught),
    but the turn event said nothing, so the front end appended both times.

    The transcript card still appears on the repeat: the NPC really did teach
    it again, and hiding that would misrepresent the conversation. It is the
    collected list and the word count that must not double.
    """
    sid, sess, patches = _start(client, coach=CORRECTION)
    try:
        _drain(sess)                       # the greeting teaches a word too
        turn = ('Here you are.\n<vocab>word: お取り寄せ '
                'explanation: a special order encourage: Try it!</vocab>')
        web._deliver_actor_turn(sess, turn)
        web._deliver_actor_turn(sess, turn)
        vocab = [e for e in _drain(sess) if e['type'] == 'vocab']
        assert len(vocab) == 2, vocab
        assert vocab[0]['repeat'] is False
        assert vocab[1]['repeat'] is True
    finally:
        for p in patches:
            p.stop()


def test_the_front_end_does_not_collect_a_repeated_word_twice():
    page = (pathlib.Path(web.__file__).parent / 'static' / 'index.html').read_text()
    assert 'if(ev.repeat) return;' in page


def test_a_reloaded_page_can_pick_the_session_back_up(client):
    """OPEN-46 claim 6, reproduced: the session id lived only in a JavaScript
    variable, so a reload dropped the learner on the home screen with no
    warning, no resume prompt and nothing in Progress — while the server went
    on holding the session in SESSIONS. A playtest lost an explain session at
    1/5 this way."""
    sid, sess, patches = _start(client, coach=CORRECTION)
    try:
        client.post(f'/api/turn/{sid}', json={'text': 'A table for two, please.'})
        for _ in range(300):
            if sess.state in (web.AWAITING_INPUT, web.DRILL):
                break
            time.sleep(0.01)

        d = client.get(f'/api/session/{sid}').json()
        assert d['session'] == sid
        assert d['state'] == sess.state
        assert d['language'] == 'English' and d['mode'] == 'scenario'
        assert d['scenario'] and d['speaker'] and d['total_tasks'] == 3
        assert len(d['tasks']) == 3
        # the transcript is what rebuilds the conversation on screen
        assert [m['content'] for m in d['messages']] == \
               [m['content'] for m in sess.messages]
        # the greeting taught a word, and it must come back with the rest
        assert 'sommelier' in [w.lower() for w in d['words']]
    finally:
        for p in patches:
            p.stop()


def test_resume_is_404_for_a_session_the_server_no_longer_has(client):
    """What a reload after a server restart hits. The front end clears its
    stored id on this and shows the home screen, which is the old behaviour —
    the fix is that it no longer does so when the session IS still there."""
    assert client.get('/api/session/nosuchsession').status_code == 404


def test_resume_works_in_explain_mode(client):
    sid = client.post('/api/session',
                      json={'language': 'Japanese', 'mode': 'explain',
                            'topic': 'commute'}).json()['session']
    sess = web.SESSIONS[sid]
    for _ in range(300):
        if sess.state == web.AWAITING_INPUT:
            break
        time.sleep(0.01)
    d = client.get(f'/api/session/{sid}').json()
    assert d['mode'] == 'explain' and d['language'] == 'Japanese'
    assert d['total_tasks'] == len(sess.points) == len(d['tasks'])
    assert d['words'] == []            # explain mode teaches no vocabulary


def test_the_front_end_stores_and_restores_the_session_id():
    page = (pathlib.Path(web.__file__).parent / 'static' / 'index.html').read_text()
    assert "sessionStorage.setItem(RESUME_KEY" in page
    assert "fetch('/api/session/'+sid)" in page
    # and lets go of it when the learner ends the session on purpose
    assert "remember(null);" in page


def test_the_vocabulary_panel_is_hidden_when_nothing_fills_it():
    page = (pathlib.Path(web.__file__).parent / 'static' / 'index.html').read_text()
    assert "$('vocabBox').hidden = (MODE === 'explain');" in page


def test_a_skipped_task_does_not_render_as_done(client):
    """A playtest skipped one task of ten, watched the sidebar read TASKS 10/10
    with every item wearing the same green ✓, and then got 9/10 · 1 missed in
    the end-of-session summary. task_idx advances on a skip exactly as it does
    on a pass, so the payload had no way to tell them apart."""
    sid, sess, patches = _start(client, coach=CORRECTION)
    try:
        assert client.post(f'/api/skip/{sid}').status_code == 200
        payload = web._task_payload(sess)
        assert payload[0]['skipped'] is True
        assert payload[0]['done'] is False
        assert sum(t['done'] for t in payload) == sess.tasks_done
        assert sum(t['skipped'] for t in payload) == sess.tasks_skipped
    finally:
        for p in patches:
            p.stop()


def test_explain_mode_marks_a_skipped_point_skipped_too(client):
    sid = client.post('/api/session',
                      json={'language': 'English', 'mode': 'explain',
                            'topic': 'commute'}).json()['session']
    sess = web.SESSIONS[sid]
    for _ in range(300):
        if sess.state == web.AWAITING_INPUT:
            break
        time.sleep(0.01)
    assert client.post(f'/api/skip/{sid}').status_code == 200
    payload = web._task_payload(sess)
    assert payload[0]['skipped'] is True and payload[0]['done'] is False


def test_skip_works_in_explain_mode(client):
    """It raised AttributeError on `sess.scenario.name` for every explain
    session — a 500 from a button that is visible on screen — because explain
    mode has no Scenario and its checklist is a list of strings, not Tasks."""
    sid = client.post('/api/session',
                      json={'language': 'English', 'mode': 'explain',
                            'topic': 'commute'}).json()['session']
    sess = web.SESSIONS[sid]
    for _ in range(300):
        if sess.state == web.AWAITING_INPUT:
            break
        time.sleep(0.01)

    r = client.post(f'/api/skip/{sid}')
    assert r.status_code == 200, r.text
    assert sess.task_idx == 1
    assert sess.tasks_skipped == 1
    # and it is still refused mid-drill, like the roleplay
    sess.state = web.DRILL
    assert client.post(f'/api/skip/{sid}').status_code == 409
    sess.state = web.AWAITING_INPUT

    # skipping every remaining point finishes the session rather than stranding
    for _ in range(len(sess.points)):
        if sess.current_task is None:
            break
        client.post(f'/api/skip/{sid}')
    assert sess.current_task is None
    assert sess.state == web.FINISHED
    assert any(e['type'] == 'finished' for e in _drain(sess))


def test_every_endpoint_survives_an_explain_session(client):
    """The structural risk of a second mode: explain mode has no Scenario and
    no Task objects, and `sess.scenario.name` is an AttributeError away in any
    handler written for the roleplay. /api/skip was exactly that — a 500 from a
    button visible on screen, found by playing rather than by reading.

    So this walks every endpoint a learner can reach, in explain mode, and
    fails on any 500. A new handler that assumes a Scenario trips it.
    """
    sid = client.post('/api/session',
                      json={'language': 'Japanese', 'mode': 'explain'}).json()['session']
    sess = web.SESSIONS[sid]
    for _ in range(300):
        if sess.state == web.AWAITING_INPUT:
            break
        time.sleep(0.01)

    dirty = '💡 Feedback:\n- ❌ "私は行く" → ✅ "私は行きます" (丁寧形)'
    patches = [patch('app.web.listen', return_value=(True, 'なるほど。')),
               patch('app.web.call_coach', return_value=dirty)]
    for p in patches:
        p.start()
    try:
        assert client.get('/').status_code == 200
        assert client.get('/api/topics?language=Japanese').status_code == 200
        assert client.get('/api/scenarios?language=Japanese').status_code == 200
        assert client.get('/api/stats?language=Japanese').status_code == 200
        assert client.get('/api/strings?language=Japanese').status_code == 200

        r = client.post(f'/api/turn/{sid}', json={'text': '毎朝、電車を使っています。'})
        assert r.status_code == 200, r.text
        for _ in range(400):
            if sess.state in (web.DRILL, web.AWAITING_INPUT, web.FINISHED):
                break
            time.sleep(0.01)
        assert sess.state == web.DRILL

        # the drill, then a skip, then the end — all the ways out
        assert client.post(f'/api/drill/{sid}',
                           json={'text': sess.drill_targets[0]}).status_code == 200
        for _ in range(300):
            if sess.state != web.DRILL:
                break
            time.sleep(0.01)
        assert client.post(f'/api/skip/{sid}').status_code in (200, 409)
        assert client.post(f'/api/session/{sid}/end').status_code == 200
    finally:
        for p in patches:
            p.stop()


def _finish_explain_session(client, topic='commute'):
    """Play an explain session to completion via /api/skip and return its sid."""
    sid = client.post('/api/session',
                      json={'language': 'English', 'mode': 'explain',
                            'topic': topic}).json()['session']
    sess = web.SESSIONS[sid]
    for _ in range(300):
        if sess.state == web.AWAITING_INPUT:
            break
        time.sleep(0.01)
    for _ in range(len(sess.points) + 1):
        if sess.current_task is None:
            break
        client.post(f'/api/skip/{sid}')
    return sid


def test_an_explain_session_does_not_pollute_the_scenario_table(client):
    """`_create_explain_session` used to call db.create_session with the topic
    title where a scenario name belongs, so an explain topic like 'how you get
    from home to work' landed in the same scenario_name column — and the same
    stats dict — as one of the 80 roleplay scenarios. A learner reading the
    Progress table could not tell 'Coffee Shop' (1 of 80 scenarios) from an
    explain topic (1 of 10), and the mastery ladder meant something different
    for each.
    """
    chooser_before = client.get('/api/scenarios?language=English').json()['scenarios']

    _finish_explain_session(client, topic='commute')

    stats = client.get('/api/stats?language=English').json()
    assert 'how you get from home to work' not in stats['scenarios']
    assert 'how you get from home to work' in stats['topics']
    assert stats['topics']['how you get from home to work']['topic_name'] == \
        'how you get from home to work'

    # and the scenario chooser (/api/scenarios) never mistakes a topic for one
    # of the 80 catalogue scenarios either
    chooser_after = client.get('/api/scenarios?language=English').json()['scenarios']
    assert 'how you get from home to work' not in {s['name'] for s in chooser_after}
    assert len(chooser_after) == len(chooser_before)


def test_stats_topics_have_their_own_mastery_ladder(client):
    """get_all_topic_stats mirrors get_all_scenario_stats in shape (plays,
    best_pct, mastery, last_played) but is scoped to kind='explain', so a
    played explain topic is ranked on its own plays/completion rather than
    folded into the scenario ladder.
    """
    _finish_explain_session(client, topic='commute')
    stats = client.get('/api/stats?language=English').json()
    entry = stats['topics']['how you get from home to work']
    assert entry['plays'] == 1
    assert entry['mastery'] in ('newbie', 'apprentice', 'experienced', 'mastered')
    assert stats['scenarios'] == {}


def test_db_create_session_kind_defaults_to_scenario(tmp_path):
    """The CLI (and every pre-existing caller) invokes db.create_session
    without a `kind` argument, so it must keep classifying those sessions as
    'scenario' — the default before explain mode's kind column existed at
    all.
    """
    conn = db.init_db(str(tmp_path / 'kind.db'))
    uid = db.get_or_create_user(conn, target_lang='English')
    sid = db.create_session(conn, uid, 'Cafe', 'English', 'polite', None, 10)
    row = conn.execute('SELECT kind FROM sessions WHERE id = ?', (sid,)).fetchone()
    assert row['kind'] == 'scenario'


def test_legacy_database_without_a_kind_column_still_works(tmp_path):
    """A database created before explain mode existed has no `kind` column at
    all. init_db must add it (backfilled to 'scenario', since every session
    that old was a roleplay scenario) rather than erroring on the missing
    column the first time a stats query runs.
    """
    import sqlite3
    path = str(tmp_path / 'legacy.db')
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT, display_name TEXT NOT NULL DEFAULT 'learner',
            target_lang TEXT NOT NULL, created_at TEXT NOT NULL, last_active TEXT NOT NULL
        );
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            scenario_name TEXT NOT NULL, language TEXT NOT NULL, mood TEXT NOT NULL,
            complication TEXT, tasks_total INTEGER NOT NULL, tasks_done INTEGER NOT NULL DEFAULT 0,
            tasks_skipped INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL, finished_at TEXT
        );
    """)
    now = '2020-01-01T00:00:00Z'
    conn.execute("INSERT INTO user_profiles (display_name, target_lang, created_at, last_active) "
                "VALUES ('learner','English',?,?)", (now, now))
    conn.execute("INSERT INTO sessions (user_id, scenario_name, language, mood, complication, "
                "tasks_total, tasks_done, tasks_skipped, started_at, finished_at) "
                "VALUES (1,'Old Scenario','English','polite',NULL,10,8,2,?,?)", (now, now))
    conn.commit()
    conn.close()

    migrated = db.init_db(path)
    row = migrated.execute('SELECT kind FROM sessions').fetchone()
    assert row['kind'] == 'scenario'
    stats = db.get_all_scenario_stats(migrated, 1)
    assert stats['Old Scenario']['plays'] == 1
    assert stats['Old Scenario']['best_pct'] == 80


def test_the_kind_backfill_is_not_gated_on_the_schema_step(tmp_path):
    """A database migrated once, by a build that predated this backfill, kept
    its explain sessions filed as scenarios forever — the backfill sat inside
    the `column is missing` branch and never ran again.

    Found against the author's real database: 4 explain sessions, 1 correctly
    classified, 3 stranded.
    """
    from app.explain import load_topics

    path = str(tmp_path / 'already-migrated.db')
    conn = db.init_db(path)              # creates the column
    uid = db.get_or_create_user(conn, target_lang='English')
    title = load_topics()[0].title('English')
    # a row written by explain mode BEFORE the kind column existed: the topic
    # title landed in scenario_name and the default filed it as a scenario
    sid = db.create_session(conn, uid, title, 'English', '', None, 5)
    db.finish_session(conn, sid, 3, 0)
    assert conn.execute('SELECT kind FROM sessions WHERE id=?', (sid,)).fetchone()[0] == 'scenario'
    conn.close()

    conn = db.init_db(path)              # second startup: the column exists
    assert conn.execute('SELECT kind FROM sessions WHERE id=?', (sid,)).fetchone()[0] == 'explain'
    assert title not in db.get_all_scenario_stats(conn, uid)
    assert title in db.get_all_topic_stats(conn, uid)


def test_the_backfill_never_reclassifies_a_real_scenario():
    """It matches on name, so the guard is that the two namespaces cannot
    overlap — and anything the catalogue claims is excluded outright."""
    from app.explain import load_topics
    from app.scenarios.builtins import load_scenarios
    scenario_names = {sc.name for sc in load_scenarios()}
    titles = {t.title(lang) for t in load_topics() for lang in ('English', 'Japanese')}
    assert not (titles & scenario_names), titles & scenario_names
