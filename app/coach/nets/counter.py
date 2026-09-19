"""Counters that do not match the shape of the noun counted.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
import re

from ..verdict import is_clean_verdict
from .tables import (_COUNTER_RULES, _COUNT_NUM)


def apply_counter_net(feedback: str, user_input: str, language: str) -> str:
    """Catch a counter that does not match the shape of the noun counted.
    Only ever overturns a clean verdict."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    for nouns, wrong_counters, suggested, reason in _COUNTER_RULES:
        for noun in nouns:
            for wrong in wrong_counters:
                # The noun and its count sit adjacent in the error shape
                # (水を三枚), the same adjacency that kept the transitivity net
                # from reaching across clauses.
                pattern = re.escape(noun) + r'を(' + _COUNT_NUM + r')' + re.escape(wrong)
                match = re.search(pattern, user_input)
                if not match:
                    continue
                number = match.group(1)
                fixes = '」か「'.join(f'{number}{s}' for s in suggested)
                return (f'💡 Feedback:\n- ❌ "{number}{wrong}" → ✅ '
                        f'"{number}{suggested[0]}" '
                        f'({reason}。「{fixes}」と言います)')
    return feedback
