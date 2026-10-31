"""Where does a learner turn's time go? Per stage, over a fixed script.

    python3 dev/tools/probe_turn_latency.py [--out result.json] [--compare base.json]

Plays one scripted Fine Dining session in English and one in Japanese
through the real turn code (app/cli/turns.py: greeting, then judge -> actor
-> coach per message) with the real model, into a throwaway database schema.
The tasks, mood and complication are pinned and the samplers seeded, so two
runs do the same work and differ only in the code under test.

Timings come from the app's own OpenTelemetry spans (`turn`, `judge`,
`actor`, `coach`, `llm.generate` per cache key), collected in memory, plus
spans this probe wraps around the bookkeeping the app does not trace
(review-word retrieval, hint translation, vocab logging, mistake records,
vocab credit). Two learner-facing numbers are taken from the turn's events:

    first sentence  Enter -> the NPC's first sentence on screen
    first token     Enter -> the actor's first generated token
    turn            Enter -> input open again (the `turn` span; the #43
                    target is this at p50 < 8 s)

--think N waits N seconds before each message (default 5), standing in for
the learner reading the reply and typing: the app warms the next turn's
prompt caches in that gap (client.prefill), and a probe with no gap would
measure a learner who answers instantly. --think 0 is that worst case.

Run it alone: it loads the 7B, and two model jobs at once have OOM-killed
runs on the 16 GB machine.
"""
import argparse
import json
import os
import random
import statistics
import sys
import tempfile
import threading
import time

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
# A schema of its own (app/db/connection.py), dropped at the end.
_DB_PATH = os.path.join(tempfile.gettempdir(), f'probe_turn_latency_{os.getpid()}.db')
os.environ['LANGUAGE_COACH_DB'] = _DB_PATH

import mlx.core as mx  # noqa: E402
from opentelemetry import trace  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # noqa: E402

from app import db  # noqa: E402
from app.cli import state, turns  # noqa: E402
from app.llm import _ensure_model, client, reset_prompt_caches  # noqa: E402
from app.scenarios.builtins import SCENARIOS  # noqa: E402
from app.telemetry import tracer  # noqa: E402

SCENARIO = 'Fine Dining Restaurant'
MOOD, COMPLICATION = 'chatty and friendly, happy to chat while you work', None
TASKS = [
    'Learner asked about the history or background of the restaurant.',
    'Learner cancelled an order.',
    'Learner requested a dessert modification or allergen-free option.',
    'Learner asked for a quieter seating location due to noise.',
    'Learner ordered a side salad.',
    'Learner ordered or asked for dessert.',
    'Learner complimented the chef.',
    "Learner asked about the chef's background or culinary experience.",
]
# One off-task line (a judge NO), a few errors for the coach, and two long
# messages that the coach cuts into clause passes.
SCRIPT = {
    'English': [
        'Good evening! This place looks beautiful, how long has the restaurant been here?',
        'Actually, I want to cancel the soup I ordered before, sorry.',
        'The weather is so nice tonight.',
        'Can the chocolate cake be made without nuts? I have allergy to nuts.',
        "It is very noisy near the kitchen, so could we move to a quieter table, because my wife can't hear me well?",
        "I'd like a side salad, please.",
        'What do you recommend for dessert tonight?',
        'Please tell the chef the fish was amazing, I really enjoyed it and my wife enjoyed it too.',
        'Where did the chef learn to cook? Did he worked in France before?',
    ],
    'Japanese': [
        'こんばんは。このレストランはいつからありますか？',
        'すみません、さっき頼んだスープをキャンセルしたいです。',
        '今日はとても暑いですね。',
        'チョコレートケーキはナッツなしで作れますか？ナッツのアレルギーがあります。',
        'キッチンの近くはとてもうるさいので、静かな席に移動してもいいですか、妻の声が聞こえません。',
        'サイドサラダを一つお願いします。',
        'デザートは何がおすすめですか？',
        'シェフに魚がとてもおいしかったと伝えてください。',
        'シェフはどこで料理を勉強しましたか？フランスで働くましたか？',
    ],
}

