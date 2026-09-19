"""How much of a clear JAPANESE error does the coach simply not correct?

The Japanese half of OPEN-10, measured the way OPEN-39 measured the English
half. `eval_coach.py`'s Japanese cases cover the classes that already have a
net behind them — transitivity, counters, te-form 音便, i-adjective past,
を/に on 会う, place に/で, 住む, 結婚, stranded adverbs, 薬を食べる. Every one
of those is code, so the suite mostly measures the nets, not the model.

This probe deliberately picks classes NO fixture and NO net covers:

    exist      いる/ある animacy          猫があります / 本がいます
    na-adj     な-adjective + の           有名の店
    i-adj-neg  い-adjective + じゃない      高いじゃないです
    adverb     い-adjective used adverbially 早い歩いて
    time-ni    relative time word + に      先週に / 毎日に
    de-exist   で with an existence verb    教室で学生がいます

Every input carries exactly ONE unambiguous error a teacher would mark. The
two CONTROLS at the end are classes an existing net handles, so if they fall
the harness is broken rather than the coach.

Read this WITH the clean arm, never alone. Recall is trivially raised by
correcting everything, and over-correction is the failure this project treats
as worst. The clean arm carries the twin of every probe class (有名な店,
高くないです, 三時に) plus three SHORT replies — OPEN-39's clean arm was eight
full sentences, that gap hid a design that broke "No problem." into
"No problems.", and the lesson is written down here rather than relearned.

MODE=plain re-runs the same sentences with NO coach prompt at all, asking the
model outright whether the sentence is correct. That single number decides the
whole approach: OPEN-07 found the model does not KNOW 友達を会いました is
wrong (so only a net can help), OPEN-39 found the opposite for English (so the
prompt was suppressing knowledge the model had). Measure, never assume.

Usage:
    python3 dev/evals/eval_jarecall.py eval_out.json          # full run
    SLICE=12 python3 dev/evals/eval_jarecall.py eval_out.json # 12 cases, then exit
    MODE=plain ITERS=3 python3 dev/evals/eval_jarecall.py plain_out.json

Every case is written to the output file as soon as it finishes, so a run that
is killed for memory costs one case, and re-running resumes. SLICE exists for
the same reason: each slice is a process that exits.
"""
import json
import os
import re
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)          # find the project root by
sys.path.insert(0, _here)                   # marker, not by counting depth
from app.llm import _llm_chat                                       # noqa: E402
from app.coach import (coach_feedback, coach_system, COACH_OPTS,    # noqa: E402
                       is_clean_verdict)

CASES = [
    ("exist",     "部屋に猫があります。",          ["がいます", "猫がいる", "猫はいます"]),
    ("exist",     "駅の前に友達があります。",       ["がいます", "友達がい", "友達はいます"]),
    ("exist",     "机の上に本がいます。",          ["があります", "本がある", "本はあります"]),
    ("na-adj",    "有名の店に行きました。",         ["有名な"]),
    ("na-adj",    "きれいの部屋ですね。",          ["きれいな", "綺麗な"]),
    ("i-adj-neg", "この店は高いじゃないです。",      ["高くない"]),
    ("i-adj-neg", "今日は寒いじゃなかったです。",     ["寒くなかった"]),
    ("adverb",    "もっと早い歩いてください。",      ["早く"]),
    ("adverb",    "字を大きい書いてください。",      ["大きく"]),
    ("time-ni",   "先週に京都へ行きました。",       ['先週京都', '先週"', "先週、", "先週へ"]),
    ("time-ni",   "毎日に日本語を勉強します。",      ['毎日日本語', '毎日"', "毎日、", "毎日勉強"]),
    ("de-exist",  "教室で学生がいます。",          ["教室に"]),
    # Controls: classes an existing net already handles. They must stay at
    # full marks — a control losing its correction means the harness never
    # reached the coach, and the recall number above it would mean nothing.
    ("CONTROL",   "暗いので、部屋の電気をつきました。", ["つけました"]),
    ("CONTROL",   "昨日、駅で友達を会いました。",     ["友達に", "友達と"]),
]

