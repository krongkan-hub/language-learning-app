"""English plural after a number word. Only ever overturns a CLEAN verdict.

Seen playing the web front end at a café: the coach caught "three cookie" and
"four muffin" but called "two latte" and "two cookie" perfectly natural, in
the same session — ordering things by number is most of what a learner says
in these scenarios, and the model is a coin flip on it.

Deliberately narrow, because without a part-of-speech tagger the same shape
covers "two major reasons", where "major" is an adjective and must not become
"majors". Measured on JFLEG's 6,000 native reference sentences and the
scenario catalogue (see the tests), each rule below is there because the
version without it fired on correct English:

  * number WORDS only. "Table 5 is free" and "Bus 2 stop" are correct.
    "both" is out: it is mostly followed by a verb.
  * the noun must END the phrase — followed by punctuation, the end, or a
    word like "please"/"to"/"of" — so "two major reasons" and "three
    souvenir shops" never reach it. That leaves "two cookie please", "four
    muffin to go", "two slice of pizza": the ordering shapes.
  * the noun and its plural are both reasonably common words (SCOWL <= 50).
"""
import re

from ..verdict import is_clean_verdict
from ..tables.english import _NOT_A_NOUN, _NUMBER, _PHRASE_END
from .spelling import _level

_TOKEN = re.compile(r"[A-Za-z]+|[^\sA-Za-z]")


def _plural(noun: str):
    if noun.endswith('y') and noun[-2] not in 'aeiou':
        candidates = [noun[:-1] + 'ies']
    elif re.search(r'(s|x|z|ch|sh)$', noun):
        candidates = [noun + 'es']
    else:
        candidates = [noun + 's']
    return next((p for p in candidates if _level(p) <= 50), None)


def plural_corrections(text: str) -> list:
    """(as written, corrected) for each "two cookie" this net is sure of."""
    toks = _TOKEN.findall(text)
    found = []
    for i in range(len(toks) - 1):
        num, noun = toks[i], toks[i + 1]
        if num.lower() not in _NUMBER:
            continue
        if num.lower() == 'few' and not (i and toks[i - 1].lower() == 'a'):
            continue
        if (len(noun) < 3 or not noun.isalpha() or not noun.islower()
                or noun in _NOT_A_NOUN or noun.endswith('s') or _level(noun) > 50):
            continue
        after = toks[i + 2].lower() if i + 2 < len(toks) else ''
        if after in ("'", '-') or (i and toks[i - 1] == '-'):
            continue                          # "o'clock", "two-hour"
        if after.isalpha() and after not in _PHRASE_END:
            continue                          # "two major reasons"
        plural = _plural(noun)
        if plural:
            found.append((f'{num} {noun}', f'{num} {plural}'))
    return found


def apply_plural_net(feedback: str, user_input: str, language: str) -> str:
    """Catch "two latte" when the coach called it natural."""
    if language != 'English' or not is_clean_verdict(feedback, language):
        return feedback
    fixes = plural_corrections(user_input)
    if not fixes:
        return feedback
    lines = '\n'.join(
        f'- ❌ "{was}" → ✅ "{now}" (after "{was.split()[0].lower()}", '
        f'the noun is plural)' for was, now in fixes[:2])
    return '\U0001f4a1 Feedback:\n' + lines
