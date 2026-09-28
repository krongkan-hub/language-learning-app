"""The HTTP API: create a session, stream its events, submit turns and drills,
skip, end, and the read-only stats/strings/scenario lists.
"""
from __future__ import annotations

import json
import os
import re
import queue
import threading
import unicodedata
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from .. import db
from ..coach import _normalize_phrase
from ..explain import load_topics
from ..i18n import normalize_language, scenario_name, scenario_place, t
from ..llm import sanitize_learner_input, NPC_MOODS
from .state import (AWAITING_INPUT, BUSY, DRILL, FINISHED, NewSession, SESSIONS, Session, Utterance, _database, _scenarios_for)
from .payloads import (_header, _resume_next, _task_payload, _whats_next)
from .turns import (_explain_opening_worker, _explain_turn_worker, _finish, _greeting_worker, _turn_worker)


STATIC = Path(__file__).parent.parent / 'static'


app = FastAPI(title='Language Coach')

# DNS rebinding: a page on any domain re-pointed at 127.0.0.1 counts as the
# same origin, and could read /api/stats (the learner's own sentences) or
# drive the model. The Host header is the name that page used, so only the
# local names are served. `testserver` is the test client's.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[
    h.strip() for h in os.environ.get(
        'LANGUAGE_COACH_ALLOWED_HOSTS', '127.0.0.1,localhost,[::1],testserver').split(',')])


# The front end is the React app in frontend/, built by `make web` into
# app/static/ui (Vite, base /ui/): the practice screen at /, the learner
# dashboard at /dashboard, and the hashed assets under /ui/.
UI_DIR = STATIC / 'ui'


def _app_page():
    index = UI_DIR / 'index.html'
    if not index.is_file():
        raise HTTPException(503, 'The front end is not built yet: run `make web` (or `npm run build` in frontend/).')
    # no-cache means "revalidate", not "don't cache": the ETag still answers
    # most reloads with a 304. Without it the page can come back from
    # Chrome's cache after a rebuild, still pointing at the old assets —
    # which once cost a round of measuring a fix that was on disk and simply
    # not being served. The assets themselves are content-hashed.
    return FileResponse(index, headers={'Cache-Control': 'no-cache'})


@app.get('/')
def index():
    return _app_page()


@app.get('/dashboard')
def dashboard_page():
    return _app_page()


@app.get('/ui/{path:path}')
def ui(path: str = ''):
    """A built asset under app/static/ui, or the app itself for any other path."""
    target = (UI_DIR / path).resolve()
    if path and target.is_file() and UI_DIR.resolve() in target.parents:
        return FileResponse(target)
    return _app_page()


@app.get('/api/scenarios')
def list_scenarios(language: str = 'English'):
    """Scenario chooser, with the mastery badge the CLI shows."""
    language = normalize_language(language) or 'English'
    conn = db.init_db()
    user_id = db.get_or_create_user(conn, target_lang=language)
    stats = db.get_all_scenario_stats(conn, user_id)
    out = []
    for sc in _scenarios_for(language):
        s = stats.get(sc.name, {})
        out.append({
            'name': sc.name,
            'display_name': scenario_name(sc, language),
            'place': scenario_place(sc, language),
            'role': sc.role,
            'plays': s.get('plays', 0),
            'best_pct': s.get('best_pct', 0),
            'mastery': s.get('mastery', 'newbie'),
            'mastery_label': t(s.get('mastery', 'newbie'), language),
        })
    conn.close()
    return {'language': language, 'scenarios': out}


@app.get('/api/stats')
def stats(language: str = 'English'):
    """The --stats report. Resolved by language, as OPEN-29 required."""
    language = normalize_language(language) or 'English'
    conn = db.init_db()
    user_id = db.get_or_create_user(conn, target_lang=language)
    payload = {
        'language': language,
        'overall': dict(db.get_overall_stats(conn, user_id)),
        'vocab': dict(db.get_vocab_stats(conn, user_id)),
        # Roleplay scenarios and explain topics both park their display name
        # in the same DB column, so they are split into two payload keys here
        # rather than one dict a learner (or the UI) cannot tell apart.
        'scenarios': db.get_all_scenario_stats(conn, user_id),
        'topics': db.get_all_topic_stats(conn, user_id),
        'mistakes': db.repeated_mistakes(conn, user_id, language),
    }
    conn.close()
    return payload


# The React front end (frontend/, built by `make web` into app/static/ui).


