"""The Japanese vocabulary and patterns the nets match against.

One place, because most of these tables feed more than one net — the place
nouns are used by the particle net and the existence net, the person nouns
by the particle net and the register net.

Every list here is deliberately narrow. A net is only as safe as the correct
sentences it is proven to leave alone, and each of these was widened only
when a measurement said to. See BACKLOG OPEN-07 and OPEN-10.
"""
import re


_NI_TARGET_VERBS = {
    '会': '「会う」の相手は「に」か「と」で示します',
    '乗': '「乗る」の行き先は「に」で示します',
}

_NI_PARTICLE_ERROR = re.compile(
    '(?P<noun>[^\\s、。「」『』！？!?・をはがにでともへや]{1,12})を'
    '(?P<stem>会[いうっえお]'
    '|乗(?:る|った|って|ります|りました|りません|りましょう|りたい|らない|れば|ろう))'
)

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

_TI_PATIENTS = (
    '窓', 'ドア', '扉', '電気', '明かり', '照明', '電源', 'テレビ', 'エアコン',
    '会議', '授業', '試合', '店', '番組', '映画', 'パーティー', '荷物', '予約',
    '火', 'お湯', '音楽', 'ドアベル', 'カーテン',
)

# Endings after which a transitive verb with が is CORRECT, not an error:
# passives, the 〜てある resultative (窓が開けてあります) and が-marked
# objects of 〜たい (窓が開けたいです).
_TI_SUFFIX_BLOCK = ('られ', 'れる', 'れま', 'れた', 'てあ', 'であ', 'たい')

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
     ('個', 'つ'), '丸くて小さいものは「つ」か「個」で数えます'),
    (('雑誌', 'ノート', '辞書', '教科書'),
     ('本', '枚', '匹', '台', '杯'),
     ('冊',), '本や雑誌は「冊」で数えます'),
)

_COUNT_NUM = '[0-9０-９一二三四五六七八九十百千]+'

_JA_PERSON_NOUNS = (
    '先生', '友達', '友だち', '母', '父', 'お母さん', 'お父さん', '兄', '姉',
    '弟', '妹', '両親', '家族', '彼', '彼女', '上司', '部長', '課長', '社長',
    '同僚', '先輩', '後輩', '店員', '医者', '看護師', 'お客さん', 'お客様',
    '担当者', '日本人', '外国人', '子供', '子ども', '息子', '娘', '奥さん',
    'ご主人', '主人', '妻', '夫', '友人', '知り合い', '警察官', '運転手',
)

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

_TO_PARTNER_SURU = {
    '結婚': '「結婚する」相手は「と」で示します',
    '離婚': '「離婚する」相手は「と」で示します',
    '喧嘩': '「喧嘩する」相手は「と」で示します',
    'けんか': '「けんかする」相手は「と」で示します',
    # 約束 deliberately absent: 〜に約束する (the person promised) and
    # 〜と約束する (a mutual arrangement) are BOTH correct, with different
    # meanings, so the net cannot assert one is an error.
}

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

_JA_PLACE_NOUNS = (
    '図書館', '図書室', '学校', '大学', '教室', '会社', '事務所', '公園',
    'レストラン', 'カフェ', '喫茶店', '食堂', '空港', '病院', '銀行',
    '郵便局', '本屋', 'スーパー', 'コンビニ', 'ホテル', '台所', '教会',
    '工場', '会議室', '体育館', 'プール', '図書館前', '公民館', '自習室',
)

_DE_ACTION_SURU = ('勉強', '練習', '仕事', '食事', '会議', '掃除')

_DE_ACTION_STEMS = (
    '働きました', '働きます', '働いて', '働く',
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

_BARE_TIME_WORDS = (
    '今日', 'きょう', '明日', 'あした', 'あす', '昨日', 'きのう',
    '今朝', 'けさ', '今晩', '今夜', '毎日', '毎朝', '毎晩', '毎週',
    '毎月', '毎年', '今週', '来週', '先週', '今月', '来月', '先月',
    '今年', '来年', '去年', 'おととい', '一昨日', 'あさって', '明後日',
)

_TIME_NI_OK = ('は', 'も', 'で', 'の', 'か', 'し', '近', '比', '入', '至', '向',
               '続', '備', '関', '対', 'わた', '渡', 'つい', '付', '限', '当',
               'あた', 'なっ', 'なり', 'なる', '変', '及', '間', '引', '延',
               '予', '持', '決', '送', '繰', '回', '合', '先立')

_BARE_TIME_NI_ERROR = re.compile(
    '(?P<word>' + '|'.join(sorted(_BARE_TIME_WORDS, key=len, reverse=True)) + ')'
    'に(?!' + '|'.join(_TIME_NI_OK) + ')(?=[^\\s])')

_CLAUSE_END = '。、！？!?\n'

# 降り is deliberately absent: 降りる is ichidan, so 降りて is correct and
# 「電車を降りて」 is everyday Japanese. 「雨が降りて」 is the rare error;
# catching it would cost the common correct sentence.
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
    '走り': '走って', '座り': '座って', '送り': '送って',
    '曲がり': '曲がって', '行き': '行って',
}

