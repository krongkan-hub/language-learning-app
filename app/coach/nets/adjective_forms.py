"""な-adjectives conjugated like い-adjectives, and い-adjectives given a な.

きれいくない, 暇かった, 便利ので, 大きいな病院 — all called natural by the
model on the held-out eval (issue #40, dev/evals/eval_jalearner.py).

Only ever overturns a CLEAN verdict — a real model correction always wins.
"""
import re

from ..tables.japanese import (_I_ADJECTIVES, _NA_ADJECTIVES,
                               _NA_EXCLAIM_NEXT)
from ..verdict import is_clean_verdict

_NA = '(?P<adj>' + '|'.join(sorted(_NA_ADJECTIVES, key=len, reverse=True)) + ')'
# Not the tail of a longer word (大好き, 不安): no kanji or katakana right
# before it, and no kana either unless that kana is a particle.
_NOT_INSIDE = ('(?<![\u4e00-\u9fff\u30a0-\u30ff])'
               '(?:(?<![\u3041-\u3096])|(?<=[はがもをにでとへ]))')

_NA_AS_I = {'くないです': 'じゃないです', 'くない': 'じゃない',
            'くありません': 'じゃありません', 'くなかった': 'じゃなかった',
            'かったです': 'でした', 'かった': 'だった', 'くて': 'で'}
_NA_AS_I_ERROR = re.compile(
    _NOT_INSIDE + _NA + '(?P<tail>' + '|'.join(sorted(_NA_AS_I, key=len, reverse=True)) + ')')

# 便利ので / 暇から、: ので and のに need な, から needs だ. から only before a
# comma or the end, since 安全から危険へ is "from safety".
_NA_REASON_ERROR = re.compile(
    _NOT_INSIDE + _NA + '(?:(?P<node>ので|のに)(?![きす])|(?P<kara>から)(?=[、。]|$))')

_I_ADJ_NA_ERROR = re.compile(
    '(?P<adj>' + '|'.join(sorted(_I_ADJECTIVES, key=len, reverse=True)) + ')な'
    '(?P<noun>[\u4e00-\u9fff\u30a0-\u30ff々ー]+)(?=[がをにでへとの])')


def adjective_form_error(text: str):
    """(wrong, right, reason) for the first adjective-form error, or None."""
    match = _NA_AS_I_ERROR.search(text)
    if match:
        adj, tail = match.group('adj'), match.group('tail')
        return (adj + tail, adj + _NA_AS_I[tail],
                f'「{adj}」はな形容詞なので「{_NA_AS_I[tail]}」の形になります')

    match = _NA_REASON_ERROR.search(text)
    if match:
        adj = match.group('adj')
        if match.group('node'):
            node = match.group('node')
            return (adj + node, adj + 'な' + node,
                    f'な形容詞に「{node}」がつくときは「な」が必要です')
        return (adj + 'から', adj + 'だから',
                'な形容詞に「から」がつくときは「だ」が必要です')

    for match in _I_ADJ_NA_ERROR.finditer(text):
        adj, noun = match.group('adj'), match.group('noun')
        if noun.startswith(_NA_EXCLAIM_NEXT):
            continue
        return (f'{adj}な{noun}', f'{adj}{noun}',
                'い形容詞は「な」を使わずに直接名詞を修飾します')
    return None


def apply_adjective_form_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a な/い-adjective mix-up."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    error = adjective_form_error(user_input)
    if not error:
        return feedback
    wrong, right, reason = error
    return f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" ({reason})'
