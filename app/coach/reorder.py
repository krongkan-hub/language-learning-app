"""Dropping a Japanese "correction" that only moves the words around.

「先生がある日教室に来ました。」 is correct, and the coach rewrote it to
「ある日、先生が教室に来ました。」 on 5 of 5 runs, which failed the jarecall
clean arm at 95/100 (OPEN-49). Japanese word order is free before the
predicate: fronting a time phrase is a style preference, and this project
treats over-correction as its worst failure — a learner told their correct
sentence is wrong loses more than one told nothing.

The line between the two is the predicate. 明日私は行きます東京へ IS a word
order error and must keep its correction (OPEN-38): 東京へ trails the verb, so
the sentence is not predicate-final. 先生がある日教室に来ました ends in
来ました, so every reordering above it is taste.

So: drop a bullet only when it is a pure permutation of the learner's own
characters — nothing added, nothing removed, punctuation aside — AND the
learner's sentence already ends in a predicate. A correction that changes a
particle, a conjugation or a word is not a permutation and never reaches here.
"""
import re

from .verdict import _CORRECTION_BULLET

# Politeness and plain forms that can end a Japanese sentence. A sentence
# ending in one of these has its predicate where it belongs, whatever the
# order above it.
_PREDICATE_FINAL = re.compile(
    r'(ます|ました|ません|ませんでした|ましょう|です|でした|でしょう|'
    r'ください|ない|なかった|だった|[うくぐすつぬぶむる]|[たいだ])$')

_STRIP = str.maketrans('', '', '、。！？!?「」『』"\'  　')


def _same_characters(a: str, b: str) -> bool:
    """True when two strings differ only in the order of their characters."""
    a, b = a.translate(_STRIP), b.translate(_STRIP)
    return a != b and sorted(a) == sorted(b)


def drop_stylistic_reorder(feedback: str, language: str) -> str:
    """Remove bullets that reorder an already predicate-final sentence."""
    if language != 'Japanese' or '❌' not in feedback:
        return feedback

    kept, dropped = [], False
    for line in feedback.split('\n'):
        match = _CORRECTION_BULLET.search(line)
        if match:
            wrong, right = match.group(1), match.group(2)
            stripped = wrong.translate(_STRIP)
            if _same_characters(wrong, right) and _PREDICATE_FINAL.search(stripped):
                dropped = True
                continue
        kept.append(line)

    if not dropped:
        return feedback
    if not any(_CORRECTION_BULLET.search(line) for line in kept):
        # Every bullet was taste. Say nothing rather than print an empty
        # Feedback header; the English sentinel is what localize_clean_verdict
        # keys on, and this runs before it.
        return '💡 Feedback: Perfectly natural!'
    return '\n'.join(kept)
