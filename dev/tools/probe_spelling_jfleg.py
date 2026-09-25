"""The English spelling net against JFLEG, with no model loaded. OPEN-50.

probe_jfleg.py asks whether the COACH speaks up; this asks the narrower,
deterministic question the spelling net has to answer on its own: when it
fires, is its correction the one a native annotator made? It runs in seconds,
so it is the loop the net was tuned in (on dev) and checked against (on test).

    GOOD   the corrected word appears in at least one of the four references
           and the misspelling does not — that annotator made this fix.
    BAD    otherwise. Strict: "sientist" -> "scientist" counts as BAD when the
           annotator wrote "scientists", and "palce" -> "place" does when they
           rephrased to "location". Read the BAD list before trusting the rate.
    CLEAN  sentences all four annotators left untouched. Any fire here is a
           false positive nobody can argue with.

DATA IS NOT VENDORED (CC BY-NC-SA 4.0); it is fetched to a scratch directory,
same as probe_jfleg.py.

    python3 dev/tools/probe_spelling_jfleg.py dev
    python3 dev/tools/probe_spelling_jfleg.py test -v
"""
import os
import re
import sys
import urllib.request

_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
from app.coach.nets.spelling import spelling_corrections             # noqa: E402

BASE = 'https://raw.githubusercontent.com/keisks/jfleg/master/'
CACHE = os.environ.get('JFLEG_DIR', '/tmp/jfleg')


def _lines(split: str, name: str) -> list:
    path = os.path.join(CACHE, split, name)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(f'{BASE}{split}/{name}', path)
    with open(path, encoding='utf-8') as f:
        return f.read().split('\n')


def _words(s: str) -> set:
    # JFLEG is tokenized: "do n't". Rejoin so "don't" can be matched.
    return set(re.findall(r"[a-z']+", s.lower().replace(" n't", "n't")))


def main(split: str, verbose: bool) -> None:
    src = _lines(split, f'{split}.src')
    refs = [_lines(split, f'{split}.ref{i}') for i in range(4)]
    good, bad, clean_fires, clean_n = 0, [], 0, 0
    for i, sentence in enumerate(src):
        if not sentence.strip():
            continue
        rs = [r[i] for r in refs]
        unanimous_clean = all(r.strip() == sentence.strip() for r in rs)
        clean_n += unanimous_clean
        for was, now in spelling_corrections(sentence):
            clean_fires += unanimous_clean
            fixed = set(re.findall(r"[a-z']+", now.lower()))
            if any(fixed <= _words(r) and was.lower() not in _words(r) for r in rs):
                good += 1
            else:
                bad.append((was, now, rs[0].strip()))
    fires = good + len(bad)
    print(f'{split}: fires={fires} good={good} bad={len(bad)} '
          f'strict precision={good / max(fires, 1):.1%} | '
          f'fires on {clean_n} unanimous-clean sentences: {clean_fires}')
    if verbose:
        for was, now, ref in bad:
            print(f'  BAD  {was!r} -> {now!r}   ref: {ref[:90]}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'dev', '-v' in sys.argv)
