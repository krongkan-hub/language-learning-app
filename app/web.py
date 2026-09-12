"""Web front end for the language coach.

A second front end beside `app/cli.py`, not a replacement: the core —
`app/session.py`, `llm`, `coach`, `judge`, `db`, `i18n` — is untouched, and
`tests/test_cli_session.py` still covers the CLI.

Why it exists, in the order the reasons actually matter:

1. Coach feedback scrolls away in a terminal. The coach was taken from 69% to
   84% on the Japanese arm, and none of that reaches a learner who does not
   read it. A panel that stays on screen is the point of this UI.
2. A turn costs ~9-11s, and the three LLM calls are serialised by `_llm_lock`.
   The CLI reorder in 7e312f0 already put the NPC first; SSE lets the coach and
   the task verdict arrive afterwards without the learner waiting on them.
3. Japanese renders properly in a browser.

The turn order mirrors the CLI exactly — judge, then actor, then coach — and
for the same reason: the actor's system prompt depends on the judge's verdict,
because a completed task advances the index that picks the next task.
"""
from __future__ import annotations

import json
import queue
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from . import db
from .cli import extract_and_format_vocab, parse_vocab
from .coach import (call_coach, correction_targets, describe_situation,
                    is_clean_verdict, _normalize_phrase)
from .i18n import (mood_label, normalize_language, scenario_name,
                    scenario_place, t)
from .judge import evaluate_task
from .llm import NPC_MOODS, call_actor, stream_actor, translate_hints
from .scenarios.builtins import load_scenarios
from .session import (ACTOR_MAX_SENTENCES, GREETING_MAX_SENTENCES,
                      build_actor_system_prompt, build_greeting_system_prompt,
                      produce_actor_turn, produce_greeting_turn, recent_history)

STATIC = Path(__file__).parent / 'static'

# Server-side states. The learner cannot leave DRILL by any route the browser
# controls — see `submit_turn`.
AWAITING_INPUT = 'awaiting_input'
BUSY = 'busy'
DRILL = 'drill'
FINISHED = 'finished'


@dataclass
class Session:
    id: str
    language: str
    scenario: object
    tasks: list
    mood: str
    complication: Optional[str]
    user_id: int
    db_session_id: int
    hint_translations: dict = field(default_factory=dict)
    messages: list = field(default_factory=list)
    events: queue.Queue = field(default_factory=queue.Queue)
    state: str = BUSY
    task_idx: int = 0
    task_start_idx: int = 1
    attempts: int = 0
    tasks_done: int = 0
    tasks_skipped: int = 0
    drill_targets: list = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def current_task(self):
        return self.tasks[self.task_idx] if self.task_idx < len(self.tasks) else None

    def emit(self, kind: str, **payload):
        self.events.put({'type': kind, **payload})

    def set_state(self, state: str):
        self.state = state
        self.emit('state', state=state, task_index=self.task_idx,
                  tasks_done=self.tasks_done, tasks_skipped=self.tasks_skipped)


@contextmanager
def _database():
    """A connection scoped to the calling thread.

    sqlite3 refuses to use a connection from a thread other than the one that
    created it, and the turn runs on a worker thread while the session is
    created on the request thread — caching one on the Session raised
    "SQLite objects created in a thread can only be used in that same thread"
    on the first real turn. `check_same_thread=False` would silence that while
    leaving two threads sharing one connection, which is a data race rather
    than a fix; opening per unit of work is cheap and correct.
    """
    conn = db.init_db()
    try:
        yield conn
    finally:
        conn.close()


SESSIONS: dict = {}
MAX_TASK_ATTEMPTS = 4

app = FastAPI(title='Language Coach')


class NewSession(BaseModel):
    language: str
    # Omitted means "surprise me", which is the normal way in: choosing from a
    # list of 80 turns every session into a decision, and a learner picking for
    # themselves drifts toward the scenarios they already find easy.
    scenario: Optional[str] = None
    tasks: int = 10


class Utterance(BaseModel):
    text: str


