"""A practice session: its state, how one starts, and the moves the learner
makes that are not model calls (skip, the drill check).

The turn logic in turns.py reports through Session.emit(), which hands each
event to `sink` — the terminal renderer in game.py, or a list in a test.
"""
from __future__ import annotations

import random
import re
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from typing import Callable, Optional

from .. import db
from ..coach import _normalize_phrase
from ..explain import load_topics
from ..llm import NPC_MOODS
from ..review import build_review_scenario, review_items
from ..scenarios.builtins import load_scenarios
from ..scenarios.compose import SceneSpec, compose_from_spec


AWAITING_INPUT = 'awaiting_input'
BUSY = 'busy'
# The learner cannot leave DRILL except by retyping every correction.
DRILL = 'drill'
FINISHED = 'finished'

MAX_TASK_ATTEMPTS = 4

# Kana (U+3040-30FF) and CJK unified ideographs (U+4E00-9FFF).
JAPANESE_SCRIPT = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
# Hyphen to horizontal bar (U+2010-2015) and the minus sign (U+2212).
_DASHES = re.compile(r'[\u2010-\u2015\u2212]')


@dataclass
class Session:
    language: str
    scenario: object
    tasks: list
    mood: str
    complication: Optional[str]
    user_id: int
    db_session_id: int
    sink: Callable = lambda event: None
    # Explain mode. `topic` is None for a roleplay session; otherwise the
    # same object, with the same drill, coach and summary — only the opening
    # and the turn differ.
    topic: object = None
    # Words already taught that fit THIS scenario, retrieved once at session
    # start (app/retrieval.py) and offered to the NPC every turn. Once,
    # because the query — the scenario — does not change mid-session.
    review_words: list = field(default_factory=list)
    # A review session's mistake class per task, in task order (#67): a task
    # completed here counts toward retiring that class. Empty otherwise.
    review_keys: list = field(default_factory=list)
    retried: int = 0
    points: list = field(default_factory=list)
    hint_translations: dict = field(default_factory=dict)
    messages: list = field(default_factory=list)
    state: str = BUSY
    task_idx: int = 0
    task_start_idx: int = 1
    attempts: int = 0
    tasks_done: int = 0
    tasks_skipped: int = 0
    # Words the NPC has already taught this session, keyed by lowercase so a
    # repeat is recognised (the DB increments times_taught either way).
    taught_words: dict = field(default_factory=dict)
    drill_targets: list = field(default_factory=list)

    @property
    def explaining(self) -> bool:
        return self.topic is not None

    @property
    def current_task(self):
        if self.explaining:
            return self.points[self.task_idx] if self.task_idx < len(self.points) else None
        return self.tasks[self.task_idx] if self.task_idx < len(self.tasks) else None

    @property
    def total_tasks(self) -> int:
        return len(self.points) if self.explaining else len(self.tasks)

    def emit(self, kind: str, **payload):
        self.sink({'type': kind, **payload})

    def say(self, text: str, card: Optional[str] = None, **npc_payload):
        """Record an NPC line and show it.

        `card` is the vocabulary block the NPC wrote with the line. It is kept
        beside the spoken text, never in it — the judge and the coach read
        what was said — and handed back only to the actor (actor_view).
        """
        message = {'role': 'assistant', 'content': text}
        if card:
            message['card'] = card
        self.messages.append(message)
        self.emit('npc', text=text, **npc_payload)

    def set_state(self, state: str):
        self.state = state


@contextmanager
def _database():
    conn = db.init_db()
    try:
        yield conn
    finally:
        conn.close()


# ── starting a session ──────────────────────────────────────────────────────

def _random_scenario(conn, user_id, catalogue):
    """Pick a scenario, favouring the ones played least.

    Uniform random keeps re-serving scenarios the learner has done nine times
    while leaving others untouched, so the draw is restricted to the
    least-played band and randomised inside it.
    """
    stats = db.get_all_scenario_stats(conn, user_id)
    plays = {sc.name: stats.get(sc.name, {}).get('plays', 0) for sc in catalogue}
    fewest = min(plays.values())
    pool = [sc for sc in catalogue if plays[sc.name] <= fewest]
    return random.choice(pool or catalogue)


def start_scenario_session(conn, user_id: int, language: str, scenario,
                           num_tasks: int = 10, sink: Callable = lambda e: None) -> Session:
    db.abandon_stale_sessions(conn, user_id)
    seen = db.get_seen_task_goals(conn, user_id, scenario.name)
    retry = db.get_unfinished_task_goals(conn, user_id, scenario.name)
    tasks = scenario.get_session_tasks(num_tasks=num_tasks, seen_goals=seen, retry_goals=retry)
    sess = _new_scenario_session(conn, user_id, language, scenario, tasks, sink)
    # Unfinished goals come back in the next session of a scenario; the
    # learner is told so rather than left to wonder why one looks familiar.
    sess.retried = sum(1 for task in tasks if task.goal in retry)
    return sess


def find_resumable_session(conn, user_id: int, language: str):
    """(row, scenario) for an interrupted roleplay session worth resuming, or
    None. Open sessions that are not — nothing logged yet, every task
    logged, or a scenario no longer in the catalogue — are closed on the way."""
    db.abandon_stale_sessions(conn, user_id)
    catalogue = {s.name: s for s in scenario_catalogue()}
    while (row := db.get_resumable_session(conn, user_id, language)) is not None:
        scenario = _played_scenario(row, catalogue.get(row['scenario_name']))
        goals = {task.goal for task in scenario.tasks} if scenario else set()
        logged = row['logged_goals']
        if logged and set(logged) <= goals and len(logged) < row['tasks_total']:
            return row, scenario
        db.finish_session(conn, row['id'], row['tasks_done'], row['tasks_missed'])
    return None


