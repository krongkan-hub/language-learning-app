"""The coach against sentences THIS PROJECT DID NOT WRITE. JFLEG, English.

Every fixture in dev/fixtures was written here, which means every number this
project reports is the coach measured against errors we thought of. JFLEG is
1,501 sentences written by real English learners, each corrected by four
native annotators independently (Napoles et al., EACL 2017). It is the
standard fluency benchmark for grammatical error correction.

WHAT THIS MEASURES, and what it does not. JFLEG is normally scored with GLEU
over a system's rewritten sentence; our coach does not rewrite a sentence, it
emits feedback bullets. So this scores the decision ONE STEP EARLIER, which is
the decision the learner actually feels:

    ERROR arm   all four annotators edited the sentence  -> the coach should
                say something.  Flagged = TP, silent = FN.
    CLEAN arm   all four left it exactly as written      -> the coach should
                stay silent.    Flagged = FP.

Sentences the annotators disagreed about (some edited, some did not) are
DROPPED, deliberately: if four natives cannot agree the sentence needs work,
neither arm can fairly count it. That is the cheap way to get an unarguable
ruler out of a corpus built for a different metric.

Reported as F0.5, the GEC field's metric — see dev/evals/fhalf.py.

DATA IS NOT VENDORED. JFLEG is CC BY-NC-SA 4.0, so this downloads it to a
scratch directory at run time and nothing enters the repository. Personal,
non-commercial use only.

    python3 dev/tools/probe_jfleg.py out.json
    N=40 ITERS=1 python3 dev/tools/probe_jfleg.py out.json

Run it AFTER the eval gates, never beside them: one 7B at a time.
"""
import json
import os
import random
import sys
import urllib.request

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(_here, 'dev', 'evals'))
from app.coach import is_clean_verdict                              # noqa: E402
from app.coach.pipeline import call_coach                           # noqa: E402
from fhalf import format_f_half                                     # noqa: E402

BASE = 'https://raw.githubusercontent.com/keisks/jfleg/master/test/'
FILES = ['test.src'] + [f'test.ref{i}' for i in range(4)]
CACHE = os.environ.get('JFLEG_DIR', '/tmp/jfleg')

N = int(os.environ.get('N', '60'))          # sentences per arm
ITERS = int(os.environ.get('ITERS', '1'))
SEED = int(os.environ.get('SEED', '42'))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/dev/null'


def _fetch():
    """Download the four references and the source once, into CACHE."""
    os.makedirs(CACHE, exist_ok=True)
    for name in FILES:
        path = os.path.join(CACHE, name)
        if not os.path.exists(path):
            print(f'downloading {name} ...', flush=True)
            urllib.request.urlretrieve(BASE + name, path)
    return [open(os.path.join(CACHE, n), encoding='utf-8').read().splitlines()
            for n in FILES]


def _arms():
    """(error, clean) sentence lists, by unanimous annotator agreement."""
    src, *refs = _fetch()
    error, clean = [], []
    for i, s in enumerate(src):
        s = s.strip()
        if not s or len(s.split()) < 4:
            continue
        votes = [r[i].strip() != s for r in refs]
        if all(votes):
            error.append(s)
        elif not any(votes):
            clean.append(s)
    random.Random(SEED).shuffle(error)
    random.Random(SEED).shuffle(clean)
    return error[:N], clean[:N]


def _flagged(text):
    """True when the coach says something about this sentence."""
    return not is_clean_verdict(call_coach(text, 'English'), 'English')


def main():
    error, clean = _arms()
    print(f'JFLEG test: {len(error)} unanimous-error, {len(clean)} '
          f'unanimous-clean sentences, {ITERS} iteration(s)\n', flush=True)
    done = json.load(open(OUT)) if os.path.isfile(OUT) else {}

    for arm, sentences in (('ERROR', error), ('CLEAN', clean)):
        for text in sentences:
            key = f'{arm}::{text}'
            if key in done:
                continue
            hits = sum(_flagged(text) for _ in range(ITERS))
            done[key] = dict(arm=arm, text=text, flagged=hits, iters=ITERS)
            json.dump(done, open(OUT, 'w'), indent=1)
            mark = ('flagged' if hits else 'silent')
            wrong = (arm == 'ERROR' and not hits) or (arm == 'CLEAN' and hits)
            print(f"{hits}/{ITERS} {mark:<8}{'  <- wrong' if wrong else ''} "
                  f"| [{arm}] {text[:70]}", flush=True)

    rows = [done[f'{a}::{t}'] for a, ts in (('ERROR', error), ('CLEAN', clean))
            for t in ts if f'{a}::{t}' in done]
    if len(rows) < len(error) + len(clean):
        print(f'\nINCOMPLETE — {len(rows)} of {len(error) + len(clean)}. '
              f'Re-run with the same output file to continue.')
        return 0

    tp = sum(r['flagged'] for r in rows if r['arm'] == 'ERROR')
    fn = len(error) * ITERS - tp
    fp = sum(r['flagged'] for r in rows if r['arm'] == 'CLEAN')
    print(f'\nERROR arm flagged : {tp}/{len(error) * ITERS}')
    print(f'CLEAN arm flagged : {fp}/{len(clean) * ITERS}   (these are the '
          f'over-corrections)')
    print('\n' + format_f_half(tp=tp, fn=fn, fp=fp))
    print('\nFor comparison, the in-house fixtures are written here and the '
          'coach scores far higher on them. The gap is the number worth '
          'knowing.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