def _scenarios_for(language: str):
    return load_scenarios()


@app.get('/')
def index():
    return FileResponse(STATIC / 'index.html')


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
        'scenarios': db.get_all_scenario_stats(conn, user_id),
    }
    conn.close()
    return payload


@app.get('/api/strings')
def strings(language: str = 'English'):
    """UI labels in the language being studied — the same 71 i18n keys the CLI
    uses, so the web front end adds no parallel translation table."""
    language = normalize_language(language) or 'English'
    keys = ('cli_title', 'objective_line', 'task_completed', 'task_header',
            'drill_intro', 'drill_prompt', 'drill_correct', 'drill_retry',
            'spinner_analyzing', 'spinner_thinking', 'summary_tasks_failed',
            'skipped_task', 'judge_note', 'strategy_hint', 'moving_on_failed',
            'task_not_completed', 'newbie', 'apprentice', 'experienced',
            'mastered')
    return {'language': language,
            'strings': {k: t(k, language) for k in keys}}


# --------------------------------------------------------------------------
# Session lifecycle
# --------------------------------------------------------------------------

def _task_payload(sess: Session):
    return [{
        'index': i,
        'goal': sess.hint_translations.get((i, task.goal), task.goal),
        'done': i < sess.task_idx,
        'current': i == sess.task_idx,
    } for i, task in enumerate(sess.tasks)]


def _greeting_worker(sess: Session):
    """First turn. Runs off the request thread so the browser can open the
    stream and watch it arrive rather than waiting on a ~10s response."""
    try:
        sess.emit('stage', name='preparing')
        sess.hint_translations = translate_hints(sess.tasks, sess.language)
        sess.emit('stage', name='greeting')
        sess.emit('tasks', tasks=_task_payload(sess))
        system_prompt = build_greeting_system_prompt(
            sess.scenario, sess.tasks[0], language=sess.language,
            mood=sess.mood, complication=sess.complication)
        greeting = produce_greeting_turn(
            [{'role': 'user', 'content': 'Hello.'}], system_prompt,
            speaker=sess.scenario.speaker, max_sentences=GREETING_MAX_SENTENCES,
            actor_fn=call_actor, language=sess.language)
        _deliver_actor_turn(sess, greeting)
        sess.set_state(AWAITING_INPUT)
    except Exception as exc:  # surfaced to the learner rather than swallowed
        sess.emit('error', message=str(exc))
        sess.set_state(AWAITING_INPUT)


def _deliver_actor_turn(sess: Session, raw: str):
    """Split one actor turn into what the learner sees, and log the card."""
    spoken, vocab_box = extract_and_format_vocab(raw, sess.language, sess.scenario)
    sess.messages.append({'role': 'assistant', 'content': spoken})
    sess.emit('npc', text=spoken, speaker=sess.scenario.speaker)
    parsed = parse_vocab(raw)
    if vocab_box and parsed:
        sess.emit('vocab', word=parsed[0].strip(), explanation=parsed[1].strip(),
                  encourage=parsed[2].strip())
        with _database() as conn:
            db.log_vocab(conn, sess.user_id, sess.language,
                         parsed[0], parsed[1], sess.scenario.name)


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


@app.post('/api/session')
def create_session(body: NewSession):
    language = normalize_language(body.language)
    if language is None:
        raise HTTPException(400, 'unsupported language')
    catalogue = _scenarios_for(language)
    conn = db.init_db()
    user_id = db.get_or_create_user(conn, target_lang=language)

    if body.scenario is None:
        scenario = _random_scenario(conn, user_id, catalogue)
    else:
        scenario = next((s for s in catalogue if s.name == body.scenario), None)
        if scenario is None:
            conn.close()
            raise HTTPException(404, 'no such scenario')
    db.abandon_stale_sessions(conn, user_id)
    seen = db.get_seen_task_goals(conn, user_id, scenario.name)
    retry = db.get_unfinished_task_goals(conn, user_id, scenario.name)
    tasks = scenario.get_session_tasks(num_tasks=body.tasks,
                                       seen_goals=seen, retry_goals=retry)
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
    SESSIONS[sid] = sess
    threading.Thread(target=_greeting_worker, args=(sess,), daemon=True).start()
    return {'session': sid, 'language': language,
            'scenario': scenario_name(scenario, language),
            'place': scenario_place(scenario, language),
            'speaker': scenario.speaker, 'total_tasks': len(tasks),
            # The actor is given one of six moods and sometimes a complication,
            # and neither ever reached the learner — so every scenario read the
            # same however differently the NPC was actually behaving.
            'mood': mood_label(mood, language), 'complication': complication}