def _played_scenario(row: dict, legacy):
    """The scenario a session was played in: its stored scene rebuilt, or the
    legacy scenario when the scene is NULL (the default composition) or no
    longer rebuilds into this archetype. A composed scene draws a subset of
    the archetype's tasks, so the goal check above runs against that set."""
    if legacy is None or row.get('scene') is None:
        return legacy
    try:
        scenario, _ = compose_from_spec(SceneSpec.from_dict(row['scene']))
    except (KeyError, TypeError):
        return legacy
    return scenario if scenario.name == legacy.name else legacy


def resume_scenario_session(conn, user_id: int, language: str, row: dict, scenario,
                            sink: Callable = lambda e: None) -> Session:
    """Carry on an interrupted session in its own row, mood and complication.

    No transcript is stored (OPEN-37), so the conversation starts afresh;
    the tasks already logged keep their places, so the counter, the log's
    task_index and the summary carry on from where it stopped. The rest are
    drawn again from the tasks not yet logged, as a new session would.
    """
    by_goal = {task.goal: task for task in scenario.tasks}
    done = [by_goal[g] for g in row['logged_goals']]
    logged = set(row['logged_goals'])
    rest = replace(scenario, tasks=[task for task in scenario.tasks if task.goal not in logged])
    seen = db.get_seen_task_goals(conn, user_id, scenario.name)
    retry = db.get_unfinished_task_goals(conn, user_id, scenario.name)
    tasks = rest.get_session_tasks(num_tasks=row['tasks_total'] - len(done),
                                   seen_goals=seen, retry_goals=retry)
    return Session(language=language, scenario=scenario, tasks=done + tasks,
                   mood=row['mood'], complication=row['complication'], user_id=user_id,
                   db_session_id=row['id'], sink=sink, task_idx=len(done),
                   tasks_done=row['tasks_done'], tasks_skipped=row['tasks_missed'])


def start_review_session(conn, user_id: int, language: str,
                         sink: Callable = lambda e: None) -> Optional[Session]:
    """A session built from the learner's own corrections, or None when the
    coach has not corrected anything short enough to practise yet."""
    mistakes = db.mistakes_to_practice(conn, user_id, language)
    scenario = build_review_scenario(mistakes, language)
    if scenario is None:
        return None
    db.abandon_stale_sessions(conn, user_id)
    sess = _new_scenario_session(conn, user_id, language, scenario, list(scenario.tasks), sink)
    sess.review_keys = [i['key'] for i in review_items(mistakes, language)]
    return sess


def _new_scenario_session(conn, user_id, language, scenario, tasks, sink) -> Session:
    mood = random.choice(NPC_MOODS)
    complication = random.choice(scenario.complications) if scenario.complications else None
    return Session(language=language, scenario=scenario, tasks=tasks, mood=mood,
                   complication=complication, user_id=user_id, sink=sink,
                   db_session_id=db.create_session(conn, user_id, scenario.name, language,
                                                   mood, complication, len(tasks)))


def start_explain_session(conn, user_id: int, language: str, topic,
                          sink: Callable = lambda e: None) -> Session:
    db.abandon_stale_sessions(conn, user_id)
    points = topic.points(language)
    return Session(language=language, scenario=None, tasks=[], topic=topic, points=points,
                   mood='', complication=None, user_id=user_id, sink=sink,
                   db_session_id=db.create_session(conn, user_id, topic.title(language),
                                                   language, '', None, len(points),
                                                   kind='explain'))


def scenario_catalogue():
    return [s for s in load_scenarios() if s.tasks]


def topic_catalogue():
    return load_topics()


# ── the learner's moves that are not model calls ────────────────────────────

def skip_task(sess: Session):
    """Give up on the current task and move on. Logged as skipped, counted
    with the failed ones in the summary's "Skipped/Failed"."""
    task = sess.current_task
    # Explain mode has no Task objects and no Scenario, so there is no row to
    # log — the skip itself still happens.
    if not sess.explaining:
        now = db._utcnow()
        with _database() as conn:
            db.log_task(conn, sess.db_session_id, sess.scenario.name, sess.user_id,
                        sess.task_idx, task.goal, task.done_when, task.difficulty,
                        task.phase, 'skipped', sess.attempts, now, now)
    sess.tasks_skipped += 1
    sess.task_idx += 1
    sess.attempts = 0
    sess.task_start_idx = len(sess.messages)


def drill_form(text: str) -> str:
    """What a retyped correction is compared on: the words, not the typing.

    "hi do you use organic farming" is the same answer as "Hi! Do you use
    organic farming?" — capitals and a mid-sentence "!" are not the
    correction being practised. Apostrophes and hyphens stay: "dont" for
    "don't" IS a spelling the drill should catch.
    """
    # NFKC first: a Japanese IME types ３ and ＯＫ where the target has 3 and OK.
    text = unicodedata.normalize('NFKC', text)
    text = _DASHES.sub('-', text)
    text = _normalize_phrase(text).lower()
    text = re.sub(r"[^\w\s'\-]", ' ', text)      # \w keeps kana and kanji
    if JAPANESE_SCRIPT.search(text):
        return re.sub(r'\s+', '', text)          # Japanese is written without spaces
    return re.sub(r'\s+', ' ', text).strip()


def check_drill(sess: Session, typed: str) -> bool:
    """One retype against the current correction. A right one pops it; the
    drill is over when none are left."""
    if drill_form(typed) != drill_form(sess.drill_targets[0]):
        return False
    sess.drill_targets.pop(0)
    return True
