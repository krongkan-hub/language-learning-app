"""English spelling net. Only ever overturns a CLEAN verdict.

See BACKLOG OPEN-50: on JFLEG the coach called 「I guduate in university .」,
「nowdays」 and 「manufatures」 perfectly natural — COACH_SYS names a real
spelling mistake as a Feedback bullet, and the model still let them through.
Prompt levers on this model have measured inert three times running; the
nets that moved a number were code. This is one.

How a token becomes a correction, each step there because a measurement on
JFLEG dev said so (dev/tools/probe_spelling_jfleg.py reruns it):

  1. It is not a word. "Word" is wide on purpose: SCOWL up to size 80, a
     regular -s/-es/-ly of a common word (SCOWL has "watches" but not
     "attaches"), anything in the scenario catalogue (a learner echoes the
     NPC's "terroir" and "macaron"), and a short allowlist of informal words.
     Capitalised mid-sentence tokens are names and are never touched.
  2. Exactly one COMMON word (SCOWL <= 20) is one edit away, or one is
     strictly commoner than the rest, AND it keeps the first letter —
     "hazzle" -> "dazzle" was the shape that rule removed. Words 20-35 were
     tried: the corrections they added were 68% right, below this net's bar.
  3. A few closed shapes win before that: a negation with its apostrophe
     dropped ("dont"), two words run together ("alot", "upto"), a regular
     past on an irregular verb ("readed" -> "read", not "reader"), "-aly"
     for "-ally", "-ys" for "-ies", and a plural kept plural ("medicins" ->
     "medicines").

Measured on JFLEG (1,501 sentences by real learners, four native
corrections each): the correction matches an annotator's 91.6% of the time on
dev and 87.3% on test by a strict string rule, and reading the misses on test
by hand, about half are the right word where the annotator rewrote the whole
phrase. It fires on 0 of the 67 sentences all four annotators left alone.
"""
import functools
import gzip
import json
import os
import re

from ..verdict import is_clean_verdict


_DATA = os.path.join(os.path.dirname(__file__), 'data', 'en_words.txt.gz')
_SCENARIOS = os.path.join(os.path.dirname(__file__), '..', '..', 'scenarios', 'data')

_KNOWN_MAX = 80        # a SCOWL level this common or commoner is a word
_CANDIDATE_MAX = 20    # a correction must be at least this common
_MIN_LEN = 4           # "teh"/"hte" are too ambiguous to guess at

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

_TOKEN = re.compile(r'[A-Za-z]+')
_ALPHABET = 'abcdefghijklmnopqrstuvwxyz'


@functools.lru_cache(maxsize=1)
def _levels() -> dict:
    with gzip.open(_DATA, 'rt', encoding='ascii') as f:
        return {w: int(lvl) for lvl, w in (line.rstrip('\n').split('\t') for line in f)}


@functools.lru_cache(maxsize=1)
def _catalogue_words() -> frozenset:
    words = set()

    def walk(node):
        if isinstance(node, str):
            words.update(w.lower() for w in _TOKEN.findall(node))
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    try:
        names = os.listdir(_SCENARIOS)
    except OSError:
        return frozenset()
    for name in names:
        if name.endswith('.json'):
            with open(os.path.join(_SCENARIOS, name), encoding='utf-8') as f:
                walk(json.load(f))
    return frozenset(words)


def _level(word: str) -> int:
    return _levels().get(word, 99)


def _is_word(lw: str) -> bool:
    if _level(lw) <= _KNOWN_MAX or lw in _ALLOW or lw in _catalogue_words():
        return True
    # A regular inflection of a common stem. "es" only where English spells
    # it, and never "-ys" after a consonant: "familys" is the error itself.
    stem = None
    if lw.endswith('ies'):
        stem = lw[:-3] + 'y'
    elif re.search(r'(s|x|z|ch|sh|o)es$', lw):
        stem = lw[:-2]
    elif lw.endswith('s') and not lw.endswith('ss') and not re.search(r'[^aeiou]ys$', lw):
        stem = lw[:-1]
        if stem.endswith('er') and _level(stem[:-2]) <= 35:
            stem = None                      # "smallers"
    stems = ([stem] if stem else []) + ([lw[:-2]] if lw.endswith('ly') else [])
    return any(len(s) >= 4 and _level(s) <= 35 for s in stems)


def _edits1(w: str) -> set:
    splits = [(w[:i], w[i:]) for i in range(len(w) + 1)]
    return set([a + b[1:] for a, b in splits if b]
               + [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
               + [a + c + b[1:] for a, b in splits if b for c in _ALPHABET]
               + [a + c + b for a, b in splits for c in _ALPHABET])


def _best(lw: str):
    """The single most likely common word one edit away, or None if unsure."""
    ranked = sorted((_level(c), c) for c in _edits1(lw)
                    if _level(c) <= _CANDIDATE_MAX and c[0] == lw[0])
    if not ranked or (len(ranked) > 1 and ranked[1][0] == ranked[0][0]):
        return None
    return ranked[0][1]


def _correct(lw: str):
    if lw.endswith('aly') and _level(lw[:-3] + 'ally') <= _CANDIDATE_MAX:
        return lw[:-3] + 'ally'
    if re.search(r'[^aeiou]ys$', lw) and _level(lw[:-2] + 'ies') <= _CANDIDATE_MAX:
        return lw[:-2] + 'ies'
    if lw.endswith('s') and len(lw) > 5:
        base = _best(lw[:-1])
        if base and not base.endswith('s') and _level(base + 's') <= _KNOWN_MAX:
            return base + 's'
    return _best(lw)


def spelling_corrections(text: str) -> list:
    """(as written, corrected) for every misspelling this net is sure of."""
    found = []
    for m in _TOKEN.finditer(text):
        word, lw = m.group(0), m.group(0).lower()
        before = text[m.start() - 1] if m.start() else ''
        after = text[m.end()] if m.end() < len(text) else ''
        if {before, after} & {"'", '\u2019', '\u2018'}:
            continue                          # a piece of "don't" / "it's"
        if lw in _JOINED:
            fixed = _JOINED[lw]
        elif lw in _PAST:
            fixed = _PAST[lw]
        else:
            if len(word) < _MIN_LEN or (word.isupper() and len(word) > 1):
                continue
            if word[0].isupper() and text[:m.start()].strip():
                continue                      # a name, not a typo
            if _is_word(lw):
                continue
            # "sooo", "Heyy": stretched on purpose, not misspelled.
            if re.search(r'(.)\1\1', lw) or (lw[-1] == lw[-2] and _is_word(lw[:-1])):
                continue
            fixed = _correct(lw)
            if not fixed:
                continue
        if word[0].isupper():
            fixed = fixed[0].upper() + fixed[1:]
        if (word.lower(), fixed.lower()) not in {(w.lower(), f.lower()) for w, f in found}:
            found.append((word, fixed))
    return found


def _reason(was: str, now: str) -> str:
    if was.lower() in _PAST:
        return f'an irregular verb: the past tense is "{now.lower()}"'
    if "'" in now:
        return 'a contraction needs its apostrophe'
    if ' ' in now:
        return 'two separate words'
    return 'spelling'


def apply_spelling_net(feedback: str, user_input: str, language: str) -> str:
    """Catch an English misspelling the coach called natural."""
    if language != 'English' or not is_clean_verdict(feedback, language):
        return feedback
    fixes = spelling_corrections(user_input)
    if not fixes:
        return feedback
    lines = '\n'.join(f'- ❌ "{was}" → ✅ "{now}" ({_reason(was, now)})'
                      for was, now in fixes[:2])
    return '\U0001f4a1 Feedback:\n' + lines
