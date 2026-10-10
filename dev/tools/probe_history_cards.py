"""A/B: does a card-less history teach the actor to stop writing the card? (#38)

A real Japanese session (2026-10-10, traced): turns 1-2 carried a
vocabulary block, turns 3-5 had none — and were 49-88 characters long, far
from max_tokens. The actor sees its own earlier turns with the block stripped
(the transcript keeps only what was said), so by turn 3 its history says
"this character never writes a card". OPEN-19 fixed turn 2; nothing measured
turn 4.

Arms, same scenario, task, seeds and a K-turn history of ordinary exchanges:
    stripped   history NPC turns as production stores them (no block)
    carded     the same NPC turns each followed by a vocabulary block
Per next turn: does the raw generation carry a block (match_vocab_fields)?

    K=4 N=20 ITERS=2 LANG=Japanese python3 dev/tools/probe_history_cards.py out.json
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
from app.llm import ACTOR_OPTS, _llm_chat                                # noqa: E402
from app.llm.vocab import match_vocab_fields                             # noqa: E402
from app.scenarios.builtins import SCENARIOS                             # noqa: E402
from app.session import build_actor_system_prompt                        # noqa: E402

K = int(os.environ.get('K', '4'))
N = int(os.environ.get('N', '20'))
ITERS = int(os.environ.get('ITERS', '2'))
SEED = int(os.environ.get('SEED', '7'))
LANG = os.environ.get('LANG_UNDER_TEST', 'Japanese')

EXCHANGES = {
    'Japanese': [
        ('こんにちは。', 'いらっしゃいませ。本日はどのようなご用件でしょうか。', '用件', '何かをしに来た目的のこと。'),
        ('少し相談したいことがあります。', 'かしこまりました。どのようなご相談でしょうか。', '相談', '人に意見やアドバイスを求めること。'),
        ('おすすめを教えてください。', 'こちらが一番人気でございます。', '人気', '多くの人に好まれていること。'),
        ('それにします。', 'ありがとうございます。すぐにご用意いたします。', '用意', '前もって準備すること。'),
        ('どのくらいかかりますか。', '十分ほどでございます。少々お待ちください。', '少々', '少しの、という丁寧な言い方。'),
        ('わかりました。待ちます。', 'お待たせいたしました。こちらでございます。', 'お待たせ', '相手を待たせたときの丁寧な言葉。'),
    ],
    'English': [
        ('Hello.', 'Good afternoon, how can I help you today?', 'afternoon', 'the part of the day after noon.'),
        ('I need some advice.', 'Of course. What would you like advice on?', 'advice', 'an opinion about what someone should do.'),
        ('What do you recommend?', 'This one is our most popular choice.', 'popular', 'liked by many people.'),
        ("I'll take it.", "Great, I'll get that ready for you right away.", 'right away', 'immediately.'),
        ('How long will it take?', 'About ten minutes, if you can wait.', 'about', 'roughly; not exactly.'),
        ("Okay, I'll wait.", 'Thanks for waiting, here you are.', 'here you are', 'said when handing something over.'),
    ],
}
NEXT_LEARNER = {'Japanese': 'ありがとうございます。ほかにも聞いていいですか。',
                'English': 'Thanks. Can I ask one more thing?'}


def history(carded: bool) -> list:
    msgs = []
    for learner, npc, word, exp in EXCHANGES[LANG][:K]:
        msgs.append({'role': 'user', 'content': learner})
        block = (f'\n\n<vocab>\nword: {word}\nexplanation: {exp}\nencourage: '
                 + ('使ってみてください。' if LANG == 'Japanese' else 'Try it next time.') + '\n</vocab>')
        msgs.append({'role': 'assistant', 'content': npc + (block if carded else '')})
    msgs.append({'role': 'user', 'content': NEXT_LEARNER[LANG]})
    return msgs


def main(out: str) -> None:
    assert K <= len(EXCHANGES[LANG])
    pool = [s for s in SCENARIOS if s.tasks]
    random.Random(SEED).shuffle(pool)
    done = json.load(open(out)) if os.path.isfile(out) else {}
    for scenario in pool[:N]:
        if scenario.name in done:
            continue
        system = build_actor_system_prompt(scenario, scenario.tasks[0], language=LANG)
        row = {}
        for arm in ('stripped', 'carded'):
            row[arm] = []
            for _ in range(ITERS):
                raw = _llm_chat(messages=[{'role': 'system', 'content': system}] + history(arm == 'carded'),
                                options={**ACTOR_OPTS, 'script': LANG}, cache_key=None)['message']['content']
                row[arm].append({'card': bool(match_vocab_fields(raw)), 'chars': len(raw)})
        done[scenario.name] = row
        print(f"{scenario.name[:40]:40} stripped {sum(t['card'] for t in row['stripped'])}/{ITERS}"
              f"  carded {sum(t['card'] for t in row['carded'])}/{ITERS}", flush=True)
        with open(out, 'w') as f:
            json.dump(done, f, ensure_ascii=False, indent=1)
    for arm in ('stripped', 'carded'):
        turns = [t for r in done.values() for t in r[arm]]
        print(f'card {arm:9} {sum(t["card"] for t in turns)}/{len(turns)}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/dev/null')
