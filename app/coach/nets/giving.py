"""あげる pointed at the speaker: 友達が私にプレゼントをあげました.

あげる gives away from the speaker; something given TO the speaker is くれる
(くださる from a superior). The model called all four held-out cases natural
(issue #40, dev/evals/eval_jalearner.py).

Only ever overturns a CLEAN verdict — a real model correction always wins.
"""
import re

from ..tables.japanese import _SUPERIOR_GIVERS
from ..verdict import is_clean_verdict

# 私に … あげる in one clause. Not 私には / 私にとって (a different frame),
# and nothing quoted in between: 妹が私に「これあげる」と言いました. Not the
# て form: 私にあげてください wants ください, not くれてください.
_TO_ME_AGERU = re.compile(
    '(?P<to>私|わたし|僕|ぼく)に(?!は|とって)'
    '(?P<mid>[^、。！？!?「」『』]{0,15}?)'
    'あげ(?P<tail>ました|ます|ません|た|る)(?![いらさ])')
_TAIL_KURERU = {'ました': 'くれました', 'ます': 'くれます', 'ません': 'くれません',
                'た': 'くれた', 'る': 'くれる'}
_TAIL_KUDASARU = {'ました': 'くださいました', 'ます': 'くださいます',
                  'ません': 'くださいません', 'た': 'くださった', 'る': 'くださる'}


def giving_error(text: str):
    """(wrong, right, reason) for あげる aimed at the speaker, or None."""
    match = _TO_ME_AGERU.search(text)
    if not match:
        return None
    before = text[:match.start()]
    clause = before[max(before.rfind(c) for c in '、。！？!?') + 1:]
    superior = any(g in clause for g in _SUPERIOR_GIVERS)
    table, verb = (_TAIL_KUDASARU, 'くださる') if superior else (_TAIL_KURERU, 'くれる')
    wrong = match.group(0)
    right = wrong[:-len('あげ' + match.group('tail'))] + table[match.group('tail')]
    return (wrong, right,
            f'自分が受け取るときは「あげる」ではなく「{verb}」を使います')


def apply_giving_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on あげる with the speaker as receiver."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    error = giving_error(user_input)
    if not error:
        return feedback
    wrong, right, reason = error
    return f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" ({reason})'
