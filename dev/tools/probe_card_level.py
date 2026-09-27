"""A/B: does telling the actor to skip everyday words give more usable cards?

vocab_card._is_everyday_word now hides a card whose word is among the
commonest in English (session, machine, application): 10 of 23 real cards.
A hidden card leaves that turn with none, so the question is whether the
prompt can steer the model to a harder word in the first place — without
costing what OPEN-19 and OPEN-21 measured prompt bulk to cost: the card
itself.

Raw first generation, no retry, like eval_rawactor.py; control is the prompt
as shipped, treatment adds TREATMENT_RULE. Per turn:

    card      a vocabulary block is present at all
    everyday  that card's word is one the filter hides
    shown     card present AND not everyday — what the learner actually gets
    valid     validate() passes

    python3 dev/tools/probe_card_level.py out.json
    python3 dev/tools/ab_report.py out.json --field shown

English only (the filter is English-only). One 7B at a time.
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
from app.llm import ACTOR_OPTS, _llm_chat, sanitize, validate            # noqa: E402
from app.llm.vocab import match_vocab_fields                            # noqa: E402
from app.scenarios.builtins import SCENARIOS                            # noqa: E402
from app.session import (ACTOR_MAX_SENTENCES, GREETING_MAX_SENTENCES,   # noqa: E402
                         build_actor_system_prompt, build_greeting_system_prompt)
from app.vocab_card import _is_everyday_word                            # noqa: E402

N = int(os.environ.get('N', '20'))
ITERS = int(os.environ.get('ITERS', '2'))
SEED = int(os.environ.get('SEED', '7'))

ANCHOR = 'The word MUST be reusable vocabulary'
TREATMENT_RULE = ('Never pick an everyday word a fluent adult already knows — words like '
                  'special, machine, session, check, cover or application teach nothing.\n')

OPENER = 'Hello!'
PRIOR_NPC = "Of course, let me take a look at that for you."
LEARNER = "Thanks. That sounds good."


def with_rule(prompt: str) -> str:
    assert ANCHOR in prompt, 'anchor moved; update the probe'
    return prompt.replace(ANCHOR, TREATMENT_RULE + ANCHOR, 1)


def score(text: str, cap: int) -> dict:
    m = match_vocab_fields(text)
    word = m.group(1).strip() if m else ''
    everyday = bool(word) and _is_everyday_word(word, 'English')
    ok, reason = validate(text, max_sentences=cap, language='English')
    return {'card': bool(word), 'everyday': everyday, 'shown': bool(word) and not everyday,
            'valid': ok, 'reason': reason, 'word': word}


def main(out: str) -> None:
    pool = [s for s in SCENARIOS if s.tasks]
    random.Random(SEED).shuffle(pool)
    done = json.load(open(out)) if os.path.isfile(out) else {}   # not /dev/null
    for scenario in pool[:N]:
        task = scenario.tasks[0]
        for kind in ('greeting', 'mid'):
            name = f'{scenario.name}|{kind}'
            if name in done:
                continue
            if kind == 'greeting':
                system = build_greeting_system_prompt(scenario, task, language='English')
                messages = [{'role': 'user', 'content': OPENER}]
                cap = GREETING_MAX_SENTENCES
            else:
                system = build_actor_system_prompt(scenario, task, language='English')
                messages = [{'role': 'user', 'content': OPENER},
                            {'role': 'assistant', 'content': PRIOR_NPC},
                            {'role': 'user', 'content': LEARNER}]
                cap = ACTOR_MAX_SENTENCES
            row = {}
            for arm, prompt in (('control', system), ('treatment', with_rule(system))):
                row[arm] = []
                for _ in range(ITERS):
                    raw = _llm_chat(messages=[{'role': 'system', 'content': prompt}] + messages,
                                    options=ACTOR_OPTS, cache_key=None)['message']['content']
                    row[arm].append(score(sanitize(raw, speaker=scenario.speaker), cap))
            done[name] = row
            words = lambda arm: ','.join(t['word'] or '-' for t in row[arm])
            print(f'{name[:40]:40} control [{words("control")}]  treatment [{words("treatment")}]',
                  flush=True)
            with open(out, 'w') as f:
                json.dump(done, f, ensure_ascii=False, indent=1)
    for field in ('card', 'everyday', 'shown', 'valid'):
        for arm in ('control', 'treatment'):
            turns = [t for r in done.values() for t in r[arm]]
            print(f'{field:9} {arm:9} {sum(t[field] for t in turns)}/{len(turns)}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/dev/null')
