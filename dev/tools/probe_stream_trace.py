"""OPEN-52 from real play: why does an NPC turn end on the canned question?

Drives the web app in-process (FastAPI TestClient, the real model, no
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
import time

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
from fastapi.testclient import TestClient                           # noqa: E402

from app import web                                                 # noqa: E402

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


def _wait(sess, states=(web.AWAITING_INPUT, web.DRILL, web.FINISHED), limit=240):
    t = time.time()
    while sess.state not in states and time.time() - t < limit:
        time.sleep(0.2)


def main() -> None:
    client = TestClient(web.app)
    names = [s['name'] for s in client.get(f'/api/scenarios?language={LANG}').json()['scenarios']]
    random.Random(SEED).shuffle(names)
    for n, name in enumerate(names[:N], 1):
        sid = client.post('/api/session', json={'language': LANG, 'scenario': name}).json()['session']
        sess = web.SESSIONS[sid]
        _wait(sess)
        for text in LINES:
            if sess.state == web.DRILL:
                # finish any correction drill by typing its targets
                for target in list(sess.drill_targets):
                    client.post(f'/api/drill/{sid}', json={'text': target})
                _wait(sess)
            if sess.state != web.AWAITING_INPUT:
                break
            client.post(f'/api/turn/{sid}', json={'text': text})
            _wait(sess)
        client.post(f'/api/session/{sid}/end')
        print(f'[{n}/{N}] {name}', flush=True)
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
