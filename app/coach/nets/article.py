"""English a / an. Only ever overturns a CLEAN verdict.

"a everything", "an broad", "a apple": the article has to match the sound of
the next word. Measured on JFLEG before shipping: it fired 17 times on
learner sentences and an annotator made that same fix all 17 times; on the
6,000 native reference sentences it fired 7 times, 5 on errors the annotators
left in and 2 on "a" used as a letter ("a on", "a in"), which the
_NOT_AFTER_ARTICLE table now skips.

Spelling decides, not sound, so the exceptions are closed tables in
app/coach/tables/english.py: silent h (an hour) and vowels said as "y"/"w"
(a university, a one-way ticket). Acronyms are left alone — "an FAQ" and
"a URL" depend on how the letters are read.
"""
import re

from ..tables.english import _A_BEFORE_VOWEL, _AN_BEFORE_CONSONANT, _NOT_AFTER_ARTICLE
from ..verdict import is_clean_verdict

_ARTICLE = re.compile(r"\b(a|an|A|An)\s+([A-Za-z][A-Za-z'-]*)")


def article_corrections(text: str) -> list:
    """(as written, corrected) for each a/an that does not fit the next word."""
    found = []
    for m in _ARTICLE.finditer(text):
        art, word = m.group(1), m.group(2)
        lw = word.lower()
        if (word.isupper() and len(word) > 1) or lw in _NOT_AFTER_ARTICLE:
            continue
        vowel = lw[0] in 'aeiou'
        if art.lower() == 'a' and vowel and not lw.startswith(_A_BEFORE_VOWEL):
            found.append((m.group(0), ('An' if art[0] == 'A' else 'an') + ' ' + word))
        elif art.lower() == 'an' and not vowel and not lw.startswith(_AN_BEFORE_CONSONANT):
            found.append((m.group(0), ('A' if art[0] == 'A' else 'a') + ' ' + word))
    return found


def apply_article_net(feedback: str, user_input: str, language: str) -> str:
    """Catch "a apple" / "an book" when the coach called it natural."""
    if language != 'English' or not is_clean_verdict(feedback, language):
        return feedback
    fixes = article_corrections(user_input)
    if not fixes:
        return feedback
    lines = '\n'.join(
        f'- ❌ "{was}" → ✅ "{now}" ('
        + ('"an" before a vowel sound' if now.lower().startswith('an ') else '"a" before a consonant sound')
        + ')' for was, now in fixes[:2])
    return '\U0001f4a1 Feedback:\n' + lines
