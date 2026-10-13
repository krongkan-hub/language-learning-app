"""Verb forms glued to the wrong base: 行くたい, 降るたら, 聞くながら, 食べた前に,
帰ます, 見ります, 飲んて, 浴びって, 降りますと思います.

Each shape is regular morphology with one right answer, and every one was
called natural by the model on the held-out eval (issue #40,
dev/evals/eval_jalearner.py). Only verbs the tables list are recognised.

Only ever overturns a CLEAN verdict — a real model correction always wins.
"""
import re

from ..tables.japanese import _GODAN_VERBS, _I_ADJECTIVES, _ICHIDAN_VERBS
from ..verdict import is_clean_verdict
from .ja_verbs import (STEM_TO_DICT, VERB_CLASS, ba_form, dict_form_pattern,
                       masu_stem, nai_form, standalone, ta_form, te_form)

_DICT = dict_form_pattern()
_ADJ = '(?P<adj>' + '|'.join(sorted(_I_ADJECTIVES, key=len, reverse=True)) + ')'
_NOT_AFTER_KANJI = '(?<![\u4e00-\u9fff々])'

# 〜ば: not ばかり (食べるばかり, "does nothing but eat"), ばあい, or a
# kana-spelled noun after the verb (待つばしょ, 寝るばん).
_GLUED = (
    (re.compile(_DICT + 'たい'), lambda v: masu_stem(v) + 'たい',
     '「たい」は動詞の「ます」の形につけます'),
    (re.compile(_DICT + 'ながら'), lambda v: masu_stem(v) + 'ながら',
     '「ながら」は動詞の「ます」の形につけます'),
    (re.compile(_DICT + 'すぎ'), lambda v: masu_stem(v) + 'すぎ',
     '「すぎる」は動詞の「ます」の形につけます'),
    (re.compile(_DICT + 'たら'), lambda v: ta_form(v) + 'ら',
     '「たら」は動詞の「た」の形につけます'),
    (re.compile(_DICT + 'ば(?![かあっしん])'), ba_form,
     '「ば」の条件形は動詞の語尾を「え」の段に変えます'),
    (re.compile(_DICT + '(?:後|あと)(?=で|に)'), lambda v: ta_form(v) + '後',
     '「後で」の前の動詞は「た」の形にします'),
)

_KANJI_STEMS = sorted((s for s in STEM_TO_DICT if re.search('[\u4e00-\u9fff]', s)),
                      key=len, reverse=True)

# 水を飲みほしい for 飲みたい: ほしい wants a thing, たい wants to do. Only right
# after を, because a ます stem is often a noun too, and 休みほしい ("I want a
# day off") is casual and correct.
_STEM_HOSHII = re.compile(
    '(?<=を)(?P<stem>' + '|'.join(_KANJI_STEMS) + ')(?:ほしい|欲しい)')

_TA_BEFORE_MAE = {ta_form(v): v for v in VERB_CLASS}
_TA_MAE = re.compile(
    '(?P<verb>' + '|'.join(sorted(_TA_BEFORE_MAE, key=len, reverse=True)) + ')前に')

# The kana after すぎ come along (高いすぎます → 高すぎます), so the drill
# retypes a word rather than a stem.
_ADJ_GLUED = re.compile(_ADJ + '(?P<tail>れば|たら|すぎ)(?P<rest>[ぁ-ん]*)')
_ADJ_FIX = {'れば': 'ければ', 'たら': 'かったら', 'すぎ': 'すぎ'}

# 帰ます for 帰ります: a two-character godan verb in る or う, its kanji
# straight onto ます or て. Only that shape: 着ます is the ichidan 着る and
# correct, which is why the verbs in く, つ and the rest are not here — 待て
# and 持て are imperatives.
_SHORT_GODAN = {v[0]: v for v in _GODAN_VERBS
                if len(v) == 2 and v[-1] in 'るう' and '\u4e00' <= v[0] <= '\u9fff'}
_NO_OKURIGANA = re.compile(
    _NOT_AFTER_KANJI + '(?P<kanji>[' + ''.join(_SHORT_GODAN) + '])'
    '(?P<tail>ませんでした|ません|ました|ましょう|ます|て)(?P<q>か)?')

# 見ります for 見ます: an ichidan stem given a godan ending. Stems spelled in
# kana alone are out — い + ります is 要ります.
_ICHIDAN_STEMS = sorted({v[:-1] for v in _ICHIDAN_VERBS
                         if re.search('[\u4e00-\u9fff]', v[:-1])}, key=len, reverse=True)
