"""The word and character tables the guards in app/llm/guards.py read.

Data only — no functions. Each table says what it is for and why it holds
what it holds; the rules that use them live in guards.py.
"""

# ── English question shape ───────────────────────────────────────────────

# 'shall' was missing until the parity check in dev/checks/check_rule_vacuity.py
# flagged it on its first run: "Shall I help you?" passed while its Japanese
# twin 「お手伝いしましょうか？」 was correctly caught. For once the vacuous side
# was the English list, not the Japanese branch — which is the argument for
# parity over a one-directional "does it work on Japanese" test.
# A sentence opening with one of these (and carrying no wh-word) is a yes/no
# question, which the NPC is not allowed to ask.
CLOSED_OPENERS = {
    'am', 'is', 'are', 'was', 'were',
    'do', 'does', 'did', 'have', 'has',
    'can', 'could', 'will', 'would', 'should', 'shall', 'may',
    'want', 'need',
}

# A wh-word anywhere in the sentence makes it an OPEN question.
WH_WORDS = {'what', 'why', 'how', 'which', 'where', 'when', 'who'}

# Emoji the NPC must never write (stripped from its turns, rejected by validate).
EMOJI_PATTERN = r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u27BF]'


# ── Japanese question shape ──────────────────────────────────────────────

# Interrogatives that make a か-question OPEN. いかが is here for parity with
# English: "How about a coffee?" opens with a wh-word and passes, so
# 「コーヒーはいかがですか」 must too.
_JA_INTERROGATIVES = ('何', 'なに', 'なん', 'どこ', 'いつ', '誰', 'だれ', 'どちら', 'どっち',
                      'どの', 'どれ', 'どう', 'どんな', 'いくつ', 'いくら', 'なぜ', 'いかが')
# Ends in か but is an acknowledgement, not a question — without this it would
# be rejected as a closed one.
_JA_NOT_QUESTIONS = ('そうですか',)


# ── Characters that are never Japanese ──────────────────────────────────

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


# ── Latin inside Japanese ────────────────────────────────────────────────

# Lowercase Latin that IS Japanese. Empty on purpose so far — nothing has
# earned a slot. Add only with a sentence that proves it.
_LOWERCASE_LATIN_OK = ()
