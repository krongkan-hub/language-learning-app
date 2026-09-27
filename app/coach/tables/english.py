"""English word tables for the coach. Data only — no functions.

Each table is read by one rule, named in its section header.
"""

# ── verb-form net  (app/coach/nets/english.py) ──────────────────────────────

# present form -> past form. Only verbs whose present form is not also a common
# noun ("work", "order", "book", "call" are deliberately absent: "last week's
# work" must not look like a verb).
_PAST_OF = {
    'buy': 'bought', 'go': 'went', 'goes': 'went', 'eat': 'ate', 'eats': 'ate',
    'see': 'saw', 'sees': 'saw', 'come': 'came', 'comes': 'came',
    'take': 'took', 'takes': 'took', 'get': 'got', 'gets': 'got',
    'give': 'gave', 'gives': 'gave', 'find': 'found', 'finds': 'found',
    'meet': 'met', 'meets': 'met', 'pay': 'paid', 'pays': 'paid',
    'drive': 'drove', 'drives': 'drove', 'write': 'wrote', 'writes': 'wrote',
    'speak': 'spoke', 'speaks': 'spoke', 'break': 'broke', 'breaks': 'broke',
    'lose': 'lost', 'loses': 'lost', 'leave': 'left', 'leaves': 'left',
    'bring': 'brought', 'brings': 'brought', 'catch': 'caught',
    'catches': 'caught', 'teach': 'taught', 'teaches': 'taught',
    'think': 'thought', 'thinks': 'thought',
    'forget': 'forgot', 'forgets': 'forgot', 'send': 'sent', 'sends': 'sent',
    'spend': 'spent', 'spends': 'spent', 'wear': 'wore', 'wears': 'wore',
    'choose': 'chose', 'chooses': 'chose', 'arrive': 'arrived',
    'arrives': 'arrived', 'travel': 'travelled', 'travels': 'travelled',
    'visit': 'visited', 'visits': 'visited', 'stay': 'stayed',
    'stays': 'stayed', 'walk': 'walked', 'walks': 'walked',
}

# ── spelling net  (app/coach/nets/spelling.py) ──────────────────────────────

_JOINED = {
    'dont': "don't", 'didnt': "didn't", 'doesnt': "doesn't", 'isnt': "isn't",
    'arent': "aren't", 'wasnt': "wasn't", 'werent': "weren't",
    'couldnt': "couldn't", 'wouldnt': "wouldn't", 'shouldnt': "shouldn't",
    'havent': "haven't", 'hasnt': "hasn't", 'hadnt': "hadn't", 'cant': "can't",
    'alot': 'a lot', 'afew': 'a few', 'upto': 'up to', 'infront': 'in front',
    'aswell': 'as well', 'eachother': 'each other', 'incase': 'in case',
    'atleast': 'at least', 'noone': 'no one',
}

# A regular -ed on an irregular verb: the learner's error is the tense, and
# one edit away from "readed" is "reader", which is wrong in a new way.
# Forms that are real words ("payed", "leaved", "shined") are left out.
_PAST = {
    'readed': 'read', 'buyed': 'bought', 'goed': 'went', 'eated': 'ate',
    'teached': 'taught', 'thinked': 'thought', 'catched': 'caught',
    'bringed': 'brought', 'runned': 'ran', 'swimmed': 'swam',
    'writed': 'wrote', 'speaked': 'spoke', 'taked': 'took', 'maked': 'made',
    'gived': 'gave', 'comed': 'came', 'knowed': 'knew', 'drinked': 'drank',
    'sleeped': 'slept', 'feeled': 'felt', 'keeped': 'kept', 'meeted': 'met',
    'sayed': 'said', 'sended': 'sent', 'spended': 'spent', 'telled': 'told',
    'finded': 'found', 'getted': 'got', 'hurted': 'hurt', 'cutted': 'cut',
    'choosed': 'chose', 'drived': 'drove', 'falled': 'fell',
    'forgetted': 'forgot', 'growed': 'grew', 'holded': 'held', 'losed': 'lost',
    'rided': 'rode', 'selled': 'sold', 'standed': 'stood', 'stealed': 'stole',
    'throwed': 'threw', 'understanded': 'understood', 'weared': 'wore',
    'winned': 'won', 'breaked': 'broke', 'builded': 'built', 'drawed': 'drew',
    'fighted': 'fought', 'hided': 'hid', 'sitted': 'sat', 'beginned': 'began',
}