_ICHIDAN_RI = re.compile(
    _NOT_AFTER_KANJI + '(?P<stem>' + '|'.join(_ICHIDAN_STEMS) + ')'
    'り(?P<tail>ませんでした|ません|ました|ましょう|ます)')

# 浴びって for 浴びて. An allowlist, because most ichidan stems are also
# nouns and casual って after a noun is correct: 疲れって取れない, 答えって何,
# 慣れって大事, 思い出って. The stem must follow a particle.
_TTE_STEMS = ('出かけ', '見つけ', '食べ', '起き', '浴び', '開け', '閉め', '調べ',
              '捨て', '見せ', '降り', '信じ', '見', '寝', '着')
_ICHIDAN_TTE = re.compile(
    '(?:(?<=[をがはもにでへと、])|^)(?P<stem>' + '|'.join(_TTE_STEMS) + ')って')

# 飲んて / 書いで / 泳いて: the 音便 is right and the voicing of て is not.
_N_VERBS = {v[0]: v for v in _GODAN_VERBS if len(v) == 2 and v[-1] in 'むぶぬ'}
_KU_VERBS = {v[0]: v for v in _GODAN_VERBS if len(v) == 2 and v[-1] == 'く' and v != '行く'}
# 急いて is 急く (せく), as in 急いては事を仕損じる.
_GU_VERBS = {v[0]: v for v in _GODAN_VERBS
             if len(v) == 2 and v[-1] == 'ぐ' and v != '急ぐ'}
_TE_VOICING = re.compile(
    _NOT_AFTER_KANJI + '(?:(?P<n>[' + ''.join(_N_VERBS) + '])んて'
    '|(?P<ku>[' + ''.join(_KU_VERBS) + '])いで'
    '|(?P<gu>[' + ''.join(_GU_VERBS) + '])いて)')

# 降りますと思います: a polite form inside と思う. 「」 before と is a quote and
# keeps its own form.
_POLITE_TO_OMOU = re.compile(
    '(?P<body>[^\\s、。「」『』！？!?]{1,12}?)'
    '(?P<end>ませんでした|ません|ました|ます|なかったです|ないです|でした|です)'
    '(?P<to>と思(?:います|いました|う|った|って))')

# 駅に着くと、電話してください: と states what always follows, so its main
# clause cannot be a request or an invitation — that is たら. Only when the
# request directly follows the comma: a から or ので in between makes the
# request a separate layer (暗くなると、危ないから気をつけてください).
_TO_REQUEST = re.compile(
    _DICT + 'と、(?P<seg>[^、。！？!?「」]*?)'
    '(?P<req>てください|でください|ましょう|ませんか)(?=[。！？!?]?$)')
_TO_REQUEST_BLOCK = ('から', 'ので', 'けど', 'のに', 'ても', 'でも')

# 昨日買いました本 for 買った本: a relative clause takes the plain form. Only
# verbs from the tables spelled with a kanji (so ございました, いただきました
# and the rest of business keigo never match), and never before a pronoun or
# time word, where the learner has more likely dropped a 。 (行きました今日は).
_REL_NOT_NOUN = ('私', '僕', '彼', '今', '明日', '昨日', '先生')
_REL_POLITE = re.compile(
    '(?:(?P<stem>' + '|'.join(_KANJI_STEMS) + ')ました'
    '|(?P<te>[\u4e00-\u9fff][ぁ-ん]{0,2}[てで])い(?P<te_end>ます|ました))'
    '(?P<noun>[\u4e00-\u9fff\u30a0-\u30ffー]{1,4})(?=[はがをにでも])')


def _rel_clause_error(text: str):
    for match in _REL_POLITE.finditer(text):
        noun = match.group('noun')
        if noun.startswith(_REL_NOT_NOUN):
            continue
        if text[:match.start()].endswith(('お', 'ご')):
            continue
        if match.group('stem'):
            plain = ta_form(STEM_TO_DICT[match.group('stem')])
        else:
            plain = match.group('te') + ('いる' if match.group('te_end') == 'ます' else 'いた')
        return (match.group(0), plain + noun,
                '名詞を修飾する動詞は「ます」ではなく普通形にします')
    return None