# The other half of the ledger. Deliberately NOT taken from coach_cases.json —
# a fixture quoted in a prompt stops being a test — and deliberately carrying
# the correct twin of each probe class, because that is where a net for the
# class above would misfire if it is going to.
CLEAN = [
    "有名な店に行きました。",
    "この店は高くないです。",
    "机の上に本があります。",
    "公園に子供がいます。",
    "三時に友達と会います。",
    "毎日日本語を勉強します。",
    "教室に学生がいます。",
    "駅で友達を待っています。",
    "昨日は寒くなかったです。",
    # Short replies. OPEN-39's clean arm had none, and that is exactly the
    # shape the rejected second-opinion design broke.
    "はい、お願いします。",
    "いいえ、結構です。",
    "すみません、もう一度お願いします。",
]

# No coach prompt, no leniency bias, no format. Just: is this sentence right?
# The answer decides whether a prompt lever can exist at all for these classes.
PLAIN_SYS = (
    'あなたは日本語の先生です。学習者が書いた文を読み、文法的に正しいかどうかを'
    '判定してください。正しければ最初に「正しい」とだけ書いてください。'
    '間違っていれば最初に「間違い」と書き、そのあとに正しい文を一つだけ書いて'
    'ください。説明は一文までにしてください。'
)

ITERS = int(os.environ.get('ITERS', '5'))
SLICE = int(os.environ.get('SLICE', '0'))
MODE = os.environ.get('MODE', 'coach')
OUT = sys.argv[1] if len(sys.argv) > 1 else '/dev/null'

done = json.load(open(OUT)) if os.path.exists(OUT) else {}
fresh = 0


def _save():
    json.dump(done, open(OUT, 'w'), indent=1, ensure_ascii=False)


def _budget_spent():
    """True once this slice has computed its quota of NEW cases."""
    return SLICE and fresh >= SLICE


def _coach_once(text):
    raw = _llm_chat(messages=[{"role": "system", "content": coach_system("Japanese", "")},
                              {"role": "user", "content": text}],
                    options=COACH_OPTS)['message']['content']
    out = coach_feedback(raw, text, "Japanese", promote_fit=False)
    return re.split(r'⬆️\s*Level up:', out)[0]


def _plain_once(text):
    return _llm_chat(messages=[{"role": "system", "content": PLAIN_SYS},
                               {"role": "user", "content": text}],
                     options={'temperature': 0.2, 'max_tokens': 120})['message']['content']


if MODE == 'plain':
    # Does the model KNOW? Two numbers: how often it calls the sentence wrong
    # at all, and how often it also produces the right fix.
    for cls, text, wants in CASES:
        key = 'PLAIN::' + text
        if key in done:
            continue
        if _budget_spent():
            break
        called_wrong = right_fix = 0
        samples = []
        for _ in range(ITERS):
            reply = _plain_once(text).strip()
            wrong = '間違' in reply[:12] or '正しくありません' in reply
            if wrong:
                called_wrong += 1
            if wrong and any(w in reply for w in wants):
                right_fix += 1
            samples.append(reply.replace('\n', ' | ')[:100])
        done[key] = dict(cls=cls, text=text, wrong=called_wrong, fix=right_fix,
                         iters=ITERS, sample=samples[:1])
        fresh += 1
        _save()
        print(f"{called_wrong}/{ITERS} called wrong | {right_fix}/{ITERS} right fix "
              f"| [{cls}] {text}", flush=True)
        print(f"    said: {samples[0]}", flush=True)

    rows = [done[k] for k in ('PLAIN::' + t for _c, t, _w in CASES) if k in done]
    probes = [r for r in rows if r['cls'] != 'CONTROL']
    if len(probes) < len([c for c in CASES if c[0] != 'CONTROL']):
        print(f"\nINCOMPLETE — {len(probes)} of "
              f"{len([c for c in CASES if c[0] != 'CONTROL'])} probe cases done. "
              f"Re-run with the same output file to continue.")
        sys.exit(0)
    n = len(probes) * ITERS
    print(f"\nPLAIN, no coach prompt ({len(probes)} probes x {ITERS})")
    print(f"  called WRONG     : {sum(r['wrong'] for r in probes)}/{n}")
    print(f"  and fixed it     : {sum(r['fix'] for r in probes)}/{n}")
    by = {}
    for r in probes:
        a = by.setdefault(r['cls'], [0, 0, 0])
        a[0] += r['wrong']
        a[1] += r['fix']
        a[2] += ITERS
    for k in sorted(by):
        print(f"  {k:<10} wrong {by[k][0]:>2}/{by[k][2]:<2}  fix {by[k][1]:>2}/{by[k][2]:<2}")
    sys.exit(0)