@app.get('/api/dashboard')
def dashboard(language: str = 'English'):
    """The learner-analytics dashboard's data (app/db/analytics.py)."""
    from ..db import analytics
    language = normalize_language(language) or 'English'
    with _database() as conn:
        user_id = db.get_or_create_user(conn, target_lang=language)
        return {'language': language, **analytics.dashboard(conn, user_id, language)}


@app.get('/api/strings')
def strings(language: str = 'English'):
    """UI labels in the language being studied, from app/i18n.py.

    That docstring used to say the web "adds no parallel translation table".
    It did have one: thirteen English labels hardcoded in index.html, so a
    Japanese session showed Japanese scenario, tasks and dialogue inside an
    English chrome. The `web_` keys below are those labels, now in the same
    table as everything else.
    """
    language = normalize_language(language) or 'English'
    keys = ('cli_title', 'objective_line', 'task_completed', 'task_header',
            'drill_intro', 'drill_prompt', 'drill_correct', 'drill_retry',
            'spinner_analyzing', 'spinner_thinking', 'summary_tasks_failed',
            'skipped_task', 'judge_note', 'strategy_hint', 'moving_on_failed',
            'task_not_completed', 'newbie', 'apprentice', 'experienced',
            'mastered',
            'web_skip_task', 'web_end', 'web_send', 'web_tasks', 'web_coach',
            'web_vocabulary', 'web_coach_empty', 'web_vocab_empty',
            'web_progress', 'web_browse', 'web_close', 'web_search',
            'web_again', 'web_review', 'web_input_placeholder',
            'web_stat_scenarios', 'web_stat_topics', 'web_col_plays',
            'web_col_best', 'web_col_mastery', 'web_no_stats',
            'stats_mistakes_header', 'web_repeat_badge',
            'web_vocab_used', 'web_vocab_learned', 'web_dashboard')
    return {'language': language,
            'strings': {k: t(k, language) for k in keys}}


@app.get('/api/session/{sid}')
def resume_session(sid: str):
    """Everything a reloaded page needs to pick a session back up.

    The session id lived only in a JavaScript variable, so a reload threw the
    session away — no warning, no resume, and nothing in Progress, while the
    server went on holding it in SESSIONS. A playtest lost an explain session
    at 1/5 this way.
    """
    sess = SESSIONS.get(sid)
    if sess is None:
        raise HTTPException(404, 'no such session')
    with sess.lock:
        # Anything still queued was produced for the stream that just died and
        # is already reflected in the snapshot below — the transcript, the
        # task list, the state. Replaying it would double the NPC's last turn
        # on screen. (One viewer per session: the queue is not a broadcast.)
        while True:
            try:
                sess.events.get_nowait()
            except queue.Empty:
                break
        return dict(_header(sess), session=sid, retried=0, retried_note='',
                    state=sess.state, tasks=_task_payload(sess),
                    messages=sess.messages,
                    words=list(sess.taught_words.values()),
                    # A drill is a modal the learner cannot get out of any
                    # other way, and its targets live only in the event that
                    # opened it — which the drain above just discarded.
                    drill=list(sess.drill_targets),
                    # A session that ran to its last task is still in SESSIONS
                    # — only /end pops it — so a reload can land on one. The
                    # page shows the summary rather than a transcript it
                    # cannot type into.
                    tasks_done=sess.tasks_done,
                    tasks_missed=sess.tasks_skipped,
                    **_resume_next(sess))


def _random_scenario(conn, user_id, catalogue):
    """Pick a scenario, favouring the ones played least.

    Uniform random would keep re-serving scenarios the learner has already done
    nine times while leaving others untouched, so the draw is restricted to the
    least-played band and randomised inside it. That keeps it genuinely
    unpredictable while still widening coverage.
    """
    import random
    stats = db.get_all_scenario_stats(conn, user_id)
    plays = {sc.name: stats.get(sc.name, {}).get('plays', 0) for sc in catalogue}
    fewest = min(plays.values())
    pool = [sc for sc in catalogue if plays[sc.name] <= fewest]
    return random.choice(pool or catalogue)


def _create_explain_session(conn, user_id: int, language: str, body: NewSession):
    import random
    topics = load_topics()
    if body.topic is None:
        topic = random.choice(topics)
    else:
        topic = next((x for x in topics if x.id == body.topic), None)
        if topic is None:
            raise HTTPException(404, 'no such topic')
    db.abandon_stale_sessions(conn, user_id)
    points = topic.points(language)
    sid = uuid.uuid4().hex
    sess = Session(id=sid, language=language, scenario=None, tasks=[],
                   topic=topic, points=points, mood='', complication=None,
                   user_id=user_id,
                   db_session_id=db.create_session(conn, user_id,
                                                   topic.title(language),
                                                   language, '', None, len(points),
                                                   kind='explain'))
    _admit(sid, sess)
    threading.Thread(target=_explain_opening_worker, args=(sess,), daemon=True).start()
    return dict(_header(sess), session=sid, retried=0, retried_note='')


