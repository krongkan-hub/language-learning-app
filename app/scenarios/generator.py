"""LLM-driven scenario generation pipeline.

Given a free-text topic (e.g. "buying a train ticket"), this module asks the
local LLM to generate a full ``Scenario`` with tasks, complications, and NPC
personality — then validates and persists the result.

Dependencies: ``ollama``, ``httpx`` (already in the project), ``db.py``,
``scenarios.py`` (for the ``Task`` / ``Scenario`` dataclasses).
"""

import json
import re

from .models import Task, Scenario
import db

# ---------------------------------------------------------------------------
# System prompt — the LLM acts as a "Game Master"
# ---------------------------------------------------------------------------

GENERATOR_SYS = """\
You are a Game Master for a language-learning role-play application. The learner
will practice conversation in a real-world setting defined by the TOPIC below.

Your job: design ONE complete scenario with exactly these parts:

1. **name** — a short, evocative name for the setting (2-4 words).
2. **place** — a one-sentence description of the physical location.
3. **role** — "You are a ..." sentence defining the NPC the AI will play.
4. **speaker** — a single word: the NPC's role title (e.g. "Clerk", "Waiter",
   "Librarian"). This is used as a display label, NOT a proper name.
5. **complications** — a JSON array of 3-5 short strings. Each is a realistic
   obstacle the NPC might face (out of stock, system down, policy limit, etc.).
6. **tasks** — a JSON array of exactly 15 task objects (see format below).

TASK FORMAT — every task is a JSON object with these keys:
- "goal": a short, specific instruction for the learner (what they must say/do).
- "hint": a longer coaching sentence giving context and strategy.
- "done_when": a sentence starting with "Learner " that describes the observable
  speech act the judge will look for. For multi-clause advanced tasks, join
  clauses with " AND " (e.g. "Learner declined AND gave a reason AND asked for
  an alternative."). EVERY done_when MUST start with the word "Learner".
- "difficulty": either "standard" (simple request/question) or "advanced"
  (negotiation, comparison, justification, multi-clause). At least 10 of the 15
  tasks must be "advanced".
- "phase": integer 1, 2, or 3.
  1 = opening tasks (arrival, first contact, stating purpose). At least 2 tasks.
  3 = closing tasks (payment, farewell, receipt). At least 2 tasks.
  2 = everything in between (the default for most tasks).
- "reactive": boolean. true if the task presupposes something already happened
  (an order placed, a product received, a prior complaint). false if the learner
  can initiate it from scratch. At least 5 tasks must be reactive.
- "scene_hint": a string. Non-empty ONLY when the task requires an ambient
  environmental condition (loud noise, a dirty surface, a smell) that the NPC
  must establish in the scene. Empty string for most tasks.

DIFFICULTY GUIDELINES for "advanced" tasks:
- Require the learner to produce at least two clauses (e.g. state a preference
  AND give a reason, raise a problem AND propose a solution).
- Include negotiation, comparison, polite disagreement, escalation, or
  hypothetical reasoning.
- The "done_when" must use AND to connect multiple observable criteria.

OUTPUT: respond with a single valid JSON object — no commentary, no markdown
fences, no explanation. Just the raw JSON.
"""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_scenario_json(data: dict) -> None:
    """Raise ValueError with a specific message if the dict is malformed."""
    # Top-level keys
    for key in ('name', 'place', 'role', 'speaker', 'tasks'):
        if key not in data or not data[key]:
            raise ValueError(f"Missing or empty top-level key: '{key}'")
    for key in ('name', 'place', 'role', 'speaker'):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"'{key}' must be a non-empty string")

    if not isinstance(data.get('complications', []), list):
        raise ValueError("'complications' must be a list")

    tasks = data['tasks']
    if not isinstance(tasks, list) or len(tasks) < 10:
        raise ValueError(f"Need at least 10 tasks, got {len(tasks) if isinstance(tasks, list) else 'non-list'}")

    valid_difficulties = {'standard', 'advanced'}
    valid_phases = {1, 2, 3}

    for i, t in enumerate(tasks):
        for field in ('goal', 'hint', 'done_when'):
            if not isinstance(t.get(field), str) or not t[field].strip():
                raise ValueError(f"Task {i}: missing or empty '{field}'")
        if not t['done_when'].startswith('Learner'):
            raise ValueError(f"Task {i}: done_when must start with 'Learner', "
                             f"got: '{t['done_when'][:40]}'")
        if t.get('difficulty', 'standard') not in valid_difficulties:
            raise ValueError(f"Task {i}: invalid difficulty '{t.get('difficulty')}'")
        if t.get('phase', 2) not in valid_phases:
            raise ValueError(f"Task {i}: invalid phase '{t.get('phase')}'")
        if not isinstance(t.get('reactive', False), bool):
            raise ValueError(f"Task {i}: 'reactive' must be boolean")

    # Distribution checks
    advanced_count = sum(1 for t in tasks if t.get('difficulty') == 'advanced')
    if advanced_count < 7:
        raise ValueError(f"Need at least 7 advanced tasks, got {advanced_count}")

    phases = {t.get('phase', 2) for t in tasks}
    if 1 not in phases:
        raise ValueError("Need at least one phase-1 (opening) task")
    if 3 not in phases:
        raise ValueError("Need at least one phase-3 (closing) task")


