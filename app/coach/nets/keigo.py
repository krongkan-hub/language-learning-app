"""Humble forms turned on the listener: お待ちしてください, 拝見してください.

お〜する and 拝見する lower the SPEAKER; asking the listener to do them asks
the customer to humble themselves. Both are fixed shapes with one right
answer, and the model called both natural on the held-out eval (issue #40,
dev/evals/eval_jalearner.py).

Only ever overturns a CLEAN verdict — a real model correction always wins.
"""
import re

from ..tables.japanese import _O_HUMBLE_STEMS
from ..verdict import is_clean_verdict

_REQUEST = '(?P<req>ください|下さい|くださいませ)'
_O_SHITE_KUDASAI = re.compile(
    'お(?P<stem>' + '|'.join(sorted(_O_HUMBLE_STEMS, key=len, reverse=True)) + ')'
    'して' + _REQUEST)
_HAIKEN_KUDASAI = re.compile('拝見して' + _REQUEST)


def keigo_error(text: str):
    """(wrong, right, reason) for a humble form aimed at the listener."""
    match = _O_SHITE_KUDASAI.search(text)
    if match:
        stem, req = match.group('stem'), match.group('req')
        return (match.group(0), f'お{stem}{req}',
                '「お〜する」は自分の動作に使う謙譲語なので、相手には「お〜ください」を使います')
    match = _HAIKEN_KUDASAI.search(text)
    if match:
        return (match.group(0), 'ご覧' + match.group('req'),
                '「拝見する」は自分の動作に使う謙譲語なので、相手には「ご覧ください」を使います')
    return None


def apply_keigo_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a humble form aimed at the listener."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    error = keigo_error(user_input)
    if not error:
        return feedback
    wrong, right, reason = error
    return f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" ({reason})'