_TE_ONBIN_ERROR = re.compile('(' + '|'.join(_TE_ONBIN) + ')て')

_I_ADJ_PAST_ERROR = re.compile('(?P<stem>[^\\s、。「」『』！？!?]{0,10}?)(?<!み)(?P<adj>たい|ない)でした')

_I_ADJECTIVES = (
    '楽しい', '嬉しい', 'うれしい', '悲しい', '面白い', 'おもしろい', '忙しい',
    '寒い', '暑い', '熱い', '冷たい', '高い', '安い', '良い', 'よい', '悪い',
    '難しい', '易しい', '新しい', '古い', '大きい', '小さい', '近い', '遠い',
    '早い', '速い', '遅い', '強い', '弱い', '長い', '短い', '広い', '狭い',
    '多い', '少ない', '怖い', '痛い', 'かわいい', 'すごい', '欲しい', 'ほしい',
    'おいしい', '美味しい', '美しい', '優しい', '厳しい', '眠い',
)

_I_ADJ_LIST_ERROR = re.compile('(?P<adj>' + '|'.join(_I_ADJECTIVES) + ')でした')

_I_ADJ_JANAI_TAIL = {
    'ないです': 'くないです',
    'ないんです': 'くないんです',
    'なかったです': 'くなかったです',
    'ありません': 'くありません',
    'ありませんでした': 'くありませんでした',
}

_I_ADJ_JANAI_ERROR = re.compile(
    '(?P<adj>' + '|'.join(_I_ADJECTIVES) + ')じゃ'
    '(?P<tail>' + '|'.join(sorted(_I_ADJ_JANAI_TAIL, key=len, reverse=True))
    + ')(?![かね])')

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

_JA_SUPERIOR_ADDRESS = (
    '先生', '部長', '課長', '社長', '店長', '館長', '主任', '先輩',
    'お客様', 'お客さん', '社長さん', '部長さん',
)

_SUPERIOR_VOCATIVE = re.compile(
    '^(?:' + '|'.join(_JA_SUPERIOR_ADDRESS) + ')[、,]')

_CASUAL_PRONOUNS = (('俺', '私'), ('おれ', '私'), ('お前', 'あなた'), ('おまえ', 'あなた'))

_JA_POLITE_MARKERS = ('ます', 'です', 'ください', 'ましょう', 'でしょう', 'ございま')

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

_DEGREE_ADVERBS = ('とても', 'すごく', '本当に', 'ほんとうに', 'かなり', '非常に',
                   'ちょっと', '少し', 'たくさん', 'よく')

# The adverb must be the last thing in the clause. In
# 「この店は有名ですとても人気があります」 the とても belongs to the clause that
# follows it, and the sentence's fault is the missing punctuation, not the
# word order.
_STRANDED_ADVERB = re.compile(
    '(?P<pred>[^\\s、。「」『』！？!?がはをにでともへの]{1,10})(?P<cop>でした|ました|です|ます)'
    '(?P<adv>' + '|'.join(_DEGREE_ADVERBS) + r')(?=\s*$|[。、！？!?])')

_TAKUSAN_NO = re.compile('たくさん(?P<noun>[一-龥ァ-ヶー]{1,6})(?=が)')

_DRINK_NOUNS = ('薬', '水', 'お茶', 'コーヒー', '紅茶', 'ジュース', 'ビール',
                'ワイン', '牛乳', 'ミルク', 'お酒', '日本酒')

_EAT_TO_DRINK = {
    '食べました': '飲みました', '食べます': '飲みます', '食べた': '飲んだ',
    '食べる': '飲む', '食べて': '飲んで', '食べません': '飲みません',
    '食べたい': '飲みたい', '食べなかった': '飲まなかった', '食べよう': '飲もう',
}

_EAT_DRINK_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_DRINK_NOUNS) + ')を'
    '(?P<verb>' + '|'.join(sorted(_EAT_TO_DRINK, key=len, reverse=True)) + ')')

_JA_ANIMATE = ('猫', 'ねこ', '犬', 'いぬ', '子猫', '子犬',
               '先生', '学生', '生徒', '店員', '医者', '看護師',
               '警察官', '運転手', '男の人', '女の人')

_ARU_TO_IRU = {'あります': 'います', 'ありました': 'いました',
               'ありません': 'いません', 'ある': 'いる', 'あった': 'いた'}

_ARU_ON_ANIMATE = re.compile(
    '(?P<noun>' + '|'.join(_JA_ANIMATE) + ')(?P<p>[がは])'
    '(?P<verb>' + '|'.join(sorted(_ARU_TO_IRU, key=len, reverse=True)) + ')'
    # 「先生がある日来ました」「ある程度」 — prenominal ある is not the verb,
    # so the two plain forms only count at a clause boundary.
    r'(?=\s*$|[。、！？]|[^日程度意味種])')

_JA_POSITION = ('上', '下', '中', '前', '後ろ', '横', '隣', 'そば', '近く', '奥')

