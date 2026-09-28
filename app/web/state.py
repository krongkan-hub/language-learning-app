"""A live web session: its state machine, the registry of sessions, and the request bodies.
"""
from __future__ import annotations

import queue
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel, Field
from .. import db
from ..scenarios.builtins import load_scenarios



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
    # Explain mode. `topic` is None for a roleplay session, and the two are
    # otherwise the same object: same drill, same coach, same summary, same
    # SSE contract — only the opening and the turn differ.
    topic: object = None
    # Words already taught that fit THIS scenario, retrieved once at session
    # start (app/retrieval.py) and offered to the NPC every turn. Computed
    # once because the query — the scenario — does not change mid-session, and
    # embedding on every turn would spend the learner's latency on an answer
    # that cannot move.
    review_words: list = field(default_factory=list)
    points: list = field(default_factory=list)
    hint_translations: dict = field(default_factory=dict)
    messages: list = field(default_factory=list)
    events: queue.Queue = field(default_factory=queue.Queue)
    state: str = BUSY
    task_idx: int = 0
    task_start_idx: int = 1
    attempts: int = 0
    tasks_done: int = 0
    tasks_skipped: int = 0
    # Which task indices were skipped or run out of attempts rather than
    # completed — the same set `tasks_skipped` counts and the summary calls
    # "missed". task_idx alone cannot tell them apart, since it advances
    # either way, so the sidebar showed a skipped task with the same green ✓
    # as a completed one and read 10/10 while the summary read 9/10.
    missed_idx: set = field(default_factory=set)
    # Words the NPC has already taught this session, keyed by lowercase so a
    # repeat is recognised, valued by the word as taught so a resumed page can
    # show it. The DB has always deduplicated (log_vocab increments
    # times_taught), but the turn event did not say so, and the panel and the
    # end-of-session chips appended every time — 「お取り寄せ」 taught twice
    # showed up twice and counted twice.
    taught_words: dict = field(default_factory=dict)
    drill_targets: list = field(default_factory=list)
    # How many event streams are attached, and the timer that closes the
    # session out once none are. A reload detaches one and attaches another a
    # moment later, and closing on the first half of that is what made a
    # reload lose the session.
    viewers: int = 0
    closer: object = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def explaining(self) -> bool:
        return self.topic is not None

    @property
    def current_task(self):
        if self.explaining:
            return self.points[self.task_idx] if self.task_idx < len(self.points) else None
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


class NewSession(BaseModel):
    language: str
    # Omitted means "surprise me", which is the normal way in: choosing from a
    # list of 80 turns every session into a decision, and a learner picking for
    # themselves drifts toward the scenarios they already find easy.
    scenario: Optional[str] = None
    # bounded: 0 raised in the greeting, a negative count drew nearly the whole catalogue
    tasks: int = Field(10, ge=1, le=20)
    # 'scenario' (roleplay) or 'explain'. Omitting the topic in explain mode
    # means "surprise me", the same as omitting the scenario.
    mode: str = 'scenario'
    topic: Optional[str] = None


class Utterance(BaseModel):
    # A turn is a spoken line. Unbounded, one request of "I want a coffee, "
    # x5000 queued thousands of coach calls (one per clause) behind the
    # model lock (security review 2026-09-27).
    text: str = Field(..., max_length=1000)


def _scenarios_for(language: str):
    return load_scenarios()
