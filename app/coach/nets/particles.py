"""Case particles: を for に, に for で, and the partner particle.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
import re
from ..verdict import is_clean_verdict
from ..tables.japanese import (_BARE_TIME_WORDS, _DE_ACTION_STEMS,
                               _DE_ACTION_SURU, _JA_PERSON_NOUNS,
                               _JA_PLACE_NOUNS, _NI_PARTNER_SURU,
                               _NI_TARGET_VERBS, _TIME_NI_OK, _TO_PARTNER_SURU)
from .ja_text import _CLAUSE_END, _quote_through


_NI_PARTICLE_ERROR = re.compile(
    '(?P<noun>[^\\s、。「」『』！？!?・をはがにでともへや]{1,12})を'
    '(?P<stem>会[いうっえお]'
    '|乗(?:る|った|って|ります|りました|りません|りましょう|りたい|らない|れば|ろう))'
)


_SURU_TAIL = ('(?:し(?:ました|ませんでした|ましょう|まして|ません|ます|たい|たら|'
              'なかった|ない|よう|た|て)?|する|すれば|される)')


_NI_PARTNER_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_JA_PERSON_NOUNS) + ')を'
    '(?P<verb>' + '|'.join(_NI_PARTNER_SURU) + ')(?P<tail>' + _SURU_TAIL + ')')


_TO_PARTNER_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_JA_PERSON_NOUNS) + ')に'
    '(?P<verb>' + '|'.join(_TO_PARTNER_SURU) + ')(?P<tail>' + _SURU_TAIL + ')')


_NI_RESIDENCE_ERROR = re.compile(
    '(?P<noun>[一-龥ァ-ヶーA-Za-z]{1,12})で'
    '(?P<stem>住(?:んでいます|んでいる|んでます|んでいた|んだ|んで|みます|みました|む|み)'
    '|勤め(?:ています|ている|ます|ました|て|る))')


_DE_ACTION_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_JA_PLACE_NOUNS) + ')に'
    '(?P<stem>(?:' + '|'.join(_DE_ACTION_SURU) + ')' + _SURU_TAIL
    + '|' + '|'.join(_DE_ACTION_STEMS) + ')')


_BARE_TIME_NI_ERROR = re.compile(
    '(?P<word>' + '|'.join(sorted(_BARE_TIME_WORDS, key=len, reverse=True)) + ')'
    'に(?!' + '|'.join(_TIME_NI_OK) + ')(?=[^\\s])')


# The object of a request: 「値段が教えてください」 → 「値段を教えてください」.
# Only transitive verbs, and only a request ending, where が cannot be the
# intended subject marker: the learner is asking someone to act ON the noun.
# Playtest 2026-09-27: the model called this sentence natural.
_GA_REQUEST_VERBS = ('教えて', '見せて', '送って', '貸して', '書いて', '持ってきて', '呼んで',
                     '包んで', '取って', '変えて', '直して', '確認して', '説明して', '用意して',
                     '予約して', '交換して', '調べて', '紹介して')
_GA_REQUEST_ERROR = re.compile(
    '(?P<noun>[^\\s、。「」『』！？!?・をはがにでともへや]{1,12})が'
    '(?P<verb>' + '|'.join(_GA_REQUEST_VERBS) + ')'
    '(?P<tail>ください|くださいませんか|もらえますか|もらえませんか|いただけますか|いただけませんか)')


def _clause_or_pair(user_input: str, start: int, word: str) -> tuple:
    """Quote the learner's clause when it is short enough to retype, else the
    bare particle pair.

    Deleting a particle leaves nothing to quote: 「先週に」 → 「先週」 names the
    fix but the repeat drill asks the learner to type the ✅ side back, and a
    two-character fragment is not a sentence. Quoting the clause gives them
    「先週京都へ行きました」, which is what they meant to write. The length cap
    is what keeps a long sentence from being dumped into a bullet.
    """
    end = len(user_input)
    for stop in _CLAUSE_END:
        cut = user_input.find(stop, start)
        if cut != -1:
            end = min(end, cut)
    clause = user_input[start:end]
    if len(clause) <= 14:
        return clause, clause.replace(word + 'に', word, 1)
    return f'{word}に', word


def apply_particle_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a particle the verb, not the meaning, fixes.

    Five shapes, all of them classes the model calls natural: を on a に-taking
    verb's target (会う/乗る, and the suru-verbs whose partner is a person),
    に where a reciprocal verb needs と, に where an action at a place needs で,
    and で where 住む/勤める need に.
    """
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    match = _NI_PARTICLE_ERROR.search(user_input)
    if match:
        noun = match.group('noun')
        reason = _NI_TARGET_VERBS[match.group('stem')[0]]
        return f'💡 Feedback:\n- ❌ "{noun}を" → ✅ "{noun}に" ({reason})'

    for pattern, table, wrong_particle, right_particle in (
        (_NI_PARTNER_ERROR, _NI_PARTNER_SURU, 'を', 'に'),
        (_TO_PARTNER_ERROR, _TO_PARTNER_SURU, 'に', 'と'),
    ):
        match = pattern.search(user_input)
        if not match:
            continue
        noun, verb, tail = match.group('noun'), match.group('verb'), match.group('tail')
        wrong, right = _quote_through(
            user_input, match, f'{noun}{right_particle}{verb}{tail}')
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'({table[verb]})')

    match = _GA_REQUEST_ERROR.search(user_input)
    if match:
        noun, verb, tail = match.group('noun'), match.group('verb'), match.group('tail')
        wrong, right = _quote_through(user_input, match, f'{noun}を{verb}{tail}')
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(頼んでいる動作の対象は「を」で示します)')

    match = _DE_ACTION_ERROR.search(user_input)
    if match:
        noun, stem = match.group('noun'), match.group('stem')
        wrong, right = _quote_through(user_input, match, f'{noun}で{stem}')
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(動作を行う場所は「で」で示します)')

    match = _NI_RESIDENCE_ERROR.search(user_input)
    if match:
        noun, stem = match.group('noun'), match.group('stem')
        wrong, right = _quote_through(user_input, match, f'{noun}に{stem}')
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(「住む」「勤める」の場所は「に」で示します)')

    # Last, so the five shapes above keep priority on a sentence that carries
    # both: 「昨日に友達を会いました」 should be told about the を, which is the
    # error the learner is more likely to repeat.
    match = _BARE_TIME_NI_ERROR.search(user_input)
    if match:
        word = match.group('word')
        wrong, right = _clause_or_pair(user_input, match.start(), word)
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(「{word}」は時を表す副詞なので「に」は付けません)')

    return feedback
