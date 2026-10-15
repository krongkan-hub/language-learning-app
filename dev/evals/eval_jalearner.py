"""Does the coach correct Japanese errors that NO net was written against?

Issue #40. `eval_jarecall.py` scores 100%, but its probes and the nets were
written together, so it mostly measures the nets. This suite is the held-out
half: eighteen error classes a Thai/English-speaking beginner-intermediate
learner makes in shops, hospitals, school and travel, none of which any net
targeted when the fixtures were written (dev/fixtures/ja_learner_cases.json).

The fixtures carry a dev/test split per class. A prompt change or a net may be
designed against the `dev` rows; the `test` rows are only ever scored. The
gated number is TEST recall — the KPI is recall on errors the fixes were not
written against, and the dev rows stop being that the moment a net reads them.

Read WITH the clean arm, never alone: 72 correct sentences in the same styles,
casual ones included, carrying the correct twin of every class plus the
look-alikes a net for that class would misfire on (弟にも, 「行きます」と言い
ました, ご予約いただきました, おいしいね、これ). A clean sentence "corrected"
is the worst failure in this project, so its count is gated on its own
(`max_clean_flagged` in eval_baselines.json) rather than traded against recall.

A probe scores only when an accepted fix appears on a ✅ side of a Feedback
bullet: quoting the learner back, or a Level up suggestion, is not a
correction the learner is drilled on. Every turn goes through `call_coach`, the
path a real turn takes, with no situation line.

Usage:
    python3 dev/evals/eval_jalearner.py out.json          # full run, resumable
    SLICE=10 python3 dev/evals/eval_jalearner.py out.json # 10 new cases, then exit
    ITERS=1 python3 dev/evals/eval_jalearner.py out.json
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.coach import is_clean_verdict                              # noqa: E402
from app.coach.pipeline import call_coach                           # noqa: E402
from app.coach.verdict import _CORRECTION_BULLET                    # noqa: E402
from fhalf import format_f_half                                     # noqa: E402

FIXTURES = os.path.join(_here, 'dev', 'fixtures', 'ja_learner_cases.json')
DATA = json.load(open(FIXTURES, encoding='utf-8'))
ERRORS, CONTROLS, CLEAN = DATA['errors'], DATA['controls'], DATA['clean']

for _case in ERRORS + CONTROLS:
    # The coach quotes the learner back; a want inside the input would score
    # that quote as a correction.
    assert not any(w in _case['input'] for w in _case['want']), _case

ITERS = int(os.environ.get('ITERS', '2'))
SLICE = int(os.environ.get('SLICE', '0'))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/dev/null'

done = json.load(open(OUT)) if os.path.isfile(OUT) else {}   # not /dev/null
fresh = 0


def _save():
    json.dump(done, open(OUT, 'w'), indent=1, ensure_ascii=False)


def _feedback(text):
    """The Feedback part of what the learner sees; Level up is never drilled."""
    return re.split(r'⬆️?\s*Level up:', call_coach(text, 'Japanese'))[0]


def _fixed(feedback, wants):
    return any(w in right for _said, right in _CORRECTION_BULLET.findall(feedback)
               for w in wants)


for case in ERRORS + CONTROLS:
    text = case['input']
    if text in done:
        continue
    if SLICE and fresh >= SLICE:
        break
    hit = clean = 0
    misses = []
    for _ in range(ITERS):
        fb = _feedback(text)
        if _fixed(fb, case['want']):
            hit += 1
            continue
        if is_clean_verdict(fb, 'Japanese'):
            clean += 1
        misses.append(fb.replace('\n', ' | ')[:120])
    done[text] = dict(cls=case['cls'], split=case.get('split', 'control'),
                      hit=hit, clean=clean, iters=ITERS, miss=misses[:1])
    fresh += 1
    _save()
    print(f"{hit}/{ITERS} fixed | {clean} called clean | "
          f"[{case['cls']}/{case.get('split', 'control')}] {text}", flush=True)
    if misses:
        print(f"    missed as: {misses[0]}", flush=True)

for text in CLEAN:
    key = 'CLEAN::' + text
    if key in done:
        continue
    if SLICE and fresh >= SLICE:
        break
    kept = 0
    flagged = []
    for _ in range(ITERS):
        fb = _feedback(text)
        if is_clean_verdict(fb, 'Japanese'):
            kept += 1
        else:
            flagged.append(fb.replace('\n', ' | ')[:120])
    done[key] = dict(cls='CLEAN', kept=kept, iters=ITERS, flagged=flagged[:1])
    fresh += 1
    _save()
    print(f"{kept}/{ITERS} left alone | [clean] {text}", flush=True)
    if flagged:
        print(f"    over-corrected as: {flagged[0]}", flush=True)

expected = len(ERRORS) + len(CONTROLS) + len(CLEAN)
have = sum(1 for c in ERRORS + CONTROLS if c['input'] in done) + \
    sum(1 for t in CLEAN if 'CLEAN::' + t in done)
if have < expected:
    print(f"\nINCOMPLETE — {have} of {expected} cases done. Re-run with the same "
          f"output file to continue. A partial score is not a score.")
    sys.exit(0)

rows = [done[c['input']] for c in ERRORS]
ctrl = [done[c['input']] for c in CONTROLS]
clean_rows = [done['CLEAN::' + t] for t in CLEAN]


def _recall(subset):
    hit = sum(r['hit'] for r in subset)
    return hit, sum(r['iters'] for r in subset)


clean_n = sum(r['iters'] for r in clean_rows)
clean_kept = sum(r['kept'] for r in clean_rows)
flagged = clean_n - clean_kept
for label, split in (('dev', 'dev'), ('TEST', 'test')):
    h, n = _recall([r for r in rows if r['split'] == split])
    print(f"RECALL {label:<4} : {h}/{n} ({100.0 * h / n:.1f}%)")
h_all, n_all = _recall(rows)
print(f"RECALL all  : {h_all}/{n_all} ({100.0 * h_all / n_all:.1f}%)")
print(f"  called clean: {sum(r['clean'] for r in rows)}/{n_all}")
print(f"controls    : {sum(r['hit'] for r in ctrl)}/{sum(r['iters'] for r in ctrl)}")
print(f"CLEAN left alone: {clean_kept}/{clean_n}")
print(f"CLEAN flagged: {flagged}")

by = {}
for r in rows:
    a = by.setdefault(r['cls'], [0, 0, 0, 0])
    i = 0 if r['split'] == 'dev' else 2
    a[i] += r['hit']
    a[i + 1] += r['iters']
print("\n  class            dev    test")
for k in sorted(by):
    a = by[k]
    print(f"  {k:<15} {a[0]:>2}/{a[1]:<2}  {a[2]:>2}/{a[3]:<2}")

print("\n" + format_f_half(tp=h_all, fn=n_all - h_all, fp=flagged))

if sum(r['hit'] for r in ctrl) < sum(r['iters'] for r in ctrl):
    print("\n❌ a control lost its correction — the harness never reached the "
          "nets, and the recall above means nothing.")
    sys.exit(1)

h_test, n_test = _recall([r for r in rows if r['split'] == 'test'])
print(f"\nFinal Recall Score: {100.0 * h_test / n_test:.1f}% ({h_test}/{n_test})")