# Bookkeeping the app does not trace, wrapped here so it shows up too.
_WRAPPED = {'_retrieve_review_words': 'retrieval', 'translate_hints': 'hints',
            '_record_mistakes': 'mistakes', '_credit_vocab_use': 'vocab_credit',
            '_advance_after_judge': 'judge_bookkeeping'}


def _wrap(module, name, span_name):
    fn = getattr(module, name)

    def wrapped(*a, **k):
        with tracer.start_as_current_span(span_name):
            return fn(*a, **k)
    setattr(module, name, wrapped)


def _wrap_log_vocab():
    fn = db.log_vocab

    def wrapped(*a, **k):
        with tracer.start_as_current_span('vocab_log'):
            return fn(*a, **k)
    db.log_vocab = wrapped


def _wrap_first_token(marks: dict):
    """Timestamp the actor's first generated token (before any sentence)."""
    fn = client.stream_generate

    def wrapped(*a, **k):
        first = True
        for item in fn(*a, **k):
            if first:
                marks.setdefault('first_token', time.perf_counter())
                first = False
            yield item
    client.stream_generate = wrapped


def _count_prefill(marks: dict):
    """Tokens the turn itself had to run through the model before
    generating (main thread only; the background warm is not the turn's).
    Steadier than seconds on a machine whose speed drifts with memory
    pressure, and it is what prompt caching changes."""
    fn = client._prepare_prompt_cache_for_call

    def wrapped(model, tokenizer, prompt, key):
        out = fn(model, tokenizer, prompt, key)
        if threading.current_thread() is threading.main_thread():
            marks['prefill_tokens'] = marks.get('prefill_tokens', 0) + len(out[1])
        return out
    client._prepare_prompt_cache_for_call = wrapped


def _pct(values, q):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def play(language: str, exporter, marks: dict, think: float) -> list:
    """One scripted session; returns one record per learner turn."""
    scenario = next(s for s in SCENARIOS if s.name == SCENARIO)
    by_done = {t.done_when: t for t in scenario.tasks}
    random.seed(7)
    mx.random.seed(7)
    reset_prompt_caches()
    events = []

    def sink(ev):
        events.append((time.perf_counter(), ev))

    with state._database() as conn:
        uid = db.get_or_create_user(conn, target_lang=language)
        sess = state.start_scenario_session(conn, uid, language, scenario,
                                            num_tasks=len(TASKS), sink=sink)
    sess.tasks = [by_done[d] for d in TASKS]
    sess.mood, sess.complication = MOOD, COMPLICATION
    t0 = time.perf_counter()
    turns.open_session(sess)
    print(f'  [{language}] greeting {time.perf_counter() - t0:5.1f}s')

    records = []
    for text in SCRIPT[language]:
        if sess.state == state.FINISHED:
            break
        sess.drill_targets = []       # the drill is typing, not model work
        time.sleep(think)
        exporter.clear()
        marks.clear()
        start = len(events)
        t0 = time.perf_counter()
        turns.take_turn(sess, text)
        end = time.perf_counter()
        evs = events[start:]
        first_sentence = next((t for t, e in evs if e['type'] == 'sentence'), None)
        spans = {}
        for s in exporter.get_finished_spans():
            name = s.name
            if name == 'llm.generate':
                name = f"llm.{s.attributes.get('llm.cache_key') or 'uncached'}"
            spans.setdefault(name, []).append((s.end_time - s.start_time) / 1e9)
        done = next((e.get('done') for _, e in evs if e['type'] == 'task_result'), None)
        rec = {
            'language': language, 'text': text, 'turn_wall': end - t0,
            'first_sentence': (first_sentence - t0) if first_sentence else None,
            'first_token': (marks['first_token'] - t0) if 'first_token' in marks else None,
            'prefill_tokens': marks.get('prefill_tokens', 0),
            'judge_done': done,
            'stages': {k: sum(v) for k, v in spans.items()},
            'calls': {k: len(v) for k, v in spans.items()},
            'npc': next((e['text'] for _, e in evs if e['type'] == 'npc'), ''),
            'coach': next((e['text'] for _, e in evs if e['type'] == 'coach'), ''),
        }
        records.append(rec)
        st = rec['stages']
        print(f"  [{language}] turn {rec['turn_wall']:5.1f}s  first-sentence "
              f"{(rec['first_sentence'] or 0):4.1f}s  judge {st.get('judge', 0):4.1f}  "
              f"actor {st.get('actor', 0):4.1f}  coach {st.get('coach', 0):4.1f}  "
              f"prefill {rec['prefill_tokens']:5d}  done={done}  {text[:40]}")
        if sess.state not in (state.AWAITING_INPUT, state.DRILL, state.FINISHED):
            sess.set_state(state.AWAITING_INPUT)
    return records


