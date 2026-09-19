"""Deterministic nets for Japanese. Each only ever overturns a CLEAN verdict.

Why nets and not prompt rules: see BACKLOG OPEN-07 and OPEN-10. The model
does not know some of these are errors, so no wording reaches them.
"""
import re

from ..verdict import is_clean_verdict


_NI_TARGET_VERBS = {
    '会': '「会う」の相手は「に」か「と」で示します',
    '乗': '「乗る」の行き先は「に」で示します',
}
# The noun class excludes particles so 「久しぶりに友達を会う」 quotes 友達, not
# 久しぶりに友達. Requiring を to touch the verb keeps causatives, where を is
# correct, out: 「友達を医者に会わせた」 has a noun after を, and the わ stems of
# 会わせる/乗せる are outside the stem classes.
#
# 乗 is spelled out as whole inflections of plain 乗る rather than as a stem
# class, because 乗り/乗っ also open every compound built on 乗る, and those
# compounds take を: 電車を乗り換える, 駅を乗り過ごす, 飛行機を乗っ取る,
# 困難を乗り越える. Matching a stem class flagged all of those as errors. An
# inflection list also survives kana spelling — 「電車を乗りかえます」 is left
# alone, where a "no kanji after the stem" rule would still fire on it. The
# cost is missing を on inflections nobody listed here; a miss is recoverable,
# telling a learner that correct Japanese is wrong is not.
_NI_PARTICLE_ERROR = re.compile(
    '(?P<noun>[^\\s、。「」『』！？!?・をはがにでともへや]{1,12})を'
    '(?P<stem>会[いうっえお]'
    '|乗(?:る|った|って|ります|りました|りません|りましょう|りたい|らない|れば|ろう))'
)


# Transitive/intransitive pairs, the largest net-able slice of OPEN-10: the
# coach scores 0/3 on them, answering "Perfectly natural!" to 電気をつきました,
# 会議が始めました and 窓が閉めました. The pairs are a closed, enumerable set,
# which is what makes a deterministic net possible here where it is not for
# particle choice or register.
#
# Stems are listed as the ren'youkei (ます-stem) plus the dictionary form,
# because those two cover every inflection the learner is likely to write and
# an inflection list is what kept the 乗る net out of trouble.
_TI_PAIRS = (
    # (intransitive stems, transitive stems, intransitive citation, transitive citation)
    (('つき', 'つく'), ('つけ', 'つける'), 'つきます', 'つけます'),
    (('閉まり', '閉まる'), ('閉め', '閉める'), '閉まります', '閉めます'),
    (('始まり', '始まる'), ('始め', '始める'), '始まります', '始めます'),
    (('開き', '開く'), ('開け', '開ける'), '開きます', '開けます'),
    (('消え', '消える'), ('消し', '消す'), '消えます', '消します'),
    (('入り', '入る'), ('入れ', '入れる'), '入ります', '入れます'),
    (('止まり', '止まる'), ('止め', '止める'), '止まります', '止めます'),
    (('変わり', '変わる'), ('変え', '変える'), '変わります', '変えます'),
    (('決まり', '決まる'), ('決め', '決める'), '決まります', '決めます'),
    (('壊れ', '壊れる'), ('壊し', '壊す'), '壊れます', '壊します'),
    (('届き', '届く'), ('届け', '届ける'), '届きます', '届けます'),
    (('落ち', '落ちる'), ('落とし', '落とす'), '落ちます', '落とします'),
)

# が + a transitive verb is NOT an error in general — が marks the agent, so
# 「私が閉めました」 is correct. It is only wrong when the noun is the thing
# being acted on, which needs semantics we do not have. So rule B fires only
# for an enumerated set of inanimate patients. Anything not listed, including
# every person, is left to the model.
_TI_PATIENTS = (
    '窓', 'ドア', '扉', '電気', '明かり', '照明', '電源', 'テレビ', 'エアコン',
    '会議', '授業', '試合', '店', '番組', '映画', 'パーティー', '荷物', '予約',
    '火', 'お湯', 'music', '音楽', 'ドアベル', 'カーテン',
)

# られ/れ mark passive and potential, where the transitive stem is correct:
# 「窓が閉められました」 is good Japanese. Never fire in front of them.
_TI_SUFFIX_BLOCK = ('られ', 'れる', 'れま', 'れた')


def _ti_lookup(text: str, stems, offset: int):
    """Match a stem sitting IMMEDIATELY at `offset`, never merely later in the
    sentence. Searching ahead produced false positives on correct multi-clause
    Japanese — 「電気をつけて、窓が閉まりました。」 matched the intransitive 閉まり
    from the second clause against the を of the first and "corrected" it. The
    error shape this net targets is adjacent by construction (電気を+つきました),
    so adjacency costs nothing and removes the whole class."""
    for stem in stems:
        if text.startswith(stem, offset):
            after = text[offset + len(stem): offset + len(stem) + 2]
            if not any(after.startswith(b) for b in _TI_SUFFIX_BLOCK):
                return stem
    return None


