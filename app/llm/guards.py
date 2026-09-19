"""Is this the language we asked for, and is it a usable sentence?

Script checks, question shape, and the validator the actor is held to.
The rules here are narrow on purpose — a guard that rejects correct output
costs the learner the turn. See BACKLOG OPEN-22, OPEN-26, OPEN-35, OPEN-40.
"""
import re

from .client import (CLOSED_OPENERS, WH_WORDS, EMOJI_PATTERN,
                     strip_think_tags)
from .vocab import strip_vocab_block

# Japanese character classes, shared with translate.py, which owns them
_KANA_OR_KANJI = re.compile(r'[\u3040-\u30FF\u4E00-\u9FFF]')



def sanitize(text: str, speaker: str=None) -> str:
    """Strip reasoning traces, stage directions, character prefixes, and emoji.

    `speaker` should be the known character name (e.g. "Barista") so only
    that exact prefix is stripped — a generic \\w+: pattern would also eat
    the first clause of real dialogue that happens to start the same way
    (e.g. "Sure: here you go." -> "here you go.").
    """
    text = strip_think_tags(text)
    # Deliberately ASCII-only, and measured rather than assumed. Across 152
    # Japanese actor turns — including 24 generated with the anti-narration
    # clause removed to provoke it — the model produced ZERO full-width stage
    # directions, zero ＊ and zero 【】. Every full-width bracket found was
    # content the learner wants kept: 収入比（債務対収入比率）, 烤鸭（かがも）,
    # スターダストホテル（これは地名や施設名ではなく、例示のための言葉）.
    #
    # So widening this to （）would delete glosses to catch narration that does
    # not occur — the ASCII rule is already observed destroying a Japanese
    # reading gloss, パーム (パーム). Widening it to ＊ was tried and dropped:
    # zero measured benefit, and a ＊ span straddling the word:/explanation:
    # labels destroys the whole vocab card, which is the dominant actor
    # failure. If a future model does emit full-width narration, measure it
    # first — see OPEN-16 and the F3 audit finding.
    text = re.sub('\\*+[^*]*\\*+', '', text)
    text = re.sub('\\([^)]*\\)', '', text)
    if speaker:
        text = re.sub(f'^\\s*{re.escape(speaker)}\\s*:\\s*', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(EMOJI_PATTERN, '', text)
    text = re.sub('\\s{2,}', ' ', text).strip()
    text = text.strip('"')
    return text

def sanitize_learner_input(user_input: str) -> str:
    """Strip system directive injection tokens from learner input."""
    cleaned = re.sub(r'<\|.*?\|>', '', user_input)
    cleaned = re.sub(r'\[System:.*?\]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'</?(?:system|user|assistant|think|vocab)>', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

# Japanese question detection. A polite question ends in か; it is OPEN when it
# carries an interrogative, and closed otherwise. Mirrors the English rule,
# where a wh-word likewise rescues a sentence from the closed-opener test.
#
# いかが is treated as open for exactly that parity: English "How about a
# coffee?" opens with a wh-word and passes, so 「コーヒーはいかがですか」 must too.
# そうですか is excluded because it is an acknowledgement, not a question, and
# would otherwise be rejected as closed.


_JA_KANA = re.compile('[ぁ-んァ-ヴ]')
_JA_QUESTION_END = re.compile('か[。．.？?！!\\s]*$')
_JA_INTERROGATIVES = ('何', 'なに', 'なん', 'どこ', 'いつ', '誰', 'だれ', 'どちら', 'どっち',
                      'どの', 'どれ', 'どう', 'どんな', 'いくつ', 'いくら', 'なぜ', 'いかが')
_JA_NOT_QUESTIONS = ('そうですか',)

# A casual question drops か and carries only ？ (砂糖は入れる？). It must still
# end in a predicate — plain-form verbs and adjectives inflect in hiragana — to
# keep the rule off elliptical questions, which are OPEN and carry no
# interrogative to find: お名前？ is "what is your name", not a yes/no offer, and
# is indistinguishable from 領収書？ except by the noun. A trailing bare particle
# (ご注文は？) is the same ellipsis with the particle left on.
_JA_CASUAL_END = re.compile('[ぁ-ん]？\\s*$')
_JA_ELLIPTICAL_END = re.compile('[はがをにでとも]？\\s*$')

# The indefinite pronouns embed an interrogative as a substring, so a bare
# `word in s` test reads every closed question built on one — 何かお手伝いできる
# ことがありますか, the commonest Japanese service greeting there is — as open.
# They are removed before the interrogative test rather than added to it.
#
# Three guards keep genuine interrogatives whole. か must not open the ablative
# から (まず何からいたしましょうか is "what shall we start with"), and must not be
# the sentence-final question particle (これは何か。) or sit on a clause boundary
# (お気に入りは何か、または…), where the word before it is a real interrogative.
_JA_INDEFINITE = re.compile(
    '(?:何|なに|なん|どこ|いつ|誰|だれ|どれ|どちら)か(?!ら)(?![、，])(?![。．.？?！!\\s]*$)')

# Mirrors the English branch, which exempts a medial ' or ' but still closes a
# sentence-initial "Or, do you want ...": an alternative question hands the
# learner a real choice, a discourse-initial connective does not.
_JA_ALTERNATIVE = re.compile('.(?:または|それとも|もしくは|あるいは|或いは)')


def _is_closed_question_ja(sentence: str) -> bool:
    """Japanese branch: reads as a question, carries no interrogative."""
    s = sentence.strip()
    if not (_JA_QUESTION_END.search(s)
            or (_JA_CASUAL_END.search(s) and not _JA_ELLIPTICAL_END.search(s))):
        return False
    if any(phrase in s for phrase in _JA_NOT_QUESTIONS):
        return False
    if _JA_ALTERNATIVE.search(s):
        return False
    return not any(word in _JA_INDEFINITE.sub('', s) for word in _JA_INTERROGATIVES)


def is_question(sentence: str) -> bool:
    """Whether a sentence is a question AT ALL, in either script.

    Deliberately NOT the complement of `is_closed_question`, which answers the
    narrower "is this a yes/no question". Both are needed: closed questions are
    dropped before this is consulted, so anything this accepts at the reserved
    last slot is an open one.

    Dispatches on the same evidence `is_closed_question` uses — the か-final
    pattern — rather than on ASCII `?`, which Japanese sentences never contain.
    そうですか is excluded for the same reason it is there: it is an
    acknowledgement, and a turn that ends on one has not asked the learner
    anything, so it should still earn a salvage question.
    """
    s = sentence.strip()
    if '?' in s or '？' in s:
        return True
    if not _JA_QUESTION_END.search(s):
        return False
    return not any(phrase in s for phrase in _JA_NOT_QUESTIONS)


def is_closed_question(sentence: str) -> bool:
    """Check if a single sentence is a closed yes/no question.

    Dispatches on script rather than on a language argument, so the ~15
    existing single-argument callers keep working: English text never contains
    kana. The Japanese branch was added after the actor suite was found to be
    enforcing this rule on only half the catalog — `列車のチケットが必要ですか。`
    passed because the test matched ASCII `?` and `[a-z']+` only.
    """
    if _JA_KANA.search(sentence):
        return _is_closed_question_ja(sentence)
    s_lower = sentence.lower()
    if s_lower.endswith('?'):
        words = re.findall("[a-z']+", s_lower)
        if words:
            leading_words = set(words[:3])
            found_opener = leading_words.intersection(CLOSED_OPENERS)
            if found_opener and not (WH_WORDS & set(words)):
                if ' or ' not in s_lower or ' or not' in s_lower or ' or no' in s_lower:
                    return True
    return False

# Simplified-Chinese-only forms that do not occur in modern Japanese. NOT a Han
# check: Japanese uses kanji throughout, so rejecting Han would fail every
# correct Japanese turn. Story and measurements: BACKLOG OPEN-22.
#
# THE END POINTS ARE TRIMMED DELIBERATELY AND MUST NOT BE WIDENED to the end of
# each Unicode block. The blocks run on into ordinary Japanese kanji, and the
# loose version of this rule flagged 谷 豆 豈 鹿 角 辛 辞 辟 韭 缶 缺 網 罕 飛 食
# — all common Japanese, none caught by the fixture corpus, all found by
# printing the ranges and reading them. dev/tests/test_main.py pins them.
_SIMPLIFIED_RANGES = (
    (0x8BA0, 0x8C36),  # 讠 speech radical: 计 … 谶
    (0x9485, 0x9576),  # 钅 metal radical:  钅 … 镶
    (0x7EA0, 0x7F35),  # 纟 silk radical:   纠 … 缵
    (0x9963, 0x9995),  # 饣 food radical:   饣 … 馕
    (0x9A6C, 0x9A9F),  # 马 horse radical:  马 … 骟
    (0x9E1F, 0x9E74),  # 鸟 bird radical:   鸟 … 鹴
    (0x9C7C, 0x9CE0),  # 鱼 fish radical:   鱼 … 鳠
    (0x8D1D, 0x8D5F),  # 贝 shell radical:  贝 … 赟
    (0x9875, 0x98A0),  # 页 page radical:   页 … 颠
    (0x8F66, 0x8F9A),  # 车 cart radical:   车 … 辚
    (0x95E8, 0x9615),  # 门 gate radical:   门 … 阕
    (0x97E6, 0x97EC),  # 韦 leather:        韦 … 韬
    (0x98CE, 0x98DA),  # 风 wind:           风 … 飚
    (0x98DE, 0x98DE),  # 飞
    (0x89C1, 0x89D1),  # 见 see radical:    见 … 觑
)

# Rule 2, the characters simplified without a radical series, so no range
# reaches them. Chosen as "the simplified form differs from the Japanese form"
# — 药/薬, 还/還, 书/書, 宠/寵, 带/帯 — never merely "looks Chinese". Forms that
# Japanese shares are deliberately absent and must stay absent: 医 励 鼓 物 院
# 使 用 来 如 或 appear in the audit's leaked line and are all ordinary
# Japanese; so are 没 (没収), 区, 双, 号, 学, 国, 会, 写, 与, 宝, 声, 麦, 黄 and
# 迎 — 迎 was in the old hand-picked set, which is a live false positive it
# never hit only because no test string used 迎える.
#
# 据 筑 庄 怜 were in this table's first cut and are official Japanese kanji
# (据 jōyō, the rest jinmeiyō), each reachable from this app's own scenarios:
# 筑前煮, 据え付け, 庄内. The 356-string corpus contained none of them, so a
# Shift-JIS screen guards the table instead — see
# test_wrong_script_table_is_screened_against_the_japanese_standard_set.
_SIMPLIFIED_CHARS = set(
    '这们个么无东长时电关开还药书您卖买亚汉欢华单发变头实宁专业丛严丧临为举义乐习乡'
    '亿仅从仑仓仪优伞伟传伤伦价众侣侦侧侨俭债倾偿储兑兰兴养兽冈军农冲决况冻净凉减凤凭击凿'
    '刘则刚创删别刽剂剑劝办务动劳势勋协卢卫厂厅历厉压厌厕叠叹吓吗听吨启员呛呜咙哑哗唤啧啬喷嚣'
    '园围图圆圣场块坚坛坏坝坞坟坠垄垒垦垫埚堑报壳壶处备复够夸夹夺奋奖妆妇妈娄娇娱婴孙孪'
    '实宠审宪宫宽宾对寻导尔尘尝尧尴层屉屿岁岂岗岚岛岭崭巩币帅师帐帘帜带帮广庆庐库应庙庞废'
    '异弃张弯弹归录彻忆忏忧怀态总恳恶恼悬惊惧惩惭惯愤懒戏战户扑执扩扫扬扰抚抛抢护拟拥拨择'
    '挡挤挥捞损换捣掷插搅摄摆摊摇败'
    '罗罚罢羁联聂聋职肃肠肤肾肿胀胁脏脑脓脸腻舆舰舱艳艺节芜苇苍苏茧荐荡荣莲获莺萝萤营萧萨'
    '蓝虏虑虾蚀蚁蝇补衬袜辩边辽达迁过迈运进远违连迟递逊遗邓邮邻郑酱酿释'
    '陆陈阶阳阴陕隐隶雏杂难雾齐齿龄龙龟'
    '种类积稳穷竖竞笔简签篮粮紧热爱现环疗皱盐监盖盘瞒矫码础硕确离跃赶赵趋阵'
)


# Traditional-Chinese forms Japanese replaced with a shinjitai — neither
# simplified nor Japanese, so they fell between the other two tables
# (BACKLOG OPEN-40).
#
# A SHORT EXPLICIT LIST, NOT A RANGE: kyūjitai survive in names and formal
# titles, so 髙 and 﨑 in a surname are correct and are deliberately absent.
_TRADITIONAL_CHARS = frozenset(
    '檢醫發廣國學會體點鐵讀營齒藥證單雙舊賣價觀歡擔據屬繼總變穩豐')

# Scripts that are never Japanese. Unlike the simplified table this needs no
# judgement: one character is proof on its own. See BACKLOG OPEN-40.
_FOREIGN_SCRIPT_RANGES = (
    (0x0400, 0x052F),    # Cyrillic and its supplement
    (0x0370, 0x03FF),    # Greek
    (0x1100, 0x11FF),    # Hangul jamo
    (0xAC00, 0xD7AF),    # Hangul syllables
    (0x0E00, 0x0E7F),    # Thai
    (0x0600, 0x06FF),    # Arabic
    (0x0590, 0x05FF),    # Hebrew
    (0x0900, 0x097F),    # Devanagari
)


def find_wrong_script(text: str, language: str) -> str:
    """Characters betraying another language's script, or '' if clean."""
    if language != 'Japanese' or not text:
        return ''
    bad = {c for c in text
           if c in _SIMPLIFIED_CHARS
           or any(lo <= ord(c) <= hi for lo, hi in _SIMPLIFIED_RANGES)
           or c in _TRADITIONAL_CHARS
           or any(lo <= ord(c) <= hi for lo, hi in _FOREIGN_SCRIPT_RANGES)}
    return ''.join(sorted(bad))


# An English clause spliced into a Japanese turn. Measured 2 of 12
# mid-conversation turns and 0 of 12 greetings — the actor writes a Japanese
# sentence and drops an English phrase into it: 「…Reception or dinner party…」
# (OPEN-35). find_wrong_script cannot see it: that is a simplified-Chinese
# denylist and returns '' for Latin.
#
# The test is two or more consecutive English words of three-plus letters. That
# is deliberately narrow, for the same reason OPEN-26's guard is
# direction-sensitive: Japanese carries single Latin tokens all the time —
# Wi-Fi, eSIM, AV機器, OK, PDF — and rejecting those would reject correct
# Japanese. Two English words in a row is a clause, not a loanword.
_ENGLISH_CLAUSE = re.compile(r'[A-Za-z]{3,}(?:[\s,]+[A-Za-z]{2,}){1,}')


def find_english_clause(text: str, language: str) -> str:
    """An English clause inside a Japanese sentence, or '' if there is none."""
    if language.strip().lower() not in ('japanese', 'ja') or not text:
        return ''
    if not _KANA_OR_KANJI.search(text):
        return ''          # not a Japanese sentence at all; not this rule's job
    match = _ENGLISH_CLAUSE.search(text)
    return match.group(0) if match else ''


# A single English word spliced into a Japanese sentence, which the clause rule
# above is too narrow to see: it needs two Latin words in a row, and a playtest
# found 「出口はどのsideroadに面していますか？」 and
# 「今日何時にお取り寄せbecomeする予定ですか？」 — one word each, reaching the
# learner as target-language text.
#
# The discriminator is CASE, not the word. Every counter-example the clause
# rule was kept narrow for is capitalised or an acronym — Wi-Fi, eSIM, PDF,
# OK, JR, ATM, Tシャツ, Suica — and Japanese writes its genuine Latin tokens
# that way. A run of three or more all-lowercase Latin letters inside a
# Japanese sentence is the leak.
_LOWERCASE_LATIN_WORD = re.compile(r'(?<![A-Za-z])[a-z]{3,}(?![A-Za-z])')

# Lowercase Latin that IS Japanese. Empty on purpose so far — nothing has
# earned a slot. Add only with a sentence that proves it.
_LOWERCASE_LATIN_OK = ()


def find_english_word(text: str, language: str) -> str:
    """One lowercase English word inside a Japanese sentence, or ''."""
    if language.strip().lower() not in ('japanese', 'ja') or not text:
        return ''
    if not _KANA_OR_KANJI.search(text):
        return ''          # not a Japanese sentence at all; not this rule's job
    for match in _LOWERCASE_LATIN_WORD.finditer(text):
        if match.group(0) not in _LOWERCASE_LATIN_OK:
            return match.group(0)
    return ''


def sentence_rejection_reason(sentence: str, language: str='') -> str:
    """Why one spoken sentence must not reach the learner, or '' if it may.

    The single place the per-sentence actor rules live. `validate` (whole
    assembled turn) and `stream_actor`'s `process_spoken` (mid-stream, before
    the callback fires) both dispatch here, so a rule added here binds both
    paths at once. They used to carry separate copies, which is how the
    residual-markup rule sat dead on the streamed path while `validate`
    rejected the very same assembled text (OPEN-13a, OPEN-16).
    """
    leaked = find_wrong_script(sentence, language)
    if leaked:
        return f'Wrong script for {language}: {leaked}'
    english = find_english_clause(sentence, language)
    if english:
        return f'English clause in {language}: {english[:40]}'
    word = find_english_word(sentence, language)
    if word:
        return f'English word in {language}: {word[:40]}'
    if re.search(EMOJI_PATTERN, sentence):
        return 'Contains emoji'
    if re.search(r'[*\[\]<>]', sentence):
        return 'Contains residual markup characters'
    if is_closed_question(sentence):
        return 'Closed yes/no question'
    return ''


def validate(text: str, max_sentences: int=3, language: str='') -> tuple[bool, str]:
    """Check sanitized actor output against format rules.

    `language` is optional and defaults to no script check, so callers that do
    not know it behave exactly as before.
    """
    if not text:
        return (False, 'Empty response')
    # Checked against the FULL text, before the vocab block is stripped below:
    # most leakage is inside the vocab explanation, so checking spoken_only
    # would miss the majority of it.
    leaked = find_wrong_script(text, language)
    if leaked:
        return (False, f'Wrong script for {language}: {leaked}')
    # Strip vocab block (both explicit <vocab> tags and fallback word/explanation/encourage block)
    spoken_only = strip_vocab_block(text)
    sentences = [s.strip() for s in re.split('(?<=[.!?。！？])\\s*', spoken_only) if s.strip()]
    # Counted before the per-sentence rules so the dominant rejection reason
    # keeps its current attribution: emoji and markup are measured near-zero on
    # real output, over-length is the common failure, and the reason string is
    # what the retry note and the eval logs read.
    if len(sentences) > max_sentences:
        return (False, f'Too many sentences ({len(sentences)})')

    for sentence in sentences:
        reason = sentence_rejection_reason(sentence, language)
        if reason:
            return (False, reason)
    return (True, '')
