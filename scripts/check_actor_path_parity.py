#!/usr/bin/env python3
"""Assert the two actor output paths agree on the same model output.

`call_actor` assembles a whole turn and validates it; `stream_actor` emits
sentence by sentence and is the path the learner actually reads. They have
diverged twice, and both times it took weeks to notice:

  0df1d3f  each path carried its own copy of the per-sentence rules, and the
           residual-markup rule sat dead on the streamed path for eleven days
  OPEN-31  llm.py kept six literal `encourage:` patterns while cli.py matched
           `encourag\\w*`, so a drifted vocab label was destroyed on one path
           and kept on the other

OPEN-32 records why nothing caught either: no eval exercises `stream_actor`.
The gated suites call `call_actor`, the raw harness calls `_llm_chat`, and
`stream_actor` was covered only by unit tests of its own behaviour — never
against its sibling.

This is deterministic and needs no model. `stream_actor` takes `generator_fn`
precisely so it can be driven from captured text, so both paths are fed the
SAME bytes and any disagreement is the code, not the sampler. That makes it
cheap enough for `check_all.sh`, where a divergence is caught by the commit
that introduces it rather than by a learner.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.session import ACTOR_MAX_SENTENCES
from app.llm import (match_vocab_block, sanitize,
                     stream_actor, strip_vocab_block, validate)

CARD = ("word: sommelier\n"
        "explanation: the staff member who advises on wine\n"
        "{label}: Ask the sommelier for a pairing.")

# Shapes taken from real captured output. Each is a case where the two paths
# could plausibly disagree — label drift, over-length, markup, a card with no
# tags, and non-ASCII punctuation.
CASES = [
    ('clean three sentences',
     "Good afternoon. Our special today is the sea bass. What would you like?"),
    ('card, canonical label',
     "Good afternoon. Our special is the sea bass.\n\n" + CARD.format(label='encourage')),
    ('card, drifted label',
     "Good afternoon. Our special is the sea bass.\n\n" + CARD.format(label='encouragement')),
    ('card, misspelled label',
     "Good afternoon. Our special is the sea bass.\n\n" + CARD.format(label='exourage')),
    ('card, tagged',
     "Good afternoon. Our special is the sea bass.\n\n<vocab>\n"
     + CARD.format(label='encourage') + "\n</vocab>"),
    ('four sentences with a card',
     "Good afternoon. Our special is the sea bass. It is line-caught. "
     "What would you like?\n\n" + CARD.format(label='encourage')),
    ('japanese, card',
     "こんにちは。本日のおすすめは真鯛です。何になさいますか。\n\n"
     "word: 旬\nexplanation: その食材が一番おいしい時期\nencourage: 「旬」を使ってみましょう。"),
]


def _generator(text, chunk=12):
    def gen():
        for i in range(0, len(text), chunk):
            yield text[i:i + chunk]
    return gen


def run_case(label, text, language='English'):
    """Returns (disagreements, detail) for one captured output."""
    emitted = []
    streamed = stream_actor(
        [{'role': 'user', 'content': 'x'}], 'SYS', speaker='Waiter',
        max_sentences=ACTOR_MAX_SENTENCES, callback=emitted.append,
        generator_fn=_generator(text), cache_key=None, language=language)

    assembled = sanitize(text, speaker='Waiter')
    problems = []

    # 1. Does a vocab card survive on both paths, or neither?
    stream_card = match_vocab_block(streamed) is not None
    assembled_card = match_vocab_block(assembled) is not None
    if stream_card != assembled_card:
        problems.append(
            f'vocab card survives on stream={stream_card} assembled={assembled_card}')

    # 2. Do both agree on whether the turn is valid at all?
    ok, reason = validate(assembled, max_sentences=ACTOR_MAX_SENTENCES,
                          language=language)
    emitted_count = len(emitted)
    if ok and emitted_count == 0 and strip_vocab_block(assembled):
        problems.append('assembled path accepted the turn, stream emitted nothing')

    # 3. Neither path may leak the vocab labels into spoken text.
    for name, spoken in (('stream', ' '.join(emitted)),
                         ('assembled', strip_vocab_block(assembled))):
        low = spoken.lower()
        if 'explanation:' in low or 'word:' in low:
            problems.append(f'{name} path leaked vocab labels into dialogue')

    return problems, (f'stream_card={stream_card} assembled_card={assembled_card} '
                      f'emitted={emitted_count} valid={ok} reason={reason or "-"}')


def main():
    failures = 0
    print('Actor path parity — call_actor vs stream_actor on identical bytes')
    print('-' * 78)
    for label, text in CASES:
        language = 'Japanese' if 'japanese' in label else 'English'
        problems, detail = run_case(label, text, language)
        status = 'ok ' if not problems else 'FAIL'
        print(f'  {status} {label:<28} {detail}')
        for p in problems:
            print(f'       -> {p}')
        failures += len(problems)
    print('-' * 78)
    if failures:
        print(f'❌ CHECK FAILED: actor_path_parity ({failures} disagreement(s))')
        return 1
    print('✅ actor_path_parity PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