# ---------------------------------------------------------------------------
# Parsing: dict → dataclass objects
# ---------------------------------------------------------------------------

def parse_scenario_dict(data: dict) -> Scenario:
    """Convert a validated JSON dict into a Scenario with Task objects."""
    tasks = [
        Task(
            goal=t['goal'],
            hint=t['hint'],
            done_when=t['done_when'],
            difficulty=t.get('difficulty', 'standard'),
            scene_hint=t.get('scene_hint', ''),
            phase=t.get('phase', 2),
            reactive=t.get('reactive', False),
        )
        for t in data['tasks']
    ]
    return Scenario(
        name=data['name'],
        place=data['place'],
        role=data['role'],
        speaker=data['speaker'],
        tasks=tasks,
        complications=data.get('complications', []),
    )


# ---------------------------------------------------------------------------
# Generation pipeline
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    """Extract the first JSON object from LLM output, stripping markdown fences
    and <think> blocks."""
    # Strip <think>...</think>
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Strip markdown code fences
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    # Find the outermost { ... }
    start = text.find('{')
    if start == -1:
        raise ValueError("No JSON object found in LLM output")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("Unterminated JSON object in LLM output")


def generate_scenario(topic: str, language: str, user_id: int,
                      conn, llm_chat_fn, model: str = 'qwen3:8b',
                      max_attempts: int = 3) -> tuple[Scenario, int]:
    """Generate a scenario from a topic, validate, persist, return (Scenario, scenario_id).

    ``llm_chat_fn`` is injected so callers pass the existing ``_llm_chat``
    from main.py — no duplicate client setup.

    Raises RuntimeError after ``max_attempts`` failures.
    """
    gen_opts = {'temperature': 0.7, 'num_ctx': 8192, 'num_predict': 4096}
    prompt = f"TOPIC: {topic}\nTARGET LANGUAGE for all task text: English (the tasks are always in English; the learner practices {language} in conversation, but goals/hints/done_when stay in English for the judge)."

    last_error = None
    for attempt in range(max_attempts):
        try:
            response = llm_chat_fn(
                messages=[
                    {"role": "system", "content": GENERATOR_SYS},
                    {"role": "user", "content": prompt},
                ],
                options=gen_opts,
            )
            raw = response['message']['content']
            data = _extract_json(raw)
            validate_scenario_json(data)
            scenario = parse_scenario_dict(data)

            # Persist
            scenario_id = db.save_scenario(conn, user_id, topic, data,
                                           source='generated', model=model)
            return scenario, scenario_id

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            last_error = e
            continue

    raise RuntimeError(
        f"Failed to generate a valid scenario after {max_attempts} attempts. "
        f"Last error: {last_error}"
    )
