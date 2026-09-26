"""Verbs that do not go with their noun — 薬を食べる.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
import re
from ..verdict import is_clean_verdict
from ..tables.japanese import (_DRINK_NOUNS, _EAT_TO_DRINK)


_EAT_DRINK_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_DRINK_NOUNS) + ')を'
    '(?P<verb>' + '|'.join(sorted(_EAT_TO_DRINK, key=len, reverse=True)) + ')')


def apply_collocation_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict when a drink or a medicine is 食べる'd."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    match = _EAT_DRINK_ERROR.search(user_input)
    if not match:
        return feedback
    noun, verb = match.group('noun'), match.group('verb')
    right = _EAT_TO_DRINK[verb]
    return (f'💡 Feedback:\n- ❌ "{noun}を{verb}" → ✅ "{noun}を{right}" '
            f'(「{noun}」は「飲む」を使います)')