# Counters, the other net-able slice of OPEN-10 (currently 1/3). Japanese
# picks a counter from the SHAPE of the thing counted, so noun->counter is a
# closed mapping a rule can check where particle choice and register cannot be.
#
# Deliberately a DENY list, not an allow list. つ and 個 are near-universal
# fallbacks and many nouns take several counters legitimately (水 is 本 by the
# bottle and 杯 by the glass), so enumerating what is allowed would over-fire
# on correct Japanese. Only pairings that are unambiguously wrong are listed,
# and everything unlisted is left to the model.
_COUNTER_RULES = (
    # (nouns, counters that are wrong for them, suggested counters, reason)
    (('水', 'お茶', 'コーヒー', 'ジュース', 'ビール', 'ワイン', '牛乳'),
     ('枚', '冊', '匹', '台', '本人'),
     ('本', '杯'), '液体は瓶なら「本」、グラスなら「杯」で数えます'),
    (('切符', 'チケット', '写真', '紙', 'カード', '切手', 'シャツ', 'お皿'),
     ('本', '冊', '匹', '台', '杯'),
     ('枚',), '薄くて平らなものは「枚」で数えます'),
    (('りんご', 'みかん', '卵', 'たまご', 'ボール', '石鹸'),
     ('本', '枚', '冊', '匹', '台', '杯'),
     ('つ', '個'), '丸くて小さいものは「つ」か「個」で数えます'),
    (('雑誌', 'ノート', '辞書', '教科書'),
     ('本', '枚', '匹', '台', '杯'),
     ('冊',), '本や雑誌は「冊」で数えます'),
)
# Numerals that can precede a counter, kanji and arabic.
_COUNT_NUM = '[0-9０-９一二三四五六七八九十百千]+'


# --- OPEN-39, option A: catch an English verb form the coach stayed silent on.
#
# Scoped to three shapes with a hard edge, because a net that misfires produces
# exactly the over-correction this project treats as its worst failure. Each
# needs a marker that cannot be anything else:
#   he/she/it + "don't"            — "don't" after those three is never right
#   did / didn't + a past form     — "did" already carries the tense
#   a past-time phrase + a present verb from a CLOSED list
#
# The closed list is the whole safety argument for the third shape. Detecting
# "the verb" in arbitrary English needs a POS tagger this project does not
# have, and guessing produces "corrections" to correct sentences. A list of
# 40 common verbs corrects fewer sentences and never invents an error.


def apply_counter_net(feedback: str, user_input: str, language: str) -> str:
    """Catch a counter that does not match the shape of the noun counted.
    Only ever overturns a clean verdict."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    for nouns, wrong_counters, suggested, reason in _COUNTER_RULES:
        for noun in nouns:
            for wrong in wrong_counters:
                # The noun and its count sit adjacent in the error shape
                # (水を三枚), the same adjacency that kept the transitivity net
                # from reaching across clauses.
                pattern = re.escape(noun) + r'を(' + _COUNT_NUM + r')' + re.escape(wrong)
                match = re.search(pattern, user_input)
                if not match:
                    continue
                number = match.group(1)
                fixes = '」か「'.join(f'{number}{s}' for s in suggested)
                return (f'💡 Feedback:\n- ❌ "{number}{wrong}" → ✅ '
                        f'"{number}{suggested[0]}" '
                        f'({reason}。「{fixes}」と言います)')
    return feedback


def _ti_inflect(text: str, offset: int, hit: str, target_stems, wrong_cite: str,
                right_cite: str):
    """Quote the learner's own inflection back, not a dictionary form.

    The learner writes 「電気をつきました」; quoting 「をつきます → をつけます」 at
    them is a citation form they did not use and cannot copy. Splicing the
    correct stem onto their own ending gives 「をつきました → をつけました」, which
    is the sentence they meant and — since the repeat drill asks them to retype
    the ✅ text — the thing they should be practising.

    Falls back to the citation pair when the ending cannot be read, so a shape
    this does not understand degrades to the old behaviour rather than
    producing something wrong.
    """
    ending = ''
    for stop in ('。', '、', '！', '？', '\n'):
        cut = text.find(stop, offset + len(hit))
        if cut != -1:
            ending = text[offset + len(hit):cut]
            break
    else:
        ending = text[offset + len(hit):]
    if not ending or len(ending) > 8:
        return wrong_cite, right_cite
    # The ren'youkei stem is listed first in each tuple and is the one an
    # ending attaches to; the dictionary form takes no ending.
    replacement = target_stems[0]
    return f'{hit}{ending}', f'{replacement}{ending}'


def apply_transitivity_net(feedback: str, user_input: str, language: str) -> str:
    """Catch を+intransitive and inanimate-が+transitive, the two shapes the
    model calls natural. Only ever overturns a clean verdict."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    for intrans, trans, intrans_cite, trans_cite in _TI_PAIRS:
        # Rule A: を + intransitive. Unambiguous — an intransitive verb takes no
        # object. (Motion verbs take を for a path, but none are in this table.)
        idx = user_input.find('を')
        if idx != -1:
            hit = _ti_lookup(user_input, intrans, idx + 1)
            if hit:
                wrong, right = _ti_inflect(user_input, idx + 1, hit, trans,
                                           intrans_cite, trans_cite)
                return (f'💡 Feedback:\n- ❌ "を{wrong}" → ✅ "を{right}" '
                        f'(「を」を使うときは他動詞の「{right}」になります)')

        # Rule B: inanimate patient + が + transitive.
        for patient in _TI_PATIENTS:
            marker = patient + 'が'
            pos = user_input.find(marker)
            if pos == -1:
                continue
            hit = _ti_lookup(user_input, trans, pos + len(marker))
            if hit:
                wrong, right = _ti_inflect(user_input, pos + len(marker), hit,
                                           intrans, trans_cite, intrans_cite)
                return (f'💡 Feedback:\n- ❌ "{patient}が{wrong}" → ✅ '
                        f'"{patient}が{right}" '
                        f'(「{patient}」が主語のときは自動詞の「{right}」を使います)')
    return feedback


