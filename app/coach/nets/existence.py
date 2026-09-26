"""いる/ある animacy, and で with an existence verb.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
import re
from ..verdict import is_clean_verdict
from ..tables.japanese import (_ARU_TO_IRU, _EXIST_PLACES, _IRU_TO_ARU,
                               _JA_ANIMATE, _JA_INANIMATE, _JA_POSITION)
from .ja_text import _quote_through


_ARU_ON_ANIMATE = re.compile(
    '(?P<noun>' + '|'.join(_JA_ANIMATE) + ')(?P<p>[がは])'
    '(?P<verb>' + '|'.join(sorted(_ARU_TO_IRU, key=len, reverse=True)) + ')'
    # 「先生がある日来ました」「ある程度」 — prenominal ある is not the verb,
    # so the two plain forms only count at a clause boundary.
    r'(?=\s*$|[。、！？]|[^日程度意味種])')


_IRU_ON_INANIMATE = re.compile(
    '(?:' + '|'.join(_JA_POSITION) + ')に[^。、]{0,10}?'
    '(?P<noun>' + '|'.join(_JA_INANIMATE) + ')(?P<p>[がは])'
    '(?P<verb>' + '|'.join(sorted(_IRU_TO_ARU, key=len, reverse=True)) + ')')


_DE_EXISTENCE_ERROR = re.compile(
    # The gap may not contain a te-form: in 「教室で勉強している学生がいます」
    # the で belongs to 勉強している, not to います, and the sentence is correct.
    '(?P<place>' + '|'.join(_EXIST_PLACES) + ')で(?![^。、]{0,12}?(?:てい|でい|って|んで))'
    '[^。、]{0,8}?'
    '(?P<noun>' + '|'.join(_JA_ANIMATE) + ')(?P<p>[がは])'
    '(?P<verb>います|いました|いる|いた)')


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
