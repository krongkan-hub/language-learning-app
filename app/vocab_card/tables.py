"""Word tables that decide which vocabulary cards are worth showing. Data only.
"""



# Languages that capitalize every common noun, where a mid-sentence capital
# carries no proper-noun signal and _is_name would reject every valid tip.
NOUN_CAPITALIZING_LANGUAGES = {'german', 'deutsch', 'de', 'luxembourgish'}


STOPWORDS = {
    'a', 'an', 'the', 'you', 'are', 'is', 'at', 'in', 'on', 'of', 'for', 'and',
    'or', 'to', 'with', 'your', 'their', 'this', 'that', 'it', 'as', 'by',
}


# Suffixes that turn a Japanese noun into "a place of business" or "a job
# title": 修理店, 薬局, 歯科医院, 通関事務所, 市場, 緊急医療受付, 運転手,
# 交通警察官. Every entry here was measured to catch a real junk card with no
# false positive; suffixes that only looked plausible are deliberately absent,
# since an unmeasured one is pure over-firing risk.
VENUE_ROLE_SUFFIXES = ('店', '屋さん', '局', '院', '所', '場', '館', '受付', 'センター', '手', '官')


# 室 needs a length floor: it marks a room (緊急室, 保険請求相談室) but also
# ends 個室, which is ordinary vocabulary a learner should keep.
ROOM_SUFFIX_MIN_LEN = 3


# A card whose every word is at or below this SCOWL size (app/lexicon) is an
# everyday word a C1 learner already has — special, machine, session,
# application — and is not shown. Measured on the author's real play history:
# 9 of 23 English cards sat at 10. Size 20 (verify, celebrate, fare) is kept
# on purpose: cutting there hid 18 of 23 cards, and OPEN-19 is the history of
# getting cards to appear at all.
EVERYDAY_MAX_LEVEL = 10
