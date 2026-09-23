"""Is a WRONG Japanese objective less stable than a right one? OPEN-42 probe.

Both detectors OPEN-42 rejected asked the 7B to judge its own output, and it
cannot: it wrote 治療 for a hair treatment and does not know it is wrong. This
asks nothing. It translates the same English line K times and measures whether
the answers agree with each other — a guess should wobble, a known phrase
should not. No new dependency, no larger model, no judging.

Run it AFTER the eval gates, never beside them: one 7B at a time on a 16GB
machine.

    python3 dev/tools/probe_translation_consistency.py out.json     # all 80
    K=3 LIMIT=20 python3 dev/tools/probe_translation_consistency.py out.json

What it prints is the only thing that matters: the agreement rate for the
lines a native reviewer called fine against the rate for the ones called
false. If those two numbers are the same, this design is dead too and the row
should say so — which is worth as much as a detector, since OPEN-42 exists to
stop the next person re-measuring what has already failed.

NOTE ON FAIRNESS: the fixture's `ja` came from a BATCH call (translate_hints
sends every line of a scenario at once), and this probe translates one line
alone, so the two distributions are not identical. It is the agreement
BETWEEN this probe's own K samples that is being measured, never agreement
with the fixture, so the comparison stays internal.
"""
import json
import os
import re
import sys
from collections import Counter

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
from app.llm import client                                          # noqa: E402
from app.llm.translate import TRANSLATE_OPTS                        # noqa: E402

CASES = json.load(open(os.path.join(_here, 'dev/fixtures/ja_translation_cases.json')))

K = int(os.environ.get('K', '3'))
LIMIT = int(os.environ.get('LIMIT', '0'))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/dev/null'

# Kana carry the grammar; the kanji runs carry the meaning that OPEN-42's
# wrong-meaning class gets wrong (治療 vs トリートメント), so agreement is
# measured on those rather than on the whole string, which would call two
# identical meanings different over a ます/ましょう ending.
_KANJI_RUN = re.compile(r'[一-鿿]+|[゠-ヿー]{2,}')


def _content(text):
    return frozenset(_KANJI_RUN.findall(text))


def _translate_once(english):
    prompt = (f'Translate the instruction below into Japanese. Write ONLY the '
              f'translation, no commentary.\n\n{english}')
    reply = client._llm_chat(messages=[{'role': 'user', 'content': prompt}],
                             options=TRANSLATE_OPTS)['message']['content']
    return reply.strip().split('\n')[0].strip()


def main():
    done = json.load(open(OUT)) if os.path.isfile(OUT) else {}
    cases = CASES[:LIMIT] if LIMIT else CASES

    for case in cases:
        key = case['en']
        if key in done:
            continue
        samples = [_translate_once(case['en']) for _ in range(K)]
        sets = [_content(s) for s in samples]
        # Agreement = how often the most common content-word set repeats.
        top = Counter(sets).most_common(1)[0][1]
        done[key] = dict(label=case['label'], en=case['en'], ja=case['ja'],
                         samples=samples, agree=top / K)
        json.dump(done, open(OUT, 'w'), indent=1, ensure_ascii=False)
        print(f"agree {top}/{K} | [{case['label']}] {case['en'][:50]}", flush=True)
        if top < K:
            for s in samples:
                print(f"    {s[:70]}", flush=True)

    rows = [done[c['en']] for c in cases if c['en'] in done]
    if len(rows) < len(cases):
        print(f"\nINCOMPLETE — {len(rows)} of {len(cases)}. Re-run to continue.")
        return 0

    print(f"\nagreement over K={K}, by the reviewer's label:")
    by = {}
    for r in rows:
        by.setdefault(r['label'], []).append(r['agree'])
    for label in sorted(by):
        vals = by[label]
        full = sum(1 for v in vals if v == 1.0)
        print(f"  {label:<10} n={len(vals):<3} mean {sum(vals) / len(vals):.2f}  "
              f"unanimous {full}/{len(vals)}")

    fine = by.get('fine', [])
    false = by.get('false', [])
    if fine and false:
        gap = sum(fine) / len(fine) - sum(false) / len(false)
        print(f"\nfine - false = {gap:+.2f} mean agreement")
        print("A gap near 0.00 means instability does not see these errors "
              "either, and OPEN-42 should record this design as rejected.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