@app.get('/api/stream/{sid}')
def stream(sid: str):
    sess = SESSIONS.get(sid)
    if sess is None:
        raise HTTPException(404, 'no such session')

    def gen():
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

    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache',
                                      'X-Accel-Buffering': 'no'})


# --------------------------------------------------------------------------
# The turn
# --------------------------------------------------------------------------

def _advance_after_judge(sess: Session, is_done: bool, hint: Optional[str]):
    """Mirrors the CLI's task bookkeeping, including counting a FAILED task —
    which was missed for the whole life of the CLI (OPEN-25)."""
    task = sess.current_task
    now = db._utcnow()
    if is_done:
        sess.emit('task_result', done=True, index=sess.task_idx)
        with _database() as conn:
            db.log_task(conn, sess.db_session_id, sess.scenario.name,
                        sess.user_id, sess.task_idx, task.goal, task.done_when,
                        task.difficulty, task.phase, 'completed',
                        sess.attempts + 1, now, now)
        sess.tasks_done += 1
        sess.task_idx += 1
        sess.attempts = 0
        sess.task_start_idx = len(sess.messages)
        return
    sess.attempts += 1
    if sess.attempts >= MAX_TASK_ATTEMPTS:
        with _database() as conn:
            db.log_task(conn, sess.db_session_id, sess.scenario.name,
                        sess.user_id, sess.task_idx, task.goal, task.done_when,
                        task.difficulty, task.phase, 'failed', sess.attempts,
                        now, now)
        sess.tasks_skipped += 1
        sess.task_idx += 1
        sess.attempts = 0
        sess.task_start_idx = len(sess.messages)
        sess.emit('task_result', done=False, moved_on=True, index=sess.task_idx)
    else:
        sess.emit('task_result', done=False, moved_on=False,
                  attempts=sess.attempts, max_attempts=MAX_TASK_ATTEMPTS,
                  hint=hint)


def _finish(sess: Session):
    """End the session with a summary. A session that simply stops leaves the
    learner with no sense of having finished anything."""
    with _database() as conn:
        db.finish_session(conn, sess.db_session_id,
                          sess.tasks_done, sess.tasks_skipped)
        vocab = db.get_vocab_stats(conn, sess.user_id)
    sess.emit('finished',
              tasks_done=sess.tasks_done,
              tasks_total=len(sess.tasks),
              tasks_missed=sess.tasks_skipped,
              words=(dict(vocab).get('learned_words') or 0)
                    + (dict(vocab).get('due_words') or 0))
    sess.set_state(FINISHED)


