"""Do the coach's Japanese particle corrections explain the particle?

No eval reads a Japanese reason — eval_coachreason is English-only — and one
played session showed ❌ "駅に行くのバス" → ✅ "駅に行くバス" explained as
(バス前を省略します). This counts, over the Japanese error inputs the suites
already carry (eval_jarecall.CASES and coach_cases.json), how often a
one-particle correction comes with a reason that never names the particle,
and prints every such reason so a person can read them.

Paired like probe_spelling_ab: each model reply is generated once and cached,
then the pipeline runs with explain_particle_changes disabled (control) and
enabled (treatment) over the same text.

    python3 dev/tools/probe_ja_reasons.py out.json
"""
import json
import os
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
import app.coach.pipeline as pipeline                                # noqa: E402
from app.coach.reasons import _BULLET, _names, particle_change      # noqa: E402

ITERS = int(os.environ.get('ITERS', '3'))


def _inputs():
    src = open(os.path.join(_here, 'dev', 'evals', 'eval_jarecall.py'), encoding='utf-8').read()
    ns = {}
    exec(src[src.index('CASES = ['):src.index(']\n', src.index('CASES = [')) + 2], ns)
    out = [text for _, text, _ in ns['CASES']]
    cases = json.load(open(os.path.join(_here, 'dev', 'fixtures', 'coach_cases.json'),
                           encoding='utf-8'))
    out += [c['input'] for c in cases
            if c.get('language') == 'Japanese' and c.get('expect') == 'correct'
            and 'place' not in c]
    return out


def _particle_bullets(feedback: str) -> list:
    rows = []
    for line in feedback.split('\n'):
        m = _BULLET.match(line)
        change = particle_change(m.group(2), m.group(3)) if m else None
        if change:
            reason = m.group(4) or ''
            named = any(_names(reason, p) for p in change[1:] if p)
            rows.append({'said': m.group(2), 'better': m.group(3),
                         'reason': reason, 'named': named, 'change': change[0]})
    return rows


def main(out: str) -> None:
    cache = {}
    real_chat, real_explain = pipeline._llm_chat, pipeline.explain_particle_changes

    def cached_chat(messages, **kw):
        key = json.dumps(messages, ensure_ascii=False)
        if key not in cache:
            cache[key] = real_chat(messages=messages, **kw)
        return cache[key]

    pipeline._llm_chat = cached_chat
    rows = []
    inputs = _inputs()
    print(f'{len(inputs)} Japanese error inputs x {ITERS}', flush=True)
    for n, text in enumerate(inputs, 1):
        for i in range(ITERS):
            cache.clear() if i else None
            pipeline.explain_particle_changes = lambda fb, *_a: fb
            control = pipeline.call_coach(text, 'Japanese')
            pipeline.explain_particle_changes = real_explain
            treatment = pipeline.call_coach(text, 'Japanese')
            rows.append({'input': text, 'control': _particle_bullets(control),
                         'treatment': _particle_bullets(treatment)})
        print(f'[{n}/{len(inputs)}] {text}', flush=True)
        json.dump(rows, open(out, 'w'), ensure_ascii=False, indent=1)
    for arm in ('control', 'treatment'):
        bullets = [b for r in rows for b in r[arm]]
        named = sum(b['named'] for b in bullets)
        print(f'{arm:9} particle bullets {len(bullets)}, reason names the particle '
              f'{named}/{len(bullets)}')
    print('\nControl reasons that never name the particle:')
    for r in rows:
        for b in r['control']:
            if not b['named']:
                print(f'  {b["said"]} → {b["better"]}  ({b["reason"]})')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/dev/null')