# People. Enumerated for the same reason _TI_PATIENTS enumerates inanimate
# patients: the rules below turn on whether the noun is the verb's HUMAN
# partner, and nothing in the text tells us that. 「意味を質問しました」 is
# correct Japanese — を marks the content questioned — so a rule keyed on the
# verb alone would flag it. Keyed on a person, 「先生を質問しました」 is
# unambiguous. Anything not listed is left to the model.
_JA_PERSON_NOUNS = (
    '先生', '友達', '友だち', '母', '父', 'お母さん', 'お父さん', '兄', '姉',
    '弟', '妹', '両親', '家族', '彼', '彼女', '上司', '部長', '課長', '社長',
    '同僚', '先輩', '後輩', '店員', '医者', '看護師', 'お客さん', 'お客様',
    '担当者', '日本人', '外国人', '子供', '子ども', '息子', '娘', '奥さん',
    'ご主人', '主人', '妻', '夫', '友人', '知り合い', '警察官', '運転手',
)

# Suru-verbs whose human partner is marked に, never を.
_NI_PARTNER_SURU = {
    '質問': '「質問する」相手は「に」で示します',
    '電話': '「電話する」相手は「に」で示します',
    '連絡': '「連絡する」相手は「に」で示します',
    '相談': '「相談する」相手は「に」で示します',
    '挨拶': '「挨拶する」相手は「に」で示します',
    'あいさつ': '「あいさつする」相手は「に」で示します',
    '返事': '「返事する」相手は「に」で示します',
    '報告': '「報告する」相手は「に」で示します',
}

# Suru-verbs whose human partner is marked と, never に — a reciprocal action
# needs a co-participant, not a target.
_TO_PARTNER_SURU = {
    '結婚': '「結婚する」相手は「と」で示します',
    '離婚': '「離婚する」相手は「と」で示します',
    '喧嘩': '「喧嘩する」相手は「と」で示します',
    'けんか': '「けんかする」相手は「と」で示します',
    '約束': '「約束する」相手は「と」で示します',
}

# The suru ending is REQUIRED, not optional: it is what keeps the noun reading
# of these words out. 「彼女に結婚を申し込みました」 puts 結婚 straight after に
# and is correct; demanding し/する behind it leaves that sentence alone.
_SURU_TAIL = ('(?:し(?:ました|ませんでした|ましょう|まして|ません|ます|たい|たら|'
              'なかった|ない|よう|た|て)?|する|すれば|される)')

_NI_PARTNER_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_JA_PERSON_NOUNS) + ')を'
    '(?P<verb>' + '|'.join(_NI_PARTNER_SURU) + ')(?P<tail>' + _SURU_TAIL + ')')

_TO_PARTNER_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_JA_PERSON_NOUNS) + ')に'
    '(?P<verb>' + '|'.join(_TO_PARTNER_SURU) + ')(?P<tail>' + _SURU_TAIL + ')')

# 住む and 勤める locate a person rather than an action, so they take に. 「東京
# で住んでいます」 is wrong whatever the place is, which is why this rule needs
# no place list — unlike the で rule below, where the verb decides nothing.
# 住 must be followed by its own okurigana so 住宅/住所 do not match.
# The noun is a run of kanji/katakana/latin rather than "anything but a
# particle": a hiragana-tolerant class swallowed 「三年前から東京」 whole and
# quoted the adverbial back at the learner along with the fix.
_NI_RESIDENCE_ERROR = re.compile(
    '(?P<noun>[一-龥ァ-ヶーA-Za-z]{1,12})で'
    '(?P<stem>住(?:んでいます|んでいる|んでます|んでいた|んだ|んで|みます|みました|む|み)'
    '|勤め(?:ています|ている|ます|ました|て|る))')

# Places. Needed here because the verb cannot settle this one: 図書館に行く is
# correct and 図書館に勉強する is not, so the rule has to see both a place and
# an action performed there.
_JA_PLACE_NOUNS = (
    '図書館', '図書室', '学校', '大学', '教室', '会社', '事務所', '公園',
    'レストラン', 'カフェ', '喫茶店', '食堂', '空港', '病院', '銀行',
    '郵便局', '本屋', 'スーパー', 'コンビニ', 'ホテル', '台所', '教会',
    '工場', '会議室', '体育館', 'プール', '図書館前', '公民館', '自習室',
)