@app.get('/api/topics')
def list_topics(language: str = 'English'):
    language = normalize_language(language) or 'English'
    return {'language': language,
            'topics': [{'id': x.id, 'title': x.title(language),
                        'listener': x.listener(language),
                        'points': x.points(language)} for x in load_topics()]}


@app.post('/api/session')
def create_session(body: NewSession):
    language = normalize_language(body.language)
    if language is None:
        raise HTTPException(400, 'unsupported language')
    if len(SESSIONS) >= MAX_LIVE_SESSIONS:
        raise HTTPException(429, 'Too many sessions are open. End one, or wait a minute and try again.')
    # Closed on every path: this connection used to be left to the garbage
    # collector on success (only the 404 branches closed it).
    with _database() as conn:
        return _create_session(conn, language, body)


def _create_session(conn, language: str, body: NewSession):
    user_id = db.get_or_create_user(conn, target_lang=language)
    if body.mode == 'explain':
        return _create_explain_session(conn, user_id, language, body)

    catalogue = _scenarios_for(language)
    if body.scenario is None:
        scenario = _random_scenario(conn, user_id, catalogue)
    else:
        scenario = next((s for s in catalogue if s.name == body.scenario), None)
        if scenario is None:
            raise HTTPException(404, 'no such scenario')
    db.abandon_stale_sessions(conn, user_id)
    seen = db.get_seen_task_goals(conn, user_id, scenario.name)
    retry = db.get_unfinished_task_goals(conn, user_id, scenario.name)
    tasks = scenario.get_session_tasks(num_tasks=body.tasks,
                                       seen_goals=seen, retry_goals=retry)
    # The web already carries unfinished goals into the next session of a
    # scenario, exactly as the CLI does — but silently. The CLI says so
    # (`retried_tasks_included`), and a learner who is handed the task they
    # gave up on last time should be told that is what happened rather than
    # left to wonder why it looks familiar (OPEN-37).
    retried = sum(1 for task in tasks if task.goal in retry)
    import random
    mood = random.choice(NPC_MOODS)
    complication = (random.choice(scenario.complications)
                    if scenario.complications else None)
    sid = uuid.uuid4().hex
    sess = Session(id=sid, language=language, scenario=scenario, tasks=tasks,
                   mood=mood, complication=complication, user_id=user_id,
                   db_session_id=db.create_session(conn, user_id, scenario.name,
                                                   language, mood, complication,
                                                   len(tasks)))
    _admit(sid, sess)
    threading.Thread(target=_greeting_worker, args=(sess,), daemon=True).start()
    return dict(_header(sess), session=sid, retried=retried,
                retried_note=(t('retried_tasks_included', language, n=retried)
                              if retried else ''))


# How long a session survives with nobody watching it. A reload takes a
# moment — drop the stream, fetch /api/session/{sid}, open a new stream — and
# closing the session on the first of those three is what made a reload lose
# it. Long enough for a slow reload, short enough that a closed tab does not
# leave a session open for meaningfully longer than it used to.
ORPHAN_GRACE_SECONDS = float(os.environ.get('LANGUAGE_COACH_ORPHAN_GRACE', '90'))

# One learner, one machine: a handful of live sessions is plenty, and each
# holds a thread and queued model work.
MAX_LIVE_SESSIONS = 8


def _arm_orphan_close(sess: Session):
    """Close the session after the grace period unless a stream attaches."""
    sess.closer = threading.Timer(ORPHAN_GRACE_SECONDS, _close_orphan, args=(sess,))
    sess.closer.daemon = True
    sess.closer.start()


def _admit(sid: str, sess: Session):
    """Register a new session. The orphan timer starts now, not only when a
    stream ends: a session whose stream never opened was never cleaned up."""
    SESSIONS[sid] = sess
    with sess.lock:
        _arm_orphan_close(sess)


