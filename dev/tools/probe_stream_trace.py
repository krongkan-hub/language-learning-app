"""OPEN-52 from real play: why does an NPC turn end on the canned question?

Drives the CLI's turn logic in-process (app/cli, the real model, no
patches) through N scenarios x a few learner turns, with
LANGUAGE_COACH_TRACE on, then tallies what stream_actor did with every
sentence: shown, rejected (by which rule), over the limit, or dropped
because the last slot was kept for a question — and how often the salvage
line was appended.

The learner lines are deliberately generic so they fit any scenario; the
point is the NPC's side, not the learner's.

    python3 dev/tools/probe_stream_trace.py out_dir
    N=12 LANG_=Japanese python3 dev/tools/probe_stream_trace.py out_dir

One 7B at a time. Writes out_dir/trace.jsonl and prints the tally.
"""
import collections
import json
import os
import random
import sys

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else '/tmp/stream_trace'
os.makedirs(OUT_DIR, exist_ok=True)
os.environ['LANGUAGE_COACH_TRACE'] = os.path.join(OUT_DIR, 'trace.jsonl')
os.environ['LANGUAGE_COACH_DB'] = os.path.join(OUT_DIR, 'probe.db')
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
from app import db                                                  # noqa: E402
from app.cli import state                                           # noqa: E402
from app.cli import turns as cli_turns                              # noqa: E402

N = int(os.environ.get('N', '12'))
LANG = os.environ.get('LANG_', 'English')
SEED = int(os.environ.get('SEED', '3'))
LINES = {
    'English': ["Hi, could you help me with something?",
                "Could you tell me a bit more about the options?",
                "That sounds good. How much would that be?",
                "Okay, thank you so much."],
    'Japanese': ["すみません、ちょっと手伝ってもらえますか。",
                 "もう少し詳しく教えてください。",
                 "いいですね。いくらになりますか。",
                 "わかりました。ありがとうございます。"],
}[LANG]


def main() -> None:
    catalogue = state.scenario_catalogue()
    random.Random(SEED).shuffle(catalogue)
    for n, scenario in enumerate(catalogue[:N], 1):
        with state._database() as conn:
            uid = db.get_or_create_user(conn, target_lang=LANG)
            sess = state.start_scenario_session(conn, uid, LANG, scenario)
        cli_turns.open_session(sess)
        for text in LINES:
            # finish any correction drill by typing its targets
            while sess.drill_targets:
                state.check_drill(sess, sess.drill_targets[0])
            if sess.current_task is None:
                break
            cli_turns.take_turn(sess, text)
        cli_turns._finish(sess)
        print(f'[{n}/{N}] {scenario.name}', flush=True)
    tally = collections.Counter()
    turns = salvaged = opened = 0
    for line in open(os.environ['LANGUAGE_COACH_TRACE'], encoding='utf-8'):
        rec = json.loads(line)
        turns += 1
        salvaged += any('salvage' in t for t in rec['trace'])
        opened += any('opened_up' in t for t in rec['trace'])
        for t in rec['trace']:
            if 'fate' in t:
                tally[t['fate'].split(':')[0]] += 1
    print(f'\n{turns} NPC turns traced, canned salvage on {salvaged}, '
          f'own yes/no question opened up on {opened}')
    for fate, count in tally.most_common():
        print(f'  {count:4}  {fate}')


if __name__ == '__main__':
    main()
