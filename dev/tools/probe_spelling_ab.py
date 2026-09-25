"""A/B: the coach on JFLEG with and without the English spelling net. OPEN-50.

probe_jfleg.py measured before and after the net in two separate runs, so its
18/40 -> 22/40 mixes the net's effect with the model's own run-to-run noise
(eval_baselines.json records unchanged code moving 10 points). This removes
the noise instead of averaging over it: every model reply is generated ONCE
and cached, then the same replies are passed through the pipeline twice —
control with apply_spelling_net replaced by the identity, treatment as
shipped. The arms differ in the net and nothing else, so every discordant
pair is the net's doing, which is exactly what an exact McNemar test wants.

    ERROR arm  all four annotators edited the sentence -> flagged is right
    CLEAN arm  all four left it alone                  -> flagged is an FP

Writes one JSON per arm in the shape dev/tools/ab_report.py reads:

    python3 dev/tools/probe_spelling_ab.py out_prefix
    python3 dev/tools/ab_report.py out_prefix.error.json --field flagged
    python3 dev/tools/ab_report.py out_prefix.clean.json --field flagged

JFLEG is CC BY-NC-SA 4.0 and is fetched at run time, never vendored. One 7B
at a time: run it on its own.
"""
import json
import os
import random
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(_here, 'dev', 'tools'))
import app.coach.pipeline as pipeline                                # noqa: E402
from app.coach import is_clean_verdict                              # noqa: E402
from probe_spelling_jfleg import _lines                             # noqa: E402

N_ERROR = int(os.environ.get('N', '160'))
SEED = int(os.environ.get('SEED', '42'))


def _arms():
    src = _lines('test', 'test.src')
    refs = [_lines('test', f'test.ref{i}') for i in range(4)]
    error, clean = [], []
    for i, s in enumerate(src):
        if not s.strip():
            continue
        same = [r[i].strip() == s.strip() for r in refs]
        if not any(same):
            error.append(s.strip())
        elif all(same):
            clean.append(s.strip())
    random.Random(SEED).shuffle(error)
    return error[:N_ERROR], clean


def main(prefix: str) -> None:
    cache = {}
    real_chat, real_net = pipeline._llm_chat, pipeline.apply_spelling_net

    def cached_chat(messages, **kw):
        key = json.dumps(messages, ensure_ascii=False)
        if key not in cache:
            cache[key] = real_chat(messages=messages, **kw)
        return cache[key]

    pipeline._llm_chat = cached_chat
    error, clean = _arms()
    print(f'JFLEG test: {len(error)} error, {len(clean)} clean', flush=True)
    for arm, sentences in (('error', error), ('clean', clean)):
        rows = {}
        for n, text in enumerate(sentences, 1):
            pipeline.apply_spelling_net = lambda fb, *_a, **_k: fb
            control = pipeline.call_coach(text, 'English')
            pipeline.apply_spelling_net = real_net
            treatment = pipeline.call_coach(text, 'English')
            c = not is_clean_verdict(control, 'English')
            t = not is_clean_verdict(treatment, 'English')
            rows[text] = {'control': [{'flagged': c}], 'treatment': [{'flagged': t}],
                          'treatment_text': treatment}
            mark = '  <- net' if c != t else ''
            print(f'[{arm} {n}/{len(sentences)}] {int(c)}{int(t)}{mark} | {text[:70]}',
                  flush=True)
        with open(f'{prefix}.{arm}.json', 'w') as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        cf = sum(r['control'][0]['flagged'] for r in rows.values())
        tf = sum(r['treatment'][0]['flagged'] for r in rows.values())
        print(f'{arm.upper()} arm flagged: control {cf}/{len(rows)}, '
              f'treatment {tf}/{len(rows)}', flush=True)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/tmp/spelling_ab')
