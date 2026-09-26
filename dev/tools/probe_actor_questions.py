"""A/B: does the actor end its turn with a question the learner can answer?

Playing the web front end, the canned salvage line ("What else can I do for
you?") was appended to about one turn in three. stream_actor appends it when a
turn carries no OPEN question — either the model asked none, or it asked a
yes/no one, which the rules forbid and the pipeline drops. ACTOR_SYS asks for
"something concrete to grab onto" — a choice, a wh-question, OR a topic — but
never for a question as such, so a topic alone satisfies it and leaves the
learner nothing to answer.

This measures the raw first generation, no retry or salvage, the way
eval_rawactor.py does, on control (ACTOR_SYS / GREETING_SYS as shipped) and
treatment (one added rule, TREATMENT_RULE below) over the same scenarios. Per
turn it records:

    open_q  a sentence is a question and not a closed one -> no salvage needed
    valid   validate() passes (the rule must not cost length or script)
    card    the vocabulary block is present — OPEN-21 measured that prompt
            bulk suppresses the card, so every added line has to show it
            does not

Writes the JSON dev/tools/ab_report.py reads:

    python3 dev/tools/probe_actor_questions.py out.json
    python3 dev/tools/ab_report.py out.json --field open_q
    python3 dev/tools/ab_report.py out.json --field card

One 7B at a time.
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
from app.llm import (ACTOR_OPTS, _llm_chat, is_closed_question,       # noqa: E402
                     is_question, match_vocab_block, sanitize, validate)
from app.llm.guards import split_sentences                          # noqa: E402
from app.llm.vocab import strip_vocab_block                         # noqa: E402
from app.scenarios.builtins import SCENARIOS                        # noqa: E402
from app.session import (ACTOR_MAX_SENTENCES, GREETING_MAX_SENTENCES,  # noqa: E402
                         build_actor_system_prompt, build_greeting_system_prompt)

N = int(os.environ.get('N', '24'))
ITERS = int(os.environ.get('ITERS', '2'))
SEED = int(os.environ.get('SEED', '42'))
LANGUAGES = os.environ.get('LANGS', 'English Japanese').split()

# Inserted right after the existing "something concrete" rule (actor) or the
# closed-question rule (greeting). The actor file carries the same text.
TREATMENT_RULE = ('- END your turn with exactly one question the learner can answer: '
                  'a wh-question (what, which, how, when, where) or two choices '
                  'joined by "or". A turn with no such question leaves the learner '
                  'with nothing to say.')
ANCHOR = '- NEVER ask a yes/no question in ANY sentence of your turn'

OPENER = {'English': 'Hello!', 'Japanese': 'こんにちは。'}
PRIOR_NPC = {'English': "Of course, let me take a look at that for you.",
             'Japanese': "かしこまりました。少々お待ちください。"}
LEARNER = {'English': "Thanks. That sounds good.",
           'Japanese': "ありがとうございます。いいですね。"}


def with_rule(prompt: str) -> str:
    assert ANCHOR in prompt, 'anchor moved; update the probe'
    return prompt.replace(ANCHOR, TREATMENT_RULE + '\n' + ANCHOR, 1)


def score(text: str, language: str, max_sentences: int) -> dict:
    spoken = strip_vocab_block(text)
    sentences = split_sentences(spoken)
    open_q = any(is_question(s) and not is_closed_question(s) for s in sentences)
    ok, reason = validate(text, max_sentences=max_sentences, language=language)
    return {'open_q': open_q, 'valid': ok, 'reason': reason,
            'card': bool(match_vocab_block(text)), 'text': text}


def main(out: str) -> None:
    pool = [s for s in SCENARIOS if s.tasks]
    random.Random(SEED).shuffle(pool)
    done = json.load(open(out)) if os.path.isfile(out) else {}   # not /dev/null
    for scenario in pool[:N]:
        task = scenario.tasks[0]
        for language in LANGUAGES:
            # A deliberately flat learner line ("That sounds good.") — the
            # turn after it is where an NPC most often stops asking.
            for kind in ('greeting', 'mid'):
                name = f'{scenario.name}|{language}|{kind}'
                if name in done:
                    continue
                if kind == 'greeting':
                    system = build_greeting_system_prompt(scenario, task, language=language)
                    messages = [{'role': 'user', 'content': OPENER[language]}]
                    cap = GREETING_MAX_SENTENCES
                else:
                    system = build_actor_system_prompt(scenario, task, language=language)
                    messages = [{'role': 'user', 'content': OPENER[language]},
                                {'role': 'assistant', 'content': PRIOR_NPC[language]},
                                {'role': 'user', 'content': LEARNER[language]}]
                    cap = ACTOR_MAX_SENTENCES
                row = {}
                for arm, prompt in (('control', system), ('treatment', with_rule(system))):
                    row[arm] = []
                    for _ in range(ITERS):
                        raw = _llm_chat(messages=[{'role': 'system', 'content': prompt}] + messages,
                                        options=ACTOR_OPTS, cache_key=None)['message']['content']
                        row[arm].append(score(sanitize(raw, speaker=scenario.speaker), language, cap))
                done[name] = row
                c = sum(t['open_q'] for t in row['control'])
                t = sum(t['open_q'] for t in row['treatment'])
                print(f'{name[:48]:48} open_q control {c}/{ITERS} treatment {t}/{ITERS}', flush=True)
                with open(out, 'w') as f:
                    json.dump(done, f, ensure_ascii=False, indent=1)
    for field in ('open_q', 'valid', 'card'):
        for arm in ('control', 'treatment'):
            turns = [t for r in done.values() for t in r[arm]]
            print(f'{field:7} {arm:9} {sum(t[field] for t in turns)}/{len(turns)}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/dev/null')