# Informal or borrowed words a learner types on purpose, each one seen
# "corrected" into a real word it is not ("matcha" -> "match"). The Thai
# romanizations are there because this app's learners order Thai food in
# English: "tom yum goong" came back as "tom yum going". Only the ones seen
# firing are listed; ~100 others (pad, kaprao, onsen, izakaya...) already
# pass as non-words with no confident correction.
_ALLOW = {'yall', 'matcha', 'okey', 'aight',
          'goong', 'laab', 'muay', 'sanuk', 'aroy', 'gaeng', 'keow'}

# ── plural net  (app/coach/nets/plural.py) ──────────────────────────────────

_NUMBER = frozenset(
    'two three four five six seven eight nine ten eleven twelve twenty thirty '
    'forty fifty hundred thousand several many few'.split())

_PHRASE_END = frozenset(
    'please too to for of in at on from with now today tonight here there '
    'then ago later each total left'.split())

_NOT_A_NOUN = frozenset(
    'more less other different new good same last first next dozen or and '
    'hundred thousand million times people percent'.split())

# ── feedback filter  (app/coach/filters.py) ─────────────────────────────────

# The words a politeness rewrite adds, swaps or drops. Strip them from both
# sides and a pure register polish leaves the same sentence behind:
# "Can I pay by card?" / "May I pay by card, please?" -> "pay by card".
# Anything left over is a real change — "explain me" / "explain to me" keeps
# its "to" — and the bullet stays a correction whatever its reason says.
_POLITENESS_WORDS = frozenset(
    "can could may might would will please kindly possibly i i'd you we "
    "want have get like also just".split())

# A correction may INFLECT what the learner wrote ("two bottle" -> "two
# bottles", "is prohibit" -> "is prohibited") and may add function words, but it
# may not introduce a CONTENT word they never used. Stem-matching on a prefix
# handles the inflection cases without a morphology library.
#
# Why it exists — the coach completing the learner's thought, and the no-skip
# drill then making them type it: BACKLOG OPEN-38.
_FUNCTION_WORDS = set(
    "a an the this that these those my your his her its our their "
    "i you he she it we they me him us them "
    "is am are was were be been being do does did have has had "
    "will would shall should can could may might must "
    "to of in on at by for with from into onto about over under "
    "and or but so if then than as not no yes please thank thanks "
    "there here it's i'd i'll i'm we'd we'll let lets".split())