def summarize(records: list) -> dict:
    keys = ['turn', 'first_sentence', 'first_token', 'prefill_tokens']
    stage_names = sorted({k for r in records for k in r['stages']})
    out = {}
    for k in keys:
        vals = [r['stages'].get('turn') if k == 'turn' else r[k] for r in records]
        vals = [v for v in vals if v is not None]
        out[k] = {'n': len(vals), 'p50': _pct(vals, .5), 'p95': _pct(vals, .95)}
    for name in stage_names:
        if name == 'turn':
            continue
        vals = [r['stages'][name] for r in records if name in r['stages']]
        calls = [r['calls'][name] for r in records if name in r['calls']]
        out[name] = {'n': len(vals), 'p50': _pct(vals, .5), 'p95': _pct(vals, .95),
                     'calls_per_turn': statistics.mean(calls)}
    return out


def _fmt(v):
    return '    -' if v is None else f'{v:5.2f}'


def print_table(summary: dict, base: dict = None):
    print(f"\n{'stage':22s} {'n':>3s} {'p50':>6s} {'p95':>6s}" +
          (f" {'base p50':>9s} {'base p95':>9s}" if base else ''))
    for name, s in summary.items():
        if name == 'prefill_tokens':
            print(f"{name:22s} {s['n']:3d} {s['p50']:6.0f} {s['p95']:6.0f}  tokens"
                  + (f"   {base[name]['p50']:6.0f} {base[name]['p95']:6.0f}"
                     if base and name in base else ''))
            continue
        line = f"{name:22s} {s['n']:3d} {_fmt(s['p50'])}s {_fmt(s['p95'])}s"
        if base and name in base:
            line += f"   {_fmt(base[name]['p50'])}s   {_fmt(base[name]['p95'])}s"
        print(line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', help='write records and summary as JSON')
    ap.add_argument('--compare', help='a previous --out file to print beside this run')
    ap.add_argument('--languages', default='English,Japanese')
    ap.add_argument('--think', type=float, default=5.0,
                    help='seconds of learner reading/typing before each message')
    args = ap.parse_args()

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    for name, span_name in _WRAPPED.items():
        _wrap(turns, name, span_name)
    _wrap_log_vocab()
    marks = {}
    _wrap_first_token(marks)
    _count_prefill(marks)

    t0 = time.perf_counter()
    _ensure_model()
    print(f'model load {time.perf_counter() - t0:.1f}s (not counted)')

    records = []
    try:
        for language in args.languages.split(','):
            records += play(language, exporter, marks, args.think)
    finally:
        from app.db.connection import connect, schema_for
        with connect('public') as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema_for(_DB_PATH)}" CASCADE')
            conn.commit()

    summary = {'all': summarize(records)}
    for language in args.languages.split(','):
        summary[language] = summarize([r for r in records if r['language'] == language])
    base = None
    if args.compare:
        with open(args.compare, encoding='utf-8') as f:
            base = json.load(f)['summary']
    for group, s in summary.items():
        print(f'\n== {group} ==')
        print_table(s, base and base.get(group))
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({'summary': summary, 'records': records}, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