# Verbs naming an action PERFORMED at a place, which takes で. Existence
# (いる/ある/住む) and arrival (行く/来る/着く/入る) take に and are absent by
# construction. Finite and te- forms are listed rather than bare ren'youkei
# because a bare stem opens compounds that take に legitimately: 買い would
# match 「店に買い物に行きました」, where に is the destination of 行く.
_DE_ACTION_SURU = ('勉強', '練習', '仕事', '食事', '会議', '掃除')
_DE_ACTION_STEMS = (
    '働きました', '働きます', '働いて', '働き', '働く',
    '食べました', '食べます', '食べた', '食べて', '食べる',
    '飲みました', '飲みます', '飲んだ', '飲んで', '飲む',
    '読みました', '読みます', '読んだ', '読んで', '読む',
    '書きました', '書きます', '書いた', '書いて', '書く',
    '買いました', '買います', '買った', '買って', '買う',
    '待ちました', '待ちます', '待った', '待って', '待つ',
    '遊びました', '遊びます', '遊んだ', '遊んで', '遊ぶ',
)

_DE_ACTION_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_JA_PLACE_NOUNS) + ')に'
    '(?P<stem>(?:' + '|'.join(_DE_ACTION_SURU) + ')' + _SURU_TAIL
    + '|' + '|'.join(_DE_ACTION_STEMS) + ')')

# Time words that are already adverbs and attach to the verb with no particle
# at all. 三時に and 月曜日に take に because they name a point on a clock or a
# calendar; these name a point relative to NOW and never do.
#
# 0/10 on the recall probe, and here the model DOES know — asked plainly with
# no coach prompt it called 6/6 samples wrong and gave the right fix 6/6. This
# is OPEN-39's world, so a COACH_SYS carve-out could in principle reach it;
# the net is chosen because it is free and deterministic and the prompt is not.
_BARE_TIME_WORDS = (
    '今日', 'きょう', '明日', 'あした', 'あす', '昨日', 'きのう',
    '今朝', 'けさ', '今晩', '今夜', '毎日', '毎朝', '毎晩', '毎週',
    '毎月', '毎年', '今週', '来週', '先週', '今月', '来月', '先月',
    '今年', '来年', '去年', 'おととい', '一昨日', 'あさって', '明後日',
)
# に after one of those IS correct in a whole family of fixed frames, and they
# are ordinary sentences rather than edge cases: 明日にします (I'll make it
# tomorrow), 明日には終わります (by tomorrow), 去年に比べて, 来年に向けて,
# 明日に間に合う, 来週にかけて, 明日に延期します, 来月に決めます. Every one of
# them continues with a word blocked here, and this list is the rule's whole
# safety argument — the same shape as the 乗る inflection list in OPEN-07,
# where a stem class "corrected" four kinds of correct Japanese.
_TIME_NI_OK = ('は', 'も', 'で', 'の', 'か', 'し', '近', '比', '入', '至', '向',
               '続', '備', '関', '対', 'わた', '渡', 'つい', '付', '限', '当',
               'あた', 'なっ', 'なり', 'なる', '変', '及', '間', '引', '延',
               '予', '持', '決', '送', '繰', '回', '合', '先立')
_BARE_TIME_NI_ERROR = re.compile(
    '(?P<word>' + '|'.join(sorted(_BARE_TIME_WORDS, key=len, reverse=True)) + ')'
    'に(?!' + '|'.join(_TIME_NI_OK) + ')(?=[^\\s])')
_CLAUSE_END = '。、！？!?\n'


def _quote_through(user_input: str, match, replacement: str) -> tuple:
    """Quote the learner's own words from the noun through the verb.

    Quoting the bare particle (「先生を」 → 「先生に」) names the fix but not the
    sentence: the repeat drill asks the learner to retype the ✅ text, and a
    two-character fragment is not something to retype. Spanning the verb gives
    them the clause they actually meant.
    """
    return user_input[match.start():match.end()], replacement


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


# Godan verbs whose te-form takes an euphonic change (音便). A learner who
# forms the te-form by analogy with ichidan verbs (食べ→食べて) writes 読みて for
# 読んで, and the model calls it natural.
#
# す-godan verbs are absent BY CONSTRUCTION, not by oversight: for those the
# ren'youkei + て IS the correct te-form (話し→話して, 出し→出して), so listing
# one would flag correct Japanese as an error.
# Values are the whole correct te-form, not a stem: む/ぶ/ぬ take んで and く
# takes いて, but ぐ takes い*で* — 泳ぎて is 泳いで, not 泳いて — so deriving the
# ending from the stem's last kana would get the ぐ verbs wrong.
_TE_ONBIN = {
    '読み': '読んで', '飲み': '飲んで', '休み': '休んで', '進み': '進んで',
    '住み': '住んで', '呼び': '呼んで', '遊び': '遊んで', '運び': '運んで',
    '選び': '選んで', '喜び': '喜んで', '死に': '死んで',
    '書き': '書いて', '聞き': '聞いて', '歩き': '歩いて', '働き': '働いて',
    '置き': '置いて',
    '泳ぎ': '泳いで', '急ぎ': '急いで', '脱ぎ': '脱いで',
    '買い': '買って', '会い': '会って', '使い': '使って', '払い': '払って',
    '習い': '習って',
    '待ち': '待って', '持ち': '持って', '立ち': '立って', '勝ち': '勝って',
    '取り': '取って', '作り': '作って', '売り': '売って', '帰り': '帰って',
    '走り': '走って', '座り': '座って', '送り': '送って', '降り': '降って',
    '曲がり': '曲がって', '行き': '行って',
}
_TE_ONBIN_ERROR = re.compile('(' + '|'.join(_TE_ONBIN) + ')て')

