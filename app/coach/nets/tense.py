"""Tense and aspect: 昨日、病院に行きます / 田中さんを知りますか / 今、東京に
住みます / 先月から、この病院で働きます.

The model called each of these natural on the held-out eval (issue #40,
dev/evals/eval_jalearner.py). Every rule is anchored on a word in the
learner's own sentence — a past time word, 今, 知る — never on a guess about
what they meant.

Only ever overturns a CLEAN verdict — a real model correction always wins.
"""
import re

from ..tables.japanese import (_CONTINUING_STEMS, _NOW_WORDS, _PAST_TIME_NO,
                               _PAST_TIME_WORDS)
from ..verdict import is_clean_verdict

_PAST = '(?P<when>' + '|'.join(sorted(_PAST_TIME_WORDS, key=len, reverse=True)) + ')'

# A past time word, then one clause that ends in a non-past ます/ません.
# The clause may hold no other comma, no た/だ (昨日買った本を読みます — the
# past belongs to the relative clause) and no ている (昨日から休んでいます).
# から, より, まで, と and の after the time word make it something else:
# 昨日から熱があります is still true now, 昨日の宿題をします is today's job.
# ございます is left alone: 昨日はありがとうございます is said. So is a
# quoting verb: 昨日は英語で何と言いますか asks about the word 昨日.
_PAST_THEN_PRESENT = re.compile(
    '(?:^|(?<=[、。！？!?\\sはが]))' + _PAST
    + '(?:(?P<no>の(?:' + '|'.join(_PAST_TIME_NO) + '))|(?!から|より|まで|と|の))'
    '(?P<sep>は|、|も)?'
    '(?P<body>[^、。！？!?「」たっだ]*?)'
    '(?P<verb>[^\\s、。！？!?がはをにでともへや]{1,6}?)(?P<end>ません|ます)'
    '(?P<q>か)?(?=[。！？!?]|$)')

_SHIRIMASU = re.compile('(?<![\\u4e00-\\u9fff])知ります(?P<q>か)?')

# 今 that means "now", not 今度 / 今日 / 今年 / 今から / 今の.
_NOW = '今(?![度後年月週日夜朝晩回のか])'
_SINCE = _PAST + 'から'
_CONTINUING = re.compile(
    '(?:' + _NOW + '|' + _SINCE + ')[、は]?[^、。！？!?]*?'
    '(?P<stem>' + '|'.join(_CONTINUING_STEMS) + ')ます(?P<q>か)?(?=[。！？!?]|$)')


def tense_error(text: str):
    """(wrong, right, reason) for the first tense/aspect slip, or None."""
    match = _SHIRIMASU.search(text)
    if match:
        q = match.group('q') or ''
        return (f'知ります{q}', f'知っています{q}',
                '「知る」の今の状態は「知っています」で表します')

    match = _CONTINUING.search(text)
    if match:
        stem, q = match.group('stem'), match.group('q') or ''
        return (f'{stem}ます{q}', _CONTINUING_STEMS[stem] + q,
                '今も続いていることは「ています」で表します')

    match = _PAST_THEN_PRESENT.search(text)
    if match and not any(w in match.group('body') for w in _NOW_WORDS) \
            and 'てい' not in match.group('body') + match.group('verb') \
            and not match.group('verb').endswith('ござい') \
            and not match.group('body').endswith(('と', 'って')):
        verb, end, q = match.group('verb'), match.group('end'), match.group('q') or ''
        past = 'ました' if end == 'ます' else 'ませんでした'
        return (f'{verb}{end}{q}', f'{verb}{past}{q}',
                f'「{match.group("when")}」は過去なので、過去形にします')
    return None


def apply_tense_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a tense the sentence's own time word rules out."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    error = tense_error(user_input)
    if not error:
        return feedback
    wrong, right, reason = error
    return f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" ({reason})'
