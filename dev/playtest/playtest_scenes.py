"""AI playtest of composed scenes through the real turn code.

    ./venv/bin/python dev/playtest/playtest_scenes.py --seeds 2,4,5,7,11
    ./venv/bin/python dev/playtest/playtest_scenes.py --seeds 2,4 --legacy
    ./venv/bin/python dev/playtest/playtest_scenes.py --seeds 2 --languages Japanese --out t.json

Each seed is the scene `main.py --seed N` offers (app/cli/state.py
composed_scene); --legacy plays the same archetypes as their legacy scenarios,
which is the control for the completion rate. A model learner (prompted with
the place, who it is talking to and the current objective) plays each session
through app/cli/turns.py — greeting, judge -> actor -> coach — with the real
7B, into a throwaway database schema. The drill is skipped (it is typing, not
model work). Prints each transcript for reading and a completion summary.

Run it alone: it loads the 7B (16 GB machine).
"""
import argparse
import json
import os
import random
import re
import sys
import tempfile

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
_DB_PATH = os.path.join(tempfile.gettempdir(), f'playtest_scenes_{os.getpid()}.db')
os.environ['LANGUAGE_COACH_DB'] = _DB_PATH

from app import db  # noqa: E402
from app.cli import state, turns  # noqa: E402
from app.i18n import scenario_name, scenario_place, scenario_speaker  # noqa: E402
from app.llm import _ensure_model, _llm_chat, reset_prompt_caches  # noqa: E402
from app.scenarios.compose import ARCHETYPES  # noqa: E402

LEARNER_SYS = """\
You are a language learner (upper-intermediate) practising {language}. You are
a customer or visitor in this scene, talking to the other person.
PLACE: {place}
YOU ARE TALKING TO: {speaker}
YOUR CURRENT OBJECTIVE: {goal}

Reply ONLY in {language}, in 1-2 natural spoken sentences that work toward
your objective and answer what was just said. No stage directions, no quotes,
no name prefix."""

MAX_TURNS = 14


def _learner_line(sess, speaker: str) -> str:
    task = sess.current_task
    goal = sess.hint_translations.get((sess.task_idx, task.goal), task.goal)
    system = LEARNER_SYS.format(language=sess.language, place=sess.scenario.place,
                                speaker=speaker, goal=goal)
    view = [{'role': 'user' if m['role'] == 'assistant' else 'assistant', 'content': m['content']}
            for m in sess.messages[-8:]]
    out = _llm_chat([{'role': 'system', 'content': system}] + view,
                    options={'temperature': 0.6, 'max_tokens': 120, 'script': sess.language})
    text = re.sub(r'<think>.*?</think>', '', out['message']['content'], flags=re.DOTALL)
    return re.sub(r'\*[^*]*\*', '', text).replace('"', '').strip().split('\n')[0]


def play(seed: int, language: str, legacy: bool, num_tasks: int) -> dict:
    scenario, spec = state.composed_scene(seed=seed)
    if legacy:
        scenario, spec = ARCHETYPES[spec.archetype], None
    random.seed(seed)
    reset_prompt_caches()
    log = []

    def sink(ev):
        if ev['type'] == 'npc':
            log.append({'who': ev.get('speaker'), 'text': ev['text']})
        elif ev['type'] == 'task_result':
            log.append({'who': '#', 'text': 'TASK DONE' if ev.get('done') else
                        ('TASK FAILED (moved on)' if ev.get('moved_on') else 'not yet')})
        elif ev['type'] == 'coach':
            log.append({'who': 'coach', 'text': ev['text']})
        elif ev['type'] == 'error':
            log.append({'who': '!', 'text': ev.get('detail', '')})

    with state._database() as conn:
        uid = db.get_or_create_user(conn, target_lang=language)
        sess = state.start_scenario_session(conn, uid, language, scenario,
                                            num_tasks=num_tasks, sink=sink, scene=spec)
    speaker = scenario_speaker(scenario, language)
    turns.open_session(sess)
    for _ in range(MAX_TURNS):
        if sess.state == state.FINISHED or sess.current_task is None:
            break
        sess.drill_targets = []
        if sess.state == state.DRILL:
            sess.set_state(state.AWAITING_INPUT)
        task = sess.current_task
        log.append({'who': '>', 'text': f'objective: {task.goal}'})
        text = _learner_line(sess, speaker) or '...'
        log.append({'who': 'learner', 'text': text})
        turns.take_turn(sess, text)
    if sess.state != state.FINISHED:
        turns._finish(sess)
    return {'seed': seed, 'language': language, 'legacy': legacy,
            'spec': spec.as_dict() if spec else None,
            'name': scenario_name(scenario, language), 'place': scenario_place(scenario, language),
            'speaker': speaker, 'complication': sess.complication,
            'tasks': [t.goal for t in sess.tasks], 'done': sess.tasks_done,
            'total': sess.total_tasks, 'log': log}


def print_run(r: dict):
    print('=' * 78)
    print(f"seed {r['seed']} [{r['language']}] {'LEGACY' if r['legacy'] else 'COMPOSED'}: "
          f"{r['name']} — {r['speaker']}")
    print(f"  place: {r['place']}   complication: {r['complication']}")
    for line in r['log']:
        if line['who'] == 'coach':
            continue
        print(f"  [{line['who']}] {line['text']}")
    print(f"  -> {r['done']}/{r['total']} tasks completed")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', default='2,4,5,7,11')
    ap.add_argument('--languages', default='English,Japanese')
    ap.add_argument('--tasks', type=int, default=4)
    ap.add_argument('--legacy', action='store_true', help='the same archetypes, legacy')
    ap.add_argument('--out')
    args = ap.parse_args()
    _ensure_model()
    runs = []
    try:
        for seed in (int(s) for s in args.seeds.split(',')):
            for language in args.languages.split(','):
                runs.append(play(seed, language, args.legacy, args.tasks))
                print_run(runs[-1])
                sys.stdout.flush()
    finally:
        from app.db.connection import connect, schema_for
        with connect('public') as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema_for(_DB_PATH)}" CASCADE')
            conn.commit()
    done, total = sum(r['done'] for r in runs), sum(r['total'] for r in runs)
    print(f"\nCompletion: {done}/{total} = {100 * done / max(total, 1):.1f}%"
          f" ({'legacy' if args.legacy else 'composed'})")
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(runs, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