# たい is an i-adjective, so its past is たかった — not たいでした, which is the
# shape a learner produces by treating たい as a noun. ない behaves the same way.
# Both are safe without any word list: no na-adjective and no noun ends in
# たい or ない, so the ending alone settles it.
_I_ADJ_PAST_ERROR = re.compile('(?P<stem>[^\\s、。「」『』！？!?]{0,10}?)(?P<adj>たい|ない)でした')

# The wider i-adjective class DOES need a list, because な-adjectives ending in
# the same kana (きれいでした, 嫌いでした, 有名でした) are correct and are
# indistinguishable from the ending alone.
_I_ADJECTIVES = (
    '楽しい', '嬉しい', 'うれしい', '悲しい', '面白い', 'おもしろい', '忙しい',
    '寒い', '暑い', '熱い', '冷たい', '高い', '安い', '良い', 'よい', '悪い',
    '難しい', '易しい', '新しい', '古い', '大きい', '小さい', '近い', '遠い',
    '早い', '速い', '遅い', '強い', '弱い', '長い', '短い', '広い', '狭い',
    '多い', '少ない', '怖い', '痛い', 'かわいい', 'すごい', '欲しい', 'ほしい',
    'おいしい', '美味しい', '美しい', '優しい', '厳しい', '眠い',
)
_I_ADJ_LIST_ERROR = re.compile('(?P<adj>' + '|'.join(_I_ADJECTIVES) + ')でした')

# --- OPEN-10, the Japanese recall gap, measured by scripts/eval_jarecall.py.
#
# Six classes no fixture and no net covered read 20/60 twice, case for case
# identical across two runs, with the coach returning a clean verdict on every
# single miss. The same probe's plain-question arm (MODE=plain) splits those
# six in two, and the split decides the lever:
#
#   the model KNOWS       na-adj 6/6, adverb 6/6, time-ni 6/6 called wrong
#                         with the right fix, asked with no coach prompt
#   the model does NOT    exist 3/9, de-exist 0/3, i-adj-neg 0/6 right fixes
#
# So Japanese is BOTH of the worlds this project has measured before, not one:
# OPEN-39's (knowledge the prompt is not using) for three classes and OPEN-07's
# (no knowledge to use) for the other three. Nets are written for all six
# anyway, because they are deterministic and because COACH_SYS has moved
# unrelated cases every time it was edited here — OPEN-10 records one deleted
# worked example costing 12 iterations across four cases it was not aimed at.

# い-adjectives negated as though they were な-adjectives. 「高くないです」 is
# the negative; 「高いじゃないです」 is what a learner writes by reaching for the
# な-adjective pattern, which for きれい IS correct.
#
# This is the class where the model is not merely silent but actively wrong:
# asked plainly it "fixed" 「この店は高いじゃないです」 to 「この店は高いですね」,
# which says the opposite of what the learner meant. 0/6 right fixes.
_I_ADJ_JANAI_TAIL = {
    'ないです': 'くないです',
    'ないんです': 'くないんです',
    'なかったです': 'くなかったです',
    'ありません': 'くありません',
    'ありませんでした': 'くありませんでした',
}
# か and ね are the whole safety argument for this rule, not a nicety.
# 「高いじゃないですか」 is ordinary colloquial Japanese for "isn't it
# expensive?" — the OPPOSITE of the 「高くないです」 this rule would otherwise
# produce, so firing on it would not just over-correct, it would invert the
# learner's meaning.
_I_ADJ_JANAI_ERROR = re.compile(
    '(?P<adj>' + '|'.join(_I_ADJECTIVES) + ')じゃ'
    '(?P<tail>' + '|'.join(sorted(_I_ADJ_JANAI_TAIL, key=len, reverse=True))
    + ')(?![かね])')

# An い-adjective modifying a VERB takes the く form: 早く歩く, not 早い歩く.
# The verb list is closed for exactly the reason OPEN-39's was: an
# い-adjective in front of a NOUN is correct (早い電車, 面白い話), and without a
# POS tagger the only safe way to know the next word is a verb is to enumerate
# the verbs. Finite and te-forms only — a bare ren'youkei would match the noun
# half of 安い飲み物 and 高い買い物.
#
# 話す is deliberately absent: 「面白い話します」 reads as 面白い話 + します, a
# correct sentence, and no ending can tell that apart from 面白く話します.
_ADVERBIAL_VERBS = (
    '歩いて', '歩きます', '歩く', '書いて', '書きます', '書く',
    '走って', '走ります', '走る', '食べて', '食べます', '食べる',
    '飲んで', '飲みます', '飲む', '起きて', '起きます', '起きる',
    '寝て', '寝ます', '寝る', '作って', '作ります', '作る',
    'なります', 'なって', 'なりました', 'なる', '切って', '切ります',
    '読んで', '読みます', '読む', '買って', '買います', '買う',
    '洗って', '洗います', '開けて', '開けます', '閉めて', '閉めます',
)
_I_ADJ_ADVERB_ERROR = re.compile(
    '(?P<adj>' + '|'.join(_I_ADJECTIVES) + ')'
    '(?P<verb>' + '|'.join(sorted(_ADVERBIAL_VERBS, key=len, reverse=True)) + ')')


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

    return feedback


