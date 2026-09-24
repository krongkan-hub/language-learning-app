"""Does the judge treat its OWN wording more kindly than a learner's? OPEN-?? probe.

The judge is the same 7B that writes the NPC's turns. Published work on
LLM-as-judge finds two biases that matter here: judges favour text produced by
models (self-preference, and it grows with how capable the writer is), and
small judges run lenient — this project measured its own version of that when
a 1.5B judge said YES to 24 of 24 (`project_llm_judge_model_tradeoff`).

The design keeps MEANING fixed and changes only AUTHORSHIP:

    original    the learner's reply from dev/fixtures/judge_cases.json, with
                the human's expect_done label
    paraphrase  the same reply, reworded by the 7B with an explicit
                instruction not to add or drop any information

Both are judged against the same done_when. If the verdict changes, the judge
is responding to wording rather than to whether the task was done — and the
DIRECTION says which way. A paraphrase passing where the original failed is
the self-preference shape.

WHAT THIS CANNOT DO, stated plainly: a paraphrase can quietly drop the very
thing the task asked for, which would flip the verdict for an honest reason.
So every flipped pair is printed in full at the end, and the number means
nothing until someone reads them. Vocabulary cases, where done_when names an
exact word, are excluded — a paraphrase that replaces that word SHOULD fail.

Run it after the eval gates, never beside them: one 7B at a time.

    python3 dev/tools/probe_judge_authorship.py out.json
    ITERS=3 python3 dev/tools/probe_judge_authorship.py out.json
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
from app.judge import evaluate_task                                 # noqa: E402
from app.llm import _llm_chat                                       # noqa: E402

CASES = json.load(open(os.path.join(_here, 'dev/fixtures/judge_cases.json')))

ITERS = int(os.environ.get('ITERS', '3'))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/dev/null'

PARAPHRASE_SYS = (
    'Reword the sentence below. Keep EVERY piece of information it contains — '
    'every number, name, request and detail — and add nothing that is not '
    'already there. Write ONLY the reworded sentence, in the same language, '
    'with no commentary.'
)


def _paraphrase(text):
    reply = _llm_chat(messages=[{'role': 'system', 'content': PARAPHRASE_SYS},
                                {'role': 'user', 'content': text}],
                      options={'temperature': 0.3, 'max_tokens': 120})
    return reply['message']['content'].strip().split('\n')[0].strip(' "「」')


def _verdict(text, case):
    done, _hint = evaluate_task(text, case['done_when'], [], case['language'], None)
    return bool(done)


def main():
    # A done_when that names an exact word is excluded: a paraphrase that
    # replaces the word should fail, and that is not bias.
    cases = [c for c in CASES if 'used the word' not in c['done_when'].lower()]
    print(f'{len(cases)} of {len(CASES)} cases (vocabulary ones excluded), '
          f'{ITERS} iteration(s)\n', flush=True)
    done = json.load(open(OUT)) if os.path.isfile(OUT) else {}

    for case in cases:
        key = case['name']
        if key in done:
            continue
        para = _paraphrase(case['input'])
        orig_pass = sum(_verdict(case['input'], case) for _ in range(ITERS))
        para_pass = sum(_verdict(para, case) for _ in range(ITERS))
        done[key] = dict(name=key, expect=bool(case['expect_done']),
                         original=case['input'], paraphrase=para,
                         orig_pass=orig_pass, para_pass=para_pass, iters=ITERS)
        json.dump(done, open(OUT, 'w'), indent=1, ensure_ascii=False)
        flag = '  <- verdict moved' if orig_pass != para_pass else ''
        print(f'orig {orig_pass}/{ITERS}  para {para_pass}/{ITERS}{flag} | {key}',
              flush=True)

    rows = [done[c['name']] for c in cases if c['name'] in done]
    if len(rows) < len(cases):
        print(f'\nINCOMPLETE — {len(rows)} of {len(cases)}. Re-run to continue.')
        return 0

    n = len(rows) * ITERS
    orig = sum(r['orig_pass'] for r in rows)
    para = sum(r['para_pass'] for r in rows)
    print(f'\npassed as written by the LEARNER : {orig}/{n}')
    print(f'passed as reworded by the MODEL  : {para}/{n}')
    print(f'difference                       : {para - orig:+d}')

    moved = [r for r in rows if r['orig_pass'] != r['para_pass']]
    print(f'\ncases whose verdict moved: {len(moved)} of {len(rows)} — read '
          f'every one before believing the number above:')
    for r in moved:
        print(f"\n  [{r['name']}] human label: "
              f"{'done' if r['expect'] else 'not done'}")
        print(f"    learner : {r['original']}")
        print(f"    model   : {r['paraphrase']}")
        print(f"    {r['orig_pass']}/{ITERS} -> {r['para_pass']}/{ITERS}")
    if not moved:
        print('  none — the judge read the task, not the wording.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
