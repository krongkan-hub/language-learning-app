"""How common an English word is, from SCOWL. Read by the spelling and plural
nets and by the vocabulary-card filter.

level(word) is the word's SCOWL size: 10 for the thousand or so commonest
words of English, rising through 20, 35, 40, 50, 55, 60, 70 to 80 for
large-dictionary rarities; 99 when the word is not in the list at all. The
list is en_words.txt.gz beside this file, rebuilt by
dev/tools/build_en_lexicon.py; SCOWL's licence requires SCOWL-COPYRIGHT to
ship with it.
"""
import functools
import gzip
import os

_DATA = os.path.join(os.path.dirname(__file__), 'en_words.txt.gz')
NOT_A_WORD = 99


@functools.lru_cache(maxsize=1)
def _levels() -> dict:
    with gzip.open(_DATA, 'rt', encoding='ascii') as f:
        return {w: int(lvl) for lvl, w in (line.rstrip('\n').split('\t') for line in f)}


def level(word: str) -> int:
    """The SCOWL size of a lowercase word, or NOT_A_WORD."""
    return _levels().get(word, NOT_A_WORD)