def _plain(body: str, end: str):
    """`body` + `end` in plain form, or None when the base cannot be read."""
    if end in ('ないです', 'なかったです'):
        return body + end[:-2]
    if end in ('です', 'でした'):
        if any(body.endswith(a) for a in _I_ADJECTIVES) or body.endswith(('ない', 'たい')):
            return body if end == 'です' else None
        if body.endswith('い'):
            return None          # きれい, 嫌い: a な-adjective or an unknown い-word
        return body + ('だ' if end == 'です' else 'だった')
    for i in range(len(body)):
        stem = body[i:]
        head = body[:i]
        verb = STEM_TO_DICT.get(stem)
        if stem == '降り' and head.endswith(('雨が', '雪が', '雨も', '雪も')):
            verb = '降る'        # 降り is 降る and 降りる; weather settles it
        if verb is None:
            continue
        if verb == 'する':
            if not head or not re.search('[\u4e00-\u9fff\u30a0-\u30ff]$', head):
                return None      # 少しますと… is not する
        elif not standalone(body, i, verb):
            return None
        plain = {'ます': verb, 'ません': nai_form(verb), 'ました': ta_form(verb),
                 'ませんでした': nai_form(verb)[:-1] + 'かった'}[end]
        return head + plain
    return None


def _bullet(wrong: str, right: str, reason: str) -> str:
    return f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" ({reason})'


def verb_form_error(text: str):
    """(wrong, right, reason) for the first glued verb form in `text`."""
    for pattern, fix, reason in _GLUED:
        for match in pattern.finditer(text):
            verb = match.group('verb')
            if not standalone(text, match.start(), verb):
                continue
            return match.group(0), fix(verb), reason

    match = _STEM_HOSHII.search(text)
    if match:
        stem = match.group('stem')
        return (match.group(0), stem + 'たい',
                '動作をしたいときは「ほしい」ではなく「たい」を使います')

    match = _TA_MAE.search(text)
    if match and standalone(text, match.start(), _TA_BEFORE_MAE[match.group('verb')]):
        verb = _TA_BEFORE_MAE[match.group('verb')]
        return match.group(0), verb + '前に', '「前に」の前の動詞は辞書形にします'

    match = _ADJ_GLUED.search(text)
    if match:
        adj, tail, rest = match.group('adj'), match.group('tail'), match.group('rest')
        if tail != 'すぎ':
            rest = ''
        return (adj + tail + rest, adj[:-1] + _ADJ_FIX[tail] + rest,
                'い形容詞は「い」を取ってから活用します')

    match = _NO_OKURIGANA.search(text)
    if match:
        verb = _SHORT_GODAN[match.group('kanji')]
        tail, q = match.group('tail'), match.group('q') or ''
        right = te_form(verb) if tail == 'て' else masu_stem(verb) + tail
        return (match.group(0), right + q,
                f'「{verb}」は五段動詞なので「{right}」になります')

    match = _ICHIDAN_RI.search(text)
    if match:
        stem, tail = match.group('stem'), match.group('tail')
        return (match.group(0), stem + tail,
                f'「{stem}る」は一段動詞なので「り」は入りません')

    match = _ICHIDAN_TTE.search(text)
    if match:
        stem = match.group('stem')
        return (match.group(0), stem + 'て',
                f'「{stem}る」は一段動詞なので、テ形は「{stem}て」です')

    match = _TE_VOICING.search(text)
    if match:
        if match.group('n'):
            verb = _N_VERBS[match.group('n')]
        elif match.group('ku'):
            verb = _KU_VERBS[match.group('ku')]
        else:
            verb = _GU_VERBS[match.group('gu')]
        return match.group(0), te_form(verb), f'「{verb}」のテ形は「{te_form(verb)}」です'

    for match in _TO_REQUEST.finditer(text):
        verb = match.group('verb')
        if standalone(text, match.start(), verb) and not any(
                b in match.group('seg') for b in _TO_REQUEST_BLOCK):
            return (verb + 'と', ta_form(verb) + 'ら',
                    '「と」の後には依頼や誘いの文を続けられないので「たら」を使います')

    error = _rel_clause_error(text)
    if error:
        return error

    for match in _POLITE_TO_OMOU.finditer(text):
        body, end = match.group('body'), match.group('end')
        plain = _plain(body, end)
        if plain:
            # Quote from the last particle on: 「雨が降りますと思います」 is
            # retyped as 「降ると思います」, not the whole sentence.
            cut = max(body.rfind(p) for p in 'はがをにで') + 1
            if cut and plain.startswith(body[:cut]):
                body, plain = body[cut:], plain[cut:]
            return (body + end + match.group('to'), plain + match.group('to'),
                    '「と思う」の前は普通形にします')
    return None


def apply_ja_verb_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a verb form glued to the wrong base."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    error = verb_form_error(user_input)
    return _bullet(*error) if error else feedback