def _close_orphan(sess: Session):
    """Close a session nobody came back to.

    Closing the tab used to leave the session unfinished forever: 13 such rows
    had accumulated in the real database, every one of them a session someone
    walked away from. This is still that cleanup — it just waits out a reload
    first.
    """
    with sess.lock:
        if sess.viewers:
            return                     # somebody reattached; nothing to do
        sess.closer = None
        if sess.state != FINISHED:
            try:
                with _database() as conn:
                    db.finish_session(conn, sess.db_session_id,
                                      sess.tasks_done, sess.tasks_skipped)
            except Exception:
                pass
            sess.state = FINISHED
    SESSIONS.pop(sess.id, None)


@app.get('/api/stream/{sid}')
def stream(sid: str):
    sess = SESSIONS.get(sid)
    if sess is None:
        raise HTTPException(404, 'no such session')

    def gen():
        with sess.lock:
            sess.viewers += 1
            if sess.closer is not None:
                sess.closer.cancel()   # a reload, not a departure
                sess.closer = None
        try:
            while True:
                try:
                    # The heartbeat matters: a turn costs ~9-11s and proxies and
                    # browsers drop an idle event stream well before that.
                    event = sess.events.get(timeout=10)
                except queue.Empty:
                    yield ': keep-alive\n\n'
                    continue
                yield f'data: {json.dumps(event, ensure_ascii=False)}\n\n'
                if event.get('type') == 'closed':
                    return
        finally:
            # The stream ending is the best signal available that nobody is
            # watching — but a reload ends it too, and the page now keeps its
            # session id and comes back. So the close is deferred rather than
            # immediate, and a stream that attaches inside the grace window
            # cancels it.
            with sess.lock:
                sess.viewers -= 1
                orphaned = sess.viewers <= 0 and sess.closer is None
                if orphaned:
                    _arm_orphan_close(sess)

    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache',
                                      'X-Accel-Buffering': 'no'})


@app.post('/api/turn/{sid}')
def submit_turn(sid: str, body: Utterance):
    sess = SESSIONS.get(sid)
    if sess is None:
        raise HTTPException(404, 'no such session')
    with sess.lock:
        # The drill is a no-skip loop in the CLI, and it is enforced HERE
        # rather than by disabling an input box: a learner who opens the
        # console could otherwise post a turn straight past it, which is not
        # what `while True` means.
        if sess.state == DRILL:
            raise HTTPException(409, 'finish the correction drill first')
        if sess.state != AWAITING_INPUT:
            raise HTTPException(409, f'session is {sess.state}')
        # Injection tokens (<|im_start|>, [System: ...], <system>) are stripped
        # before the text reaches any prompt. Only the retired CLI ever did
        # this; the web passed learner text through raw until it became the
        # only front end. A message that was nothing BUT such tokens is empty.
        text = sanitize_learner_input(body.text)
        if not text:
            raise HTTPException(400, 'empty message')
        sess.messages.append({'role': 'user', 'content': text})
        sess.set_state(BUSY)
    worker = _explain_turn_worker if sess.explaining else _turn_worker
    threading.Thread(target=worker, args=(sess, text), daemon=True).start()
    return {'state': sess.state}


def _drill_form(text: str) -> str:
    """What a retyped correction is compared on: the words, not the typing.

    A playtest answer "hi do you use organic or biodynamic farming at your
    vineyard" was refused for "Hi! Do you use…" — a phone keyboard does not
    capitalise after a pasted-in quote, and a "!" mid-sentence is not the
    correction being practised. Apostrophes and hyphens stay: "dont" for
    "don't" IS a spelling the drill should catch.
    """
    # NFKC first: a Japanese IME types ３ and ＯＫ where the target has 3 and
    # OK, and ＇ for '. Hyphen-like dashes are folded into '-'.
    text = unicodedata.normalize('NFKC', text)
    text = re.sub('[\u2010-\u2015\u2212]', '-', text)
    text = _normalize_phrase(text).lower()
    text = re.sub(r"[^\w\s'\-]", ' ', text)      # \w keeps kana and kanji
    if re.search('[\u3040-\u30ff\u4e00-\u9fff]', text):
        return re.sub(r'\s+', '', text)          # Japanese is written without spaces
    return re.sub(r'\s+', ' ', text).strip()