for cls, text, wants in CASES:
    if text in done:
        continue
    if _budget_spent():
        break
    hit = clean = 0
    misses = []
    for _ in range(ITERS):
        fb = _coach_once(text)
        if any(w in fb for w in wants):
            hit += 1
        else:
            if is_clean_verdict(fb, "Japanese"):
                clean += 1
            misses.append(fb.replace('\n', ' | ')[:110])
    done[text] = dict(cls=cls, text=text, hit=hit, clean=clean, iters=ITERS,
                      miss=misses[:1])
    fresh += 1
    _save()
    print(f"{hit}/{ITERS} corrected | {clean} said 'nothing to fix' | [{cls}] {text}",
          flush=True)
    if misses:
        print(f"    missed as: {misses[0]}", flush=True)

for text in CLEAN:
    key = 'CLEAN::' + text
    if key in done:
        continue
    if _budget_spent():
        break
    kept = 0
    flagged = []
    for _ in range(ITERS):
        fb = _coach_once(text)
        if is_clean_verdict(fb, "Japanese"):
            kept += 1
        else:
            flagged.append(fb.replace('\n', ' | ')[:110])
    done[key] = dict(cls='CLEAN', text=text, hit=kept, clean=kept, iters=ITERS,
                     miss=flagged[:1])
    fresh += 1
    _save()
    print(f"{kept}/{ITERS} left alone | [clean] {text}", flush=True)
    if flagged:
        print(f"    over-corrected as: {flagged[0]}", flush=True)

rows = [done[t] for _c, t, _w in CASES if t in done]
clean_rows = [done['CLEAN::' + t] for t in CLEAN if 'CLEAN::' + t in done]
expected = len(CASES) + len(CLEAN)
if len(rows) + len(clean_rows) < expected:
    print(f"\nINCOMPLETE — {len(rows) + len(clean_rows)} of {expected} cases done. "
          f"Re-run with the same output file to continue. No score is printed "
          f"for a partial run, because a partial score is not a score.")
    sys.exit(0)

probes = [r for r in rows if r['cls'] != 'CONTROL']
ctrl = [r for r in rows if r['cls'] == 'CONTROL']
clean_kept = sum(r['hit'] for r in clean_rows)
print(f"\nRECALL ({len(probes)} probes) : {sum(r['hit'] for r in probes)}"
      f"/{len(probes) * ITERS}")
print(f"  said 'nothing to fix': {sum(r['clean'] for r in probes)}/{len(probes) * ITERS}")
print(f"controls              : {sum(r['hit'] for r in ctrl)}/{len(ctrl) * ITERS}")
print(f"CLEAN left alone      : {clean_kept}/{len(CLEAN) * ITERS}")

by = {}
for r in probes:
    a = by.setdefault(r['cls'], [0, 0])
    a[0] += r['hit']
    a[1] += ITERS
for k in sorted(by):
    print(f"  {k:<10} {by[k][0]:>2}/{by[k][1]:<2}")

if sum(r['hit'] for r in ctrl) < len(ctrl) * ITERS:
    print("\n❌ a control lost its correction — the probe or the coach is "
          "broken, and either way the recall number above means nothing.")
    sys.exit(1)
if clean_kept < len(CLEAN) * ITERS:
    # Recall is trivially raised by correcting everything, so this fails the
    # suite outright rather than being traded against the headline.
    print(f"\n❌ over-correction: {len(CLEAN) * ITERS - clean_kept} clean "
          f"sentence(s) were 'corrected'. A recall gain bought with these is "
          f"not a gain.")
    sys.exit(1)

score = 100.0 * sum(r['hit'] for r in probes) / (len(probes) * ITERS)
print(f"\nFinal Recall Score: {score:.1f}% "
      f"({sum(r['hit'] for r in probes)}/{len(probes) * ITERS})")
