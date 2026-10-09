"""て-form 音便, い-adjective negatives and past, adverbial forms.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
import re
from ..verdict import is_clean_verdict
from ..tables.japanese import (_ADVERBIAL_VERBS, _I_ADJECTIVES,
                               _I_ADJ_JANAI_TAIL, _TE_ONBIN)


_TE_ONBIN_ERROR = re.compile('(' + '|'.join(_TE_ONBIN) + ')て')


_I_ADJ_PAST_ERROR = re.compile('(?P<stem>[^\\s、。「」『』！？!?]{0,10}?)(?<!み)(?P<adj>たい|ない)でした')


_I_ADJ_LIST_ERROR = re.compile('(?P<adj>' + '|'.join(_I_ADJECTIVES) + ')でした')


_I_ADJ_JANAI_ERROR = re.compile(
    '(?P<adj>' + '|'.join(_I_ADJECTIVES) + ')じゃ'
    '(?P<tail>' + '|'.join(sorted(_I_ADJ_JANAI_TAIL, key=len, reverse=True))
    + ')(?![かね])')


_I_ADJ_ADVERB_ERROR = re.compile(
    '(?P<adj>' + '|'.join(_I_ADJECTIVES) + ')'
    '(?P<verb>' + '|'.join(sorted(_ADVERBIAL_VERBS, key=len, reverse=True)) + ')')


# Playtest 2026-10-09: 子供も飲めるですか came back natural. A verb's
# dictionary form takes no です — the polite form is ます. Matched only right
# after a kanji (a verb stem) or after a particle for the kana-only verbs, so
# nouns in です (駅の近くです, ふつうです) stay out of reach.
_OKURIGANA = ''.join(chr(c) for c in range(0x3041, 0x3097)
                     if chr(c) not in 'がはをにでもとのへや')   # never a particle
_VERB_DESU_ERROR = re.compile(
    '(?P<verb>[\u4e00-\u9fff々]+[' + _OKURIGANA + ']{0,3}?[うくぐすつぬぶむる]'
    '|(?<=[がはもをにで])(?:ある|いる|できる|わかる|する))です')
# 遅れそうです / 行くようです / 来るでしょう-type endings are correct: そう and
# よう are what です attaches to there, not the verb.
_NOT_VERBS = ('近く', '遠く', '多く', '全く', '早く', 'そう', 'よう')
_GODAN_I = dict(zip('うくぐすつぬぶむる', 'いきぎしちにびみり'))
_E_I_ROWS = set('えけげせぜてでねへべぺめれいきぎしじちぢにひびぴみり')
_ICHIDAN_KANJI = set('見着寝出居煮似干')


def _masu_stem(verb: str) -> str:
    """飲める → 飲め, 行く → 行き, 勉強する → 勉強し: the stem ます attaches to."""
    if verb.endswith('する'):
        return verb[:-2] + 'し'
    if verb in ('来る', 'くる'):
        return verb[:-1] if verb == '来る' else 'き'
    if verb.endswith('る') and len(verb) >= 2:
        before = verb[-2]
        if before in _E_I_ROWS or before in _ICHIDAN_KANJI:
            return verb[:-1]
    return verb[:-1] + _GODAN_I[verb[-1]]


def apply_conjugation_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a mis-formed te-form or i-adjective past.

    Both are regular morphology the model does not enforce: it accepted 読みて
    and 行きたいでした as natural. Only ever overturns a clean verdict.
    """
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    match = _TE_ONBIN_ERROR.search(user_input)
    if match:
        stem = match.group(1)
        return (f'💡 Feedback:\n- ❌ "{stem}て" → ✅ "{_TE_ONBIN[stem]}" '
                f'(五段動詞のテ形は音便の形になります)')

    match = _I_ADJ_PAST_ERROR.search(user_input)
    if match:
        stem, adj = match.group('stem'), match.group('adj')
        past = 'たかったです' if adj == 'たい' else 'なかったです'
        return (f'💡 Feedback:\n- ❌ "{stem}{adj}でした" → ✅ "{stem}{past}" '
                f'(「{adj}」はい形容詞なので、過去形は「{past}」になります)')

    match = _I_ADJ_LIST_ERROR.search(user_input)
    if match:
        adj = match.group('adj')
        past = adj[:-1] + 'かったです'
        return (f'💡 Feedback:\n- ❌ "{adj}でした" → ✅ "{past}" '
                f'(い形容詞の過去形は「かったです」になります)')

    match = _I_ADJ_JANAI_ERROR.search(user_input)
    if match:
        adj, tail = match.group('adj'), match.group('tail')
        right = adj[:-1] + _I_ADJ_JANAI_TAIL[tail]
        return (f'💡 Feedback:\n- ❌ "{adj}じゃ{tail}" → ✅ "{right}" '
                f'(い形容詞の否定は「く」の形を使います)')

    match = _I_ADJ_ADVERB_ERROR.search(user_input)
    if match:
        adj, verb = match.group('adj'), match.group('verb')
        return (f'💡 Feedback:\n- ❌ "{adj}{verb}" → ✅ "{adj[:-1]}く{verb}" '
                f'(い形容詞が動詞を修飾するときは「く」の形になります)')

    for match in _VERB_DESU_ERROR.finditer(user_input):
        verb = match.group('verb')
        if verb.endswith(_NOT_VERBS):
            continue
        return (f'💡 Feedback:\n- ❌ "{verb}です" → ✅ "{_masu_stem(verb)}ます" '
                f'(動詞の丁寧形は「です」ではなく「ます」を使います)')

    return feedback