# Address terms that name someone senior to the learner. A sentence that opens
# by calling one of these and then drops into plain form is a register clash
# the learner can see and fix — and, unlike the situational rules, it needs no
# scenario: the learner named the listener themselves.
_JA_SUPERIOR_ADDRESS = (
    '先生', '部長', '課長', '社長', '店長', '館長', '主任', '先輩',
    'お客様', 'お客さん', '社長さん', '部長さん',
)
_SUPERIOR_VOCATIVE = re.compile(
    '^(?:' + '|'.join(_JA_SUPERIOR_ADDRESS) + ')[、,]')

# Pronouns a learner should not aim at someone senior.
_CASUAL_PRONOUNS = (('俺', '私'), ('おれ', '私'), ('お前', 'あなた'), ('おまえ', 'あなた'))

# Politeness anywhere in the sentence means the register is already chosen, so
# the plain-form rule below must not fire. Checked over the whole utterance
# rather than the ending, because 「先生、明日来ますか」 is polite at the end and
# 「先生、明日来るか、教えてください」 is polite only at the end.
_JA_POLITE_MARKERS = ('ます', 'です', 'ください', 'ましょう', 'でしょう', 'ございま')

# Plain sentence-final forms and their polite twins. Enumerated, because ichidan
# and godan take different endings and the irregulars (来る/する) take neither.
_PLAIN_TO_POLITE = {
    '来る': '来ます', 'くる': 'きます', 'する': 'します', 'ある': 'あります',
    'いる': 'います', '行く': '行きます', '見る': '見ます', '食べる': '食べます',
    '飲む': '飲みます', '書く': '書きます', '読む': '読みます', '買う': '買います',
    '待つ': '待ちます', '帰る': '帰ります', '言う': '言います', '聞く': '聞きます',
    '出る': '出ます', '入る': '入ります', '休む': '休みます', '使う': '使います',
    '持つ': '持ちます', '取る': '取ります', '作る': '作ります', '分かる': '分かります',
    '教える': '教えます', '始める': '始めます', '終わる': '終わります',
}
_PLAIN_ENDING = re.compile(
    '(?P<verb>' + '|'.join(_PLAIN_TO_POLITE) + ')(?P<q>か)?[。．.！？!?]?\\s*$')


