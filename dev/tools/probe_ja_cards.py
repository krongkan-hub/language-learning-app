"""Why do Japanese sessions show so few vocabulary cards? (#38)

Playtest 2026-10-09: no card in 6 Japanese NPC turns (English: 4 in 5).
Several filters can drop a card, and the model can omit the block; this
measures which one dominates, on the path the learner actually gets
(produce_greeting_turn / produce_actor_turn with call_actor: retries,
salvage and the script mask included).

Per turn, the FIRST reason that applies:
    no_block      the turn carries no vocabulary block at all
    chinese       explanation reads as Chinese (reads_as_chinese)
    not_said      the word is not in the spoken line (_not_in_dialogue)
    name          a proper noun (_is_name)
    trivial       the scenario's own word (_is_trivial_vocab)
    venue         a venue noun (_is_venue_noun)
    question      a question lifted from the line (_is_question)
    everyday      an everyday word (_is_everyday_word)
    shown         the learner sees the card

    N=20 ITERS=2 python3 dev/tools/probe_ja_cards.py out.json
    PATH_KIND=stream N=20 ITERS=2 python3 dev/tools/probe_ja_cards.py out_stream.json

One 7B at a time.
"""
import json
import os
import random
import sys
from collections import Counter

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)
sys.path.insert(0, _here)
from app.llm import call_actor, stream_actor                             # noqa: E402
from app.llm.guards import reads_as_chinese                              # noqa: E402
from app.scenarios.builtins import SCENARIOS                             # noqa: E402
from app.session import (build_actor_system_prompt, build_greeting_system_prompt,  # noqa: E402
                         produce_actor_turn, produce_greeting_turn)
from app.vocab_card import (_is_everyday_word, _is_name, _is_question,   # noqa: E402
                            _is_trivial_vocab, _is_venue_noun, _match_vocab, _not_in_dialogue)

N = int(os.environ.get('N', '20'))
ITERS = int(os.environ.get('ITERS', '2'))
SEED = int(os.environ.get('SEED', '7'))
LANG = 'Japanese'
# PATH=stream: mid turns through stream_actor, the path the web serves them on
PATH = os.environ.get('PATH_KIND', 'call')

OPENER = 'こんにちは。'
PRIOR_NPC = 'かしこまりました。少々お待ちください。'
LEARNER = 'ありがとうございます。よろしくお願いします。'


def reason(raw: str, scenario) -> tuple:
    m = _match_vocab(raw)
    if not m:
        return 'no_block', ''
    word, exp = m.group(1).strip(), m.group(2).strip()
    spoken = (raw[:m.start()] + ' ' + raw[m.end():]).strip()
    checks = (('chinese', reads_as_chinese(exp)),
              ('not_said', _not_in_dialogue(word, spoken, LANG)),
              ('name', _is_name(word, spoken, LANG)),
              ('trivial', _is_trivial_vocab(word, scenario)),
              ('venue', _is_venue_noun(word)),
              ('question', _is_question(word)),
              ('everyday', _is_everyday_word(word, LANG)))
    for name, hit in checks:
        if hit:
            return name, word
    return 'shown', word


def main(out: str) -> None:
    pool = [s for s in SCENARIOS if s.tasks]
    random.Random(SEED).shuffle(pool)
    done = json.load(open(out)) if os.path.isfile(out) else {}
    for scenario in pool[:N]:
        task = scenario.tasks[0]
        for kind in (('mid',) if PATH == 'stream' else ('greeting', 'mid')):
            key = f'{scenario.name}|{kind}'
            if key in done:
                continue
            rows = []
            for _ in range(ITERS):
                if kind == 'greeting':
                    system = build_greeting_system_prompt(scenario, task, language=LANG)
                    raw = produce_greeting_turn([{'role': 'user', 'content': OPENER}], system,
                                                speaker=scenario.speaker, actor_fn=call_actor, language=LANG)
                else:
                    system = build_actor_system_prompt(scenario, task, language=LANG)
                    msgs = [{'role': 'user', 'content': OPENER}, {'role': 'assistant', 'content': PRIOR_NPC},
                            {'role': 'user', 'content': LEARNER}]
                    if PATH == 'stream':
                        raw = produce_actor_turn(msgs, system, speaker=scenario.speaker, actor_fn=stream_actor,
                                                 callback=lambda _s: None, language=LANG)
                    else:
                        raw = produce_actor_turn(msgs, system, speaker=scenario.speaker, actor_fn=call_actor,
                                                 language=LANG)
                why, word = reason(raw, scenario)
                rows.append({'reason': why, 'word': word, 'raw': raw})
            done[key] = rows
            print(f"{key[:44]:44} " + ' '.join(f"{r['reason']}:{r['word'] or '-'}" for r in rows), flush=True)
            with open(out, 'w') as f:
                json.dump(done, f, ensure_ascii=False, indent=1)
    counts = Counter(r['reason'] for rows in done.values() for r in rows)
    total = sum(counts.values())
    for k, v in counts.most_common():
        print(f'{k:10} {v:3}/{total}  {100 * v / total:5.1f}%')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/dev/null')
