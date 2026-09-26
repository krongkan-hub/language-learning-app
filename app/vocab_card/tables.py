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
