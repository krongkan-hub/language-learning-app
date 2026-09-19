"""いる/ある animacy, and で with an existence verb.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
from ..verdict import is_clean_verdict
from .tables import (_ARU_ON_ANIMATE, _ARU_TO_IRU, _DE_EXISTENCE_ERROR, 
                     _IRU_ON_INANIMATE, _IRU_TO_ARU, _quote_through)


def apply_existence_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on いる/ある animacy, or on で where the place
    something exists needs に. Only ever overturns a clean verdict."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    match = _ARU_ON_ANIMATE.search(user_input)
    if match:
        noun, p, verb = match.group('noun'), match.group('p'), match.group('verb')
        right = _ARU_TO_IRU[verb]
        return (f'💡 Feedback:\n- ❌ "{noun}{p}{verb}" → ✅ "{noun}{p}{right}" '
                f'(生き物の存在は「いる」で表します)')

    match = _IRU_ON_INANIMATE.search(user_input)
    if match:
        noun, p, verb = match.group('noun'), match.group('p'), match.group('verb')
        right = _IRU_TO_ARU[verb]
        return (f'💡 Feedback:\n- ❌ "{noun}{p}{verb}" → ✅ "{noun}{p}{right}" '
                f'(生き物ではないものの存在は「ある」で表します)')

    match = _DE_EXISTENCE_ERROR.search(user_input)
    if match:
        wrong, right = _quote_through(
            user_input, match,
            match.group(0).replace(match.group('place') + 'で',
                                   match.group('place') + 'に', 1))
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(「いる」「ある」が表す存在の場所は「に」で示します)')

    return feedback