def _turn_worker(sess: Session, text: str):
    """judge -> actor -> coach, the same order as the CLI.

    The judge must precede the actor because the actor's system prompt depends
    on its verdict; the coach follows the actor so the NPC's reply reaches the
    learner first (7e312f0).
    """
    try:
        task = sess.current_task
        if task is None:
            sess.set_state(FINISHED)
            return

        # Each stage is announced as it starts. The turn takes 9-11s and the
        # server knows exactly which of the three calls it is in, so the wait
        # can be narrated truthfully instead of hidden behind one spinner.
        sess.emit('stage', name='judging')
        vocab_targets = (getattr(task, 'vocab_translations', {}) or {}).get(sess.language)
        is_done, hint = evaluate_task(text, task.done_when,
                                      sess.messages[sess.task_start_idx:],
                                      sess.language, vocab_targets)
        _advance_after_judge(sess, is_done, hint)
        sess.emit('tasks', tasks=_task_payload(sess))

        if sess.current_task is None:
            actor_system = build_actor_system_prompt(
                sess.scenario,
                'The customer has just completed their final interaction. '
                'Wrap up the conversation naturally in 1-2 sentences.',
                language=sess.language, mood=sess.mood,
                complication=sess.complication)
        else:
            actor_system = build_actor_system_prompt(
                sess.scenario, sess.current_task, language=sess.language,
                mood=sess.mood, complication=sess.complication)

        sess.emit('stage', name='replying')
        chunks = []
        raw = produce_actor_turn(
            recent_history(sess.messages), actor_system,
            speaker=sess.scenario.speaker, max_sentences=ACTOR_MAX_SENTENCES,
            actor_fn=stream_actor,
            callback=lambda s: (chunks.append(s), sess.emit('sentence', text=s)),
            language=sess.language)
        _deliver_actor_turn(sess, raw)

        sess.emit('stage', name='coaching')
        situation = describe_situation(sess.scenario.place, sess.scenario.role,
                                       sess.scenario.speaker)
        feedback = call_coach(text, sess.language, situation=situation)
        targets = [] if is_clean_verdict(feedback, sess.language) else correction_targets(feedback)
        sess.emit('coach', text=feedback, clean=not targets, targets=targets)

        if targets:
            sess.drill_targets = list(targets)
            sess.emit('drill', target=targets[0], remaining=len(targets))
            sess.set_state(DRILL)
        elif sess.current_task is None:
            with _database() as conn:
                                  db.finish_session(conn, sess.db_session_id,
                                                    sess.tasks_done, sess.tasks_skipped)
            sess.set_state(FINISHED)
        else:
            sess.set_state(AWAITING_INPUT)
    except Exception as exc:
        sess.emit('error', message=str(exc))
        sess.set_state(AWAITING_INPUT)


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
        text = body.text.strip()
        if not text:
            raise HTTPException(400, 'empty message')
        sess.messages.append({'role': 'user', 'content': text})
        sess.set_state(BUSY)
    threading.Thread(target=_turn_worker, args=(sess, text), daemon=True).start()
    return {'state': sess.state}


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
        wanted = _normalize_phrase(sess.drill_targets[0])
        if _normalize_phrase(body.text) != wanted:
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
            with _database() as conn:
                                  db.finish_session(conn, sess.db_session_id,
                                                    sess.tasks_done, sess.tasks_skipped)
            sess.set_state(FINISHED)
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
        now = db._utcnow()
        with _database() as conn:
            db.log_task(conn, sess.db_session_id, sess.scenario.name,
                        sess.user_id, sess.task_idx, task.goal, task.done_when,
                        task.difficulty, task.phase, 'skipped', sess.attempts,
                        now, now)
        sess.tasks_skipped += 1
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
    with _database() as conn:
                          db.finish_session(conn, sess.db_session_id,
                                            sess.tasks_done, sess.tasks_skipped)
    sess.emit('closed')
    return {'tasks_done': sess.tasks_done, 'tasks_skipped': sess.tasks_skipped}


def serve(host: str = '127.0.0.1', port: int = 8000):
    """Run the server, and say so.

    Importing mlx_lm takes roughly half a minute, and `log_level='warning'`
    swallowed uvicorn's own "Uvicorn running on ..." line — so the first run of
    `make web` printed a urllib3 warning and then sat silent for 30 seconds
    with no way to tell starting from hung. The banner is printed before the
    slow import work finishes, and uvicorn's own line is left visible.
    """
    import uvicorn
    url = f'http://{host}:{port}'
    print(f'\n  Language Coach — starting…\n  Open {url} once the line below appears.\n'
          f'  Ctrl-C to stop.\n', flush=True)
    uvicorn.run(app, host=host, port=port, log_level='info')
