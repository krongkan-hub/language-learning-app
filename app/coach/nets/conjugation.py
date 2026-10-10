"""て-form 音便, い-adjective negatives and past, adverbial forms.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
import re
from ..verdict import is_clean_verdict
from ..tables.japanese import (_ADVERBIAL_VERBS, _DESU_VERBS, _I_ADJECTIVES,
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
# dictionary form takes no です — the polite form is ます. Only verbs in
# _DESU_VERBS fire (review #53: a kana pattern caught 一つです and どうですか).
# A verb spelled in kana alone (ある, いる, わかる) must follow a particle or
# open the sentence, or 山田ゆう-style names and longer words would match.
_DESU_VERB_ERROR = re.compile(
    '(?:(?P<noun>[\u4e00-\u9fff]{2})する'
    '|(?P<verb>' + '|'.join(sorted(_DESU_VERBS, key=len, reverse=True)) + '))です')
_KANA_ONLY = re.compile('^[\u3041-\u3096]+$')


def _desu_error(text: str):
    """(wrong, right) for the first verb + です in `text`, or None."""
    for match in _DESU_VERB_ERROR.finditer(text):
        if match.group('noun'):
            noun = match.group('noun')
            return noun + 'するです', noun + 'します'
        verb = match.group('verb')
        before = text[:match.start()][-1:]
        if _KANA_ONLY.match(verb) and before and before not in 'がはもをにでとへ、。 　':
            continue
        return verb + 'です', _DESU_VERBS[verb] + 'ます'
    return None


# Playtest 2026-10-09 (#36): 頭が痛いの薬がありますか came back clean with the
# fix filed under Level up, so it was never drilled. An い-adjective modifies
# a noun directly (痛い薬); の after it is only right when it stands for the
# noun itself — 安いのはありますか, 高いのがいい, 痛いので — which is always
# followed by kana, never by the noun. Only listed adjectives: nouns ending in
# い (お互いの国, 違いの理由, 時間ぐらいの) take の correctly.
_I_ADJ_NO_NOUN_ERROR = re.compile(
    '(?P<adj>' + '|'.join(sorted(_I_ADJECTIVES, key=len, reverse=True)) + ')の'
    '(?P<noun>[\u4e00-\u9fff\u30a1-\u30fa\u30fc]{1,6})')


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

    match = _I_ADJ_NO_NOUN_ERROR.search(user_input)
    if match:
        adj, noun = match.group('adj'), match.group('noun')
        return (f'💡 Feedback:\n- ❌ "{adj}の{noun}" → ✅ "{adj}{noun}" '
                f'(い形容詞は「の」をつけずに、そのまま名詞につなぎます)')

    error = _desu_error(user_input)
    if error:
        wrong, right = error
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(動詞の丁寧形は「です」ではなく「ます」を使います)')

    return feedback