_JA_INANIMATE = ('本', '机', '椅子', 'いす', '鞄', 'かばん', '財布', '傘', 'かさ',
                 '鍵', 'かぎ', '時計', '荷物', '手紙', '新聞', '雑誌', 'パソコン',
                 '冷蔵庫', '洗濯機', '皿', 'コップ', '箱', '靴', '帽子', '切符')

_IRU_TO_ARU = {'います': 'あります', 'いました': 'ありました',
               'いません': 'ありません'}

_IRU_ON_INANIMATE = re.compile(
    '(?:' + '|'.join(_JA_POSITION) + ')に[^。、]{0,10}?'
    '(?P<noun>' + '|'.join(_JA_INANIMATE) + ')(?P<p>[がは])'
    '(?P<verb>' + '|'.join(sorted(_IRU_TO_ARU, key=len, reverse=True)) + ')')

_EXIST_PLACES = _JA_PLACE_NOUNS + ('部屋', '家', 'うち', 'ここ', 'そこ', 'あそこ',
                                   '駅前', '廊下', '庭', '屋上')

_DE_EXISTENCE_ERROR = re.compile(
    # The gap may not contain a te-form: in 「教室で勉強している学生がいます」
    # the で belongs to 勉強している, not to います, and the sentence is correct.
    '(?P<place>' + '|'.join(_EXIST_PLACES) + ')で(?![^。、]{0,12}?(?:てい|でい|って|んで))'
    '[^。、]{0,8}?'
    '(?P<noun>' + '|'.join(_JA_ANIMATE) + ')(?P<p>[がは])'
    '(?P<verb>います|いました|いる|いた)')

_LATE_MARKERS = {
    'Japanese': re.compile('遅れ(?:ま|そう|る)|遅刻|遅くなり'),
    'English': re.compile(r"\b(?:i|we)(?:'m| am| will be|'ll be| are)\b[^.!?]{0,40}?\blate\b",
                          re.IGNORECASE),
}

_APOLOGY_MARKERS = {
    'Japanese': ('すみません', 'すいません', '申し訳', 'ごめん', '恐れ入り', '失礼'),
    'English': ('sorry', 'apolog', 'forgive'),
}

_JA_FIRST_PERSON = ('私', 'わたし', 'わたくし', '僕', 'ぼく', '俺', 'おれ', '自分', 'うち')

_JA_SUBJECT = re.compile(r'([^\s、。！？]{1,12}?)[がは]')

_APOLOGY_FIX = {
    'Japanese': ('すみません、', '遅れることを伝えるときは、まずお詫びの言葉を添えます'),
    'English': ("I'm sorry — ", 'when you tell someone you are late, lead with an apology'),
}

_SENTENCE_SPLIT = re.compile('(?<=[.!?。．！？])\\s*')


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


# Underscore names are skipped by `import *` unless they are listed here,
# and every net file pulls its match tables in that way.
__all__ = [
    '_NI_TARGET_VERBS', '_NI_PARTICLE_ERROR', '_TI_PAIRS',
    '_TI_PATIENTS', '_TI_SUFFIX_BLOCK', '_COUNTER_RULES',
    '_COUNT_NUM', '_JA_PERSON_NOUNS', '_NI_PARTNER_SURU',
    '_TO_PARTNER_SURU', '_SURU_TAIL', '_NI_PARTNER_ERROR',
    '_TO_PARTNER_ERROR', '_NI_RESIDENCE_ERROR', '_JA_PLACE_NOUNS',
    '_DE_ACTION_SURU', '_DE_ACTION_STEMS', '_DE_ACTION_ERROR',
    '_BARE_TIME_WORDS', '_TIME_NI_OK', '_BARE_TIME_NI_ERROR',
    '_CLAUSE_END', '_TE_ONBIN', '_TE_ONBIN_ERROR',
    '_I_ADJ_PAST_ERROR', '_I_ADJECTIVES', '_I_ADJ_LIST_ERROR',
    '_I_ADJ_JANAI_TAIL', '_I_ADJ_JANAI_ERROR', '_ADVERBIAL_VERBS',
    '_I_ADJ_ADVERB_ERROR', '_JA_SUPERIOR_ADDRESS', '_SUPERIOR_VOCATIVE',
    '_CASUAL_PRONOUNS', '_JA_POLITE_MARKERS', '_PLAIN_TO_POLITE',
    '_PLAIN_ENDING', '_DEGREE_ADVERBS', '_STRANDED_ADVERB',
    '_TAKUSAN_NO', '_DRINK_NOUNS', '_EAT_TO_DRINK',
    '_EAT_DRINK_ERROR', '_JA_ANIMATE', '_ARU_TO_IRU',
    '_ARU_ON_ANIMATE', '_JA_POSITION', '_JA_INANIMATE',
    '_IRU_TO_ARU', '_IRU_ON_INANIMATE', '_EXIST_PLACES',
    '_DE_EXISTENCE_ERROR', '_LATE_MARKERS', '_APOLOGY_MARKERS',
    '_JA_FIRST_PERSON', '_JA_SUBJECT', '_APOLOGY_FIX',
    '_SENTENCE_SPLIT', '_ti_lookup', '_ti_inflect',
    '_quote_through', '_clause_or_pair', '_ja_subject_is_someone_else',
]