@app.post('/api/drill/{sid}')
def submit_drill(sid: str, body: Utterance):
    """One correction at a time, and no way past a wrong one — the same
    contract as run_correction_drill."""
    sess = SESSIONS.get(sid)
    if sess is None:
        raise HTTPException(404, 'no such session')
    with sess.lock:
        if sess.state != DRILL:
            raise HTTPException(409, 'no drill in progress')
        if _drill_form(body.text) != _drill_form(sess.drill_targets[0]):
            return {'correct': False, 'target': sess.drill_targets[0],
                    'remaining': len(sess.drill_targets)}
        sess.drill_targets.pop(0)
        if sess.drill_targets:
            sess.emit('drill', target=sess.drill_targets[0],
                      remaining=len(sess.drill_targets))
            return {'correct': True, 'target': sess.drill_targets[0],
                    'remaining': len(sess.drill_targets)}
        sess.emit('drill_done')
        if sess.current_task is None:
            # The last correction of the last task. Setting FINISHED alone
            # left the page with a closed input and no summary: only the
            # 'finished' event (from _finish) brings the summary up.
            _finish(sess)
        else:
            sess.set_state(AWAITING_INPUT)
        return {'correct': True, 'remaining': 0}


@app.post('/api/skip/{sid}')
def skip_task(sid: str):
    """Give up on the current task and move on.

    The CLI has had `skip` since the beginning; the web front end had no way
    out of a task at all, so a learner stuck on one could only reload and lose
    the session. Refused during a drill for the same reason a turn is: the
    drill is the one place the learner is meant to be held.
    """
    sess = SESSIONS.get(sid)
    if sess is None:
        raise HTTPException(404, 'no such session')
    with sess.lock:
        if sess.state == DRILL:
            raise HTTPException(409, 'finish the correction drill first')
        if sess.state != AWAITING_INPUT:
            raise HTTPException(409, f'session is {sess.state}')
        task = sess.current_task
        if task is None:
            raise HTTPException(409, 'nothing left to skip')
        # Explain mode has no Task objects and no Scenario — the checklist is
        # a list of strings — so there is nothing to log a row about. Skipping
        # the log rather than the SKIP: a learner stuck on a point they cannot
        # put into words needs the way out more than the statistics need the
        # row, and this endpoint raised AttributeError on `sess.scenario.name`
        # for every explain session until it was played.
        if not sess.explaining:
            now = db._utcnow()
            with _database() as conn:
                db.log_task(conn, sess.db_session_id, sess.scenario.name,
                            sess.user_id, sess.task_idx, task.goal,
                            task.done_when, task.difficulty, task.phase,
                            'skipped', sess.attempts, now, now)
        sess.tasks_skipped += 1
        sess.missed_idx.add(sess.task_idx)
        sess.task_idx += 1
        sess.attempts = 0
        sess.task_start_idx = len(sess.messages)
        sess.emit('tasks', tasks=_task_payload(sess))
        if sess.current_task is None:
            _finish(sess)
        else:
            sess.set_state(AWAITING_INPUT)
    return {'task_index': sess.task_idx, 'skipped': sess.tasks_skipped}


@app.post('/api/session/{sid}/end')
def end_session(sid: str):
    sess = SESSIONS.pop(sid, None)
    if sess is None:
        raise HTTPException(404, 'no such session')
    with sess.lock:
        # Marked finished here, or the orphan timer the dropped stream starts
        # finishes it a second time ~90s later and moves finished_at.
        sess.state = FINISHED
    with _database() as conn:
        db.finish_session(conn, sess.db_session_id,
                          sess.tasks_done, sess.tasks_skipped)
        # The end of a session is the one moment the learner is looking at a
        # screen with nothing else to do, so it carries what is TRUE and
        # earned rather than a number we invented: how far this scenario is
        # from its next rung, and how many collected words are still waiting
        # to be practised. An explain topic has no ladder, so it gets neither.
        nxt = _whats_next(conn, sess)
    sess.emit('closed')
    return {'tasks_done': sess.tasks_done, 'tasks_skipped': sess.tasks_skipped,
            **nxt}


def serve(host: str = '127.0.0.1', port: int = 8000):
    """Run the server, and say so.

    Importing mlx_lm takes roughly half a minute, and `log_level='warning'`
    swallowed uvicorn's own "Uvicorn running on ..." line — so the first run of
    `make web` printed a urllib3 warning and then sat silent for 30 seconds
    with no way to tell starting from hung. The banner is printed before the
    slow import work finishes, and uvicorn's own line is left visible.
    """
    from ..telemetry import setup as setup_tracing
    setup_tracing()
    import uvicorn
    url = f'http://{host}:{port}'
    print(f'\n  Language Coach — starting…\n  Open {url} once the line below appears.\n'
          f'  Ctrl-C to stop.\n', flush=True)
    uvicorn.run(app, host=host, port=port, log_level='info')