# Irregular verbs, every form -> its base. _introduces_new_content counts a word
# as the learner's own when the two share four letters, which is how "studied"
# vouches for "study" — but "paid" and "pay" share three, so the model's correct
# fix of "Can I paid by card?" was dropped as a rewrite and the learner was told
# the sentence was perfectly natural. Same for went/go, bought/buy, ate/eat.
_IRREGULAR = {
    'be': 'am is are was were been being', 'go': 'goes went gone going',
    'buy': 'buys bought buying', 'pay': 'pays paid paying',
    'eat': 'eats ate eaten eating', 'see': 'sees saw seen seeing',
    'come': 'comes came coming', 'take': 'takes took taken taking',
    'get': 'gets got gotten getting', 'give': 'gives gave given giving',
    'find': 'finds found finding', 'meet': 'meets met meeting',
    'drive': 'drives drove driven driving', 'write': 'writes wrote written writing',
    'speak': 'speaks spoke spoken speaking', 'break': 'breaks broke broken breaking',
    'lose': 'loses lost losing', 'leave': 'leaves left leaving',
    'bring': 'brings brought bringing', 'catch': 'catches caught catching',
    'teach': 'teaches taught teaching', 'think': 'thinks thought thinking',
    'forget': 'forgets forgot forgotten forgetting', 'send': 'sends sent sending',
    'spend': 'spends spent spending', 'wear': 'wears wore worn wearing',
    'choose': 'chooses chose chosen choosing', 'do': 'does did done doing',
    'have': 'has had having', 'make': 'makes made making', 'say': 'says said saying',
    'tell': 'tells told telling', 'know': 'knows knew known knowing',
    'run': 'runs ran running', 'sit': 'sits sat sitting', 'stand': 'stands stood standing',
    'sell': 'sells sold selling', 'hold': 'holds held holding', 'feel': 'feels felt feeling',
    'keep': 'keeps kept keeping', 'sleep': 'sleeps slept sleeping',
    'drink': 'drinks drank drunk drinking', 'swim': 'swims swam swum swimming',
    'begin': 'begins began begun beginning', 'win': 'wins won winning',
    'fly': 'flies flew flown flying', 'fall': 'falls fell fallen falling',
    'grow': 'grows grew grown growing', 'throw': 'throws threw thrown throwing',
    'understand': 'understands understood understanding', 'build': 'builds built building',
    'lend': 'lends lent lending', 'ride': 'rides rode ridden riding',
    'steal': 'steals stole stolen stealing', 'hide': 'hides hid hidden hiding',
    'fight': 'fights fought fighting', 'draw': 'draws drew drawn drawing',
    'hear': 'hears heard hearing', 'read': 'reads reading', 'put': 'puts putting',
    'cut': 'cuts cutting', 'hurt': 'hurts hurting', 'let': 'lets letting',
    'set': 'sets setting', 'cost': 'costs costing', 'shut': 'shuts shutting',
    'lie': 'lies lay lain lying', 'lay': 'lays laid laying', 'bite': 'bites bit bitten biting',
    'shake': 'shakes shook shaken shaking', 'wake': 'wakes woke woken waking',
    'sing': 'sings sang sung singing', 'ring': 'rings rang rung ringing',
    'mean': 'means meant meaning', 'light': 'lights lit lighting',
    'good': 'better best', 'bad': 'worse worst', 'many': 'more most', 'much': 'more most',
    'child': 'children', 'person': 'people', 'man': 'men', 'woman': 'women',
    'foot': 'feet', 'tooth': 'teeth', 'mouse': 'mice',
}


# ── article net  (app/coach/nets/article.py) ────────────────────────────────

# "an" is right before these consonant letters: the h is silent.
_AN_BEFORE_CONSONANT = ('hour', 'honest', 'honor', 'honour', 'heir', 'herb')

# "a" is right before these vowel letters: they are said with a consonant
# sound (a university, a European, a one-way ticket, a user).
_A_BEFORE_VOWEL = ('uni', 'use', 'usu', 'uti', 'ure', 'eu', 'one', 'once', 'ewe',
                   'ufo', 'uranium', 'ubiq', 'ukr', 'urin')

# After "a"/"an", these mean the letter, not the article — "option a or b",
# "plan a in the brief" — and are never corrected.
_NOT_AFTER_ARTICLE = frozenset(
    'and or of in on at to for by as is if so but up out off from with than'.split())

# Reflexive pronouns written as two words: "by my self" -> "by myself".
# Not before a hyphen: "my self-esteem" is a different word.
_SPLIT_REFLEXIVES = {
    'my self': 'myself', 'your self': 'yourself', 'him self': 'himself',
    'her self': 'herself', 'it self': 'itself', 'our selves': 'ourselves',
    'your selves': 'yourselves', 'them selves': 'themselves',
}
