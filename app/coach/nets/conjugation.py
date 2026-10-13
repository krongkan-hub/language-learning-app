"""て-form 音便, い-adjective negatives, past, adverbial forms and + の.

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


# Issue #36: 頭が痛いの薬 came back clean with the fix under Level up, so it
# was never drilled. An い-adjective modifies a noun directly. の after an
# い-adjective is usually right, though — "the one(s)" (新しいの一つください,
# 安いの中から, おいしいの食べたい with を dropped) — so this fires only when
# what follows is plainly a noun: a kanji/katakana run that ends right before
# a particle or punctuation, never before okurigana (食べ, 見つけ). A single
# kanji may be a verb stem before に (見に行く), so it needs が/は/を/も or
# punctuation. Not before です: 悪いの私です is 悪いのは私です with は dropped.
# Numerals, 何, 中, 全部, 方, 他, 以外 and pronouns never fire.
_I_ADJ_NO_ERROR = re.compile(
    '(?P<adj>' + '|'.join(_I_ADJECTIVES) + ')の'
    '(?P<noun>(?![一二三四五六七八九十百千万何0-9０-９中全方他私僕俺彼誰]|以外|自分)'
    '[\u4e00-\u9fff\u30a0-\u30ff々]+)'
    '(?![\u4e00-\u9fff\u30a0-\u30ff々])'
    '(?P<next>が|は|を|も|に|で(?!す)|と|へ|や|から|まで|[。、！？!?」\\s]|$)')
_LONE_KANJI_NEXT = ('が', 'は', 'を', 'も', '。', '、', '！', '？', '!', '?', '」', '')


def _i_adj_no_error(text: str):
    """The first い-adjective + の + noun match in `text`, or None."""
    for match in _I_ADJ_NO_ERROR.finditer(text):
        noun = match.group('noun')
        lone_kanji = len(noun) == 1 and '\u4e00' <= noun <= '\u9fff'
        if not lone_kanji or match.group('next').strip() in _LONE_KANJI_NEXT:
            return match
    return None


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

    match = _i_adj_no_error(user_input)
    if match:
        adj, noun = match.group('adj'), match.group('noun')
        return (f'💡 Feedback:\n- ❌ "{adj}の{noun}" → ✅ "{adj}{noun}" '
                f'(い形容詞は「の」を使わずに直接名詞を修飾します)')

    error = _desu_error(user_input)
    if error:
        wrong, right = error
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(動詞の丁寧形は「です」ではなく「ます」を使います)')

    return feedback