def apply_register_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict when the learner addresses someone senior and
    then speaks to them in plain form or with a casual pronoun.

    Narrower than the situational rules on purpose: it fires only when the
    learner's own sentence names the listener, so it needs no scenario and
    cannot mistake an equal for a superior.
    """
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    if not _SUPERIOR_VOCATIVE.match(user_input.strip()):
        return feedback

    for casual, polite in _CASUAL_PRONOUNS:
        if casual in user_input:
            return (f'💡 Feedback:\n- ❌ "{casual}" → ✅ "{polite}" '
                    f'(目上の人には「{polite}」を使います)')

    if any(marker in user_input for marker in _JA_POLITE_MARKERS):
        return feedback
    match = _PLAIN_ENDING.search(user_input.strip())
    if match:
        verb, question = match.group('verb'), match.group('q') or ''
        polite = _PLAIN_TO_POLITE[verb]
        return (f'💡 Feedback:\n- ❌ "{verb}{question}" → ✅ "{polite}{question}" '
                f'(目上の人には「ます」の形で話します)')

    return feedback


# A degree adverb sitting AFTER the predicate is stranded — Japanese puts it in
# front. The predicate ending is what makes this safe to check: nothing correct
# follows です/ます with a bare degree adverb and no comma.
_DEGREE_ADVERBS = ('とても', 'すごく', '本当に', 'ほんとうに', 'かなり', '非常に',
                   'ちょっと', '少し', 'たくさん', 'よく')
# `pred` excludes the case particles as well as the sentence punctuation, so the
# quote starts at the predicate and not at the top of the clause: without that
# 「私はコーヒーが好きですとても」 was quoted back whole and "fixed" to
# 「とても私はコーヒーが好きです」, which moves the adverb to the wrong place.
_STRANDED_ADVERB = re.compile(
    '(?P<pred>[^\\s、。「」『』！？!?がはをにでともへの]{1,10})(?P<cop>でした|ました|です|ます)'
    '(?P<adv>' + '|'.join(_DEGREE_ADVERBS) + ')')

# たくさん modifying a noun needs の. Restricted to a が-marked subject, where
# the adverbial reading is not available: 「たくさん本を読む」 is ordinary spoken
# Japanese and must not be touched, but 「たくさん人がいます」 has たくさん sitting
# on a subject noun and wants 「たくさんの人」.
_TAKUSAN_NO = re.compile('たくさん(?P<noun>[一-龥ァ-ヶー]{1,6})(?=が)')


def apply_word_order_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a stranded degree adverb or a bare
    たくさん modifying a subject noun."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    match = _STRANDED_ADVERB.search(user_input)
    if match:
        pred, cop, adv = match.group('pred'), match.group('cop'), match.group('adv')
        return (f'💡 Feedback:\n- ❌ "{pred}{cop}{adv}" → ✅ "{adv}{pred}{cop}" '
                f'(程度を表す副詞は述語の前に置きます)')

    match = _TAKUSAN_NO.search(user_input)
    if match:
        noun = match.group('noun')
        return (f'💡 Feedback:\n- ❌ "たくさん{noun}" → ✅ "たくさんの{noun}" '
                f'(「たくさん」が名詞を修飾するときは「の」が必要です)')

    return feedback


# Things that are drunk, not eaten. A closed collocation the model does not
# enforce: it called 「薬を食べました」 natural. Kept to the cases where 飲む is
# the only option — スープ is deliberately absent, since 「スープを食べる」 is
# acceptable for a chunky soup and this net must never correct correct Japanese.
_DRINK_NOUNS = ('薬', '水', 'お茶', 'コーヒー', '紅茶', 'ジュース', 'ビール',
                'ワイン', '牛乳', 'ミルク', 'お酒', '日本酒')

# The learner's own inflection, spliced onto the right verb — the same choice
# _ti_inflect makes, and for the same reason: the repeat drill asks them to
# retype the ✅ text.
_EAT_TO_DRINK = {
    '食べました': '飲みました', '食べます': '飲みます', '食べた': '飲んだ',
    '食べる': '飲む', '食べて': '飲んで', '食べません': '飲みません',
    '食べたい': '飲みたい', '食べなかった': '飲まなかった', '食べよう': '飲もう',
}
_EAT_DRINK_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_DRINK_NOUNS) + ')を'
    '(?P<verb>' + '|'.join(sorted(_EAT_TO_DRINK, key=len, reverse=True)) + ')')


def apply_collocation_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict when a drink or a medicine is 食べる'd."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    match = _EAT_DRINK_ERROR.search(user_input)
    if not match:
        return feedback
    noun, verb = match.group('noun'), match.group('verb')
    right = _EAT_TO_DRINK[verb]
    return (f'💡 Feedback:\n- ❌ "{noun}を{verb}" → ✅ "{noun}を{right}" '
            f'(「{noun}」は「飲む」を使います)')


# Existence: いる for living things, ある for everything else, and に — not で —
# for the place a thing exists. Three shapes, all measured at 0/5 on the recall
# probe with a clean verdict every time, and all three in the half of OPEN-10
# the model does not know: asked plainly with no coach prompt it called
# 「部屋に猫があります」, 「机の上に本がいます」 and 「教室で学生がいます」 正しい.
#
# Living things. Enumerated, and the exclusions are the whole point: every noun
# that ALSO takes ある in a "have one" reading is absent by construction —
# 子供がある, 友達がある, お客がある and 赤ちゃんがある are all real Japanese.
# So are 鳥/牛/豚/魚 on a menu, where the noun is the meat and ある is right.
_JA_ANIMATE = ('猫', 'ねこ', '犬', 'いぬ', '子猫', '子犬',
               '先生', '学生', '生徒', '店員', '医者', '看護師',
               '警察官', '運転手', '男の人', '女の人')
_ARU_TO_IRU = {'あります': 'います', 'ありました': 'いました',
               'ありません': 'いません', 'ある': 'いる', 'あった': 'いた'}
_ARU_ON_ANIMATE = re.compile(
    '(?P<noun>' + '|'.join(_JA_ANIMATE) + ')(?P<p>[がは])'
    '(?P<verb>' + '|'.join(sorted(_ARU_TO_IRU, key=len, reverse=True)) + ')')

# The other direction needs a position word in front of it, because いる is not
# only 居る: 要る ("to need") is normally written in kana, so 「本がいる」 and
# 「傘がいります」 are correct sentences. A physical position makes the needing
# reading unavailable.
_JA_POSITION = ('上', '下', '中', '前', '後ろ', '横', '隣', 'そば', '近く', '奥')
_JA_INANIMATE = ('本', '机', '椅子', 'いす', '鞄', 'かばん', '財布', '傘', 'かさ',
                 '鍵', 'かぎ', '時計', '荷物', '手紙', '新聞', '雑誌', 'パソコン',
                 '冷蔵庫', '洗濯機', '皿', 'コップ', '箱', '靴', '帽子', '切符')
# いる/いた are deliberately ABSENT for the same reason. The ます-forms cannot
# collide at all — 要る inflects to いります/いりません, never to います — so
# they are the only forms this rule is allowed to touch.
_IRU_TO_ARU = {'います': 'あります', 'いました': 'ありました',
               'いません': 'ありません'}
_IRU_ON_INANIMATE = re.compile(
    '(?:' + '|'.join(_JA_POSITION) + ')に[^。、]{0,10}?'
    '(?P<noun>' + '|'.join(_JA_INANIMATE) + ')(?P<p>[がは])'
    '(?P<verb>' + '|'.join(sorted(_IRU_TO_ARU, key=len, reverse=True)) + ')')

# で + existence. Restricted to いる and to a living subject, because で + ある
# is CORRECT when the thing that "exists" is an event held at the place:
# 「教室で試験があります」, 「会議室で会議があります」. Adjacency (がいます, not
# がいる anywhere later) is what keeps 「教室で学生が勉強しています」 out, the
# same adjacency argument the transitivity net already makes.
_EXIST_PLACES = _JA_PLACE_NOUNS + ('部屋', '家', 'うち', 'ここ', 'そこ', 'あそこ',
                                   '駅前', '廊下', '庭', '屋上')
_DE_EXISTENCE_ERROR = re.compile(
    '(?P<place>' + '|'.join(_EXIST_PLACES) + ')で[^。、]{0,8}?'
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


# Saying you are late and offering no apology is the one situational miss that
# does NOT need to know who the listener is: the apology is owed to anyone kept
# waiting. COACH_SITUATION already asks for it and the model does not produce
# it — 61 and 62 scored 0/5, in both languages, with the situation in the
# prompt. So it is netted, in both languages, and gated on `situational`
# because a sentence with no situation around it has nobody to apologise to.
_LATE_MARKERS = {
    'Japanese': re.compile('遅れ(?:ま|そう|る)|遅刻|遅くなり'),
    'English': re.compile(r"\b(?:i|we)(?:'m| am| will be|'ll be| are)\b[^.!?]{0,40}?\blate\b",
                          re.IGNORECASE),
}
_APOLOGY_MARKERS = {
    'Japanese': ('すみません', 'すいません', '申し訳', 'ごめん', '恐れ入り', '失礼'),
    'English': ('sorry', 'apolog', 'forgive'),
}
# The English marker is subject-anchored — it requires "I/we ... late" — but the
# Japanese one was not, so 「電車が遅れました。」 was read as the learner being
# late and the net told them to apologise for the train. That is the failure the
# whole net design exists to avoid: a net may only ever overturn a CLEAN verdict,
# and here it overturned one on correct Japanese. Worse, `promote_fit` is on in
# the CLI, so it landed as a Feedback bullet and `run_correction_drill` — a
# `while True` with no skip — made the learner retype an apology they did not
# owe, with Ctrl-D the only way out.
#
# Japanese marks the subject rather than fixing it by position, so the guard is
# to look for an explicit `Xが` / `Xは` inside the same clause as the late verb.
# A third-party subject there means the lateness is not the learner's. An absent
# subject means the speaker, which is the ordinary Japanese reading — 「予約の
# 時間に三十分遅れました」 (fixture 61) has no subject and must still fire.
_JA_FIRST_PERSON = ('私', 'わたし', 'わたくし', '僕', 'ぼく', '俺', 'おれ', '自分', 'うち')
_JA_SUBJECT = re.compile(r'([^\s、。！？]{1,12}?)[がは]')


def _ja_subject_is_someone_else(clause: str, late) -> bool:
    """True when the clause names an explicit subject that is not the speaker."""
    hit = late.search(clause)
    if not hit:
        return False
    for m in _JA_SUBJECT.finditer(clause[:hit.start()]):
        subject = m.group(1)
        if not any(p in subject for p in _JA_FIRST_PERSON):
            return True
    return False


_APOLOGY_FIX = {
    'Japanese': ('すみません、', '遅れることを伝えるときは、まずお詫びの言葉を添えます'),
    'English': ("I'm sorry — ", 'when you tell someone you are late, lead with an apology'),
}
_SENTENCE_SPLIT = re.compile('(?<=[.!?。．！？])\\s*')


def apply_apology_net(feedback: str, user_input: str, language: str,
                      situational: bool = False) -> str:
    """Overturn a clean verdict when the learner reports being late and
    apologises for nothing. Both languages."""
    if not situational or not is_clean_verdict(feedback, language):
        return feedback
    late = _LATE_MARKERS.get(language)
    if late is None or not late.search(user_input):
        return feedback
    if any(marker in user_input.lower() for marker in _APOLOGY_MARKERS[language]):
        return feedback

    prefix, reason = _APOLOGY_FIX[language]
    said = next((s for s in _SENTENCE_SPLIT.split(user_input.strip())
                 if late.search(s)), user_input.strip())
    said = said.strip()
    if language == 'Japanese' and _ja_subject_is_someone_else(said, late):
        return feedback
    return (f'💡 Feedback:\n- ❌ "{said}" → ✅ "{prefix}{said}" ({reason})')


# "Perfectly natural!" is the canonical clean verdict everywhere inside the
# pipeline — COACH_SYS asks for it, filter_coach_output collapses to it, and
# apply_particle_net keys on it. Only the learner-facing text is localized, and
# only at the very end, so the prompt itself never changes: removing a single
# worked example from COACH_SYS moved four unrelated cases and cost 12
# iterations, so prompt edits are not a cheap lever here.
#
# The Japanese wording is deliberately weaker than the English. The coach misses
# roughly three quarters of real Japanese errors (OPEN-10), and answering
# 「完璧です」 to a sentence that is in fact wrong does not merely fail to help —
# it confirms the mistake and the learner practises it. Reporting what the
# checker actually did ("I did not find anything to fix") is honest at this
# accuracy; a verdict on the sentence would not be.
