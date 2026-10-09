"""Is this the language we asked for, and is it a usable sentence?

Script checks, question shape, and the validator the actor is held to.
The rules here are narrow on purpose — a guard that rejects correct output
costs the learner the turn. See BACKLOG OPEN-22, OPEN-26, OPEN-35, OPEN-40.
"""
import re

from .client import strip_think_tags
from .tables import (CLOSED_OPENERS, EMOJI_PATTERN, WH_WORDS,
                     _FOREIGN_SCRIPT_RANGES, _JA_INTERROGATIVES, _JA_NOT_QUESTIONS,
                     _LOWERCASE_LATIN_OK, _SIMPLIFIED_CHARS, _SIMPLIFIED_RANGES,
                     _TRADITIONAL_CHARS, PRESUPPOSES_A_REQUEST)
from .vocab import strip_vocab_block

# Japanese character classes, shared with translate.py, which owns them
_KANA_OR_KANJI = re.compile(r'[\u3040-\u30FF\u4E00-\u9FFF]')


# Where one sentence ends and the next begins. Japanese 。！？ end a sentence
# outright; ASCII .!? only when whitespace follows, because the same character
# sits inside "$3.50", "3.5 km" and "U.S.A". Splitting on the bare character
# turned "Each latte is $3.50" into two sentences — "$3." and "50 ..." — which
# the learner saw as "$3. 50", and which spent one of the turn's three
# sentences on half a price. Every splitter in app/llm reads this one pattern.
# Half-width !/? between Japanese characters still ends a sentence — Japanese
# has no space to wait for, and "はい!わかりました!" is two sentences. A "."
# there is not included: that is where a decimal point would be.
SENTENCE_BREAK = re.compile(
    r'(?<=[。！？])\s*|(?<=[.!?])\s+|(?<=[!?])(?=[\u3040-\u30ff\u4e00-\u9fff])')


def split_sentences(text: str) -> list:
    """The non-empty, stripped sentences of `text`."""
    return [s.strip() for s in SENTENCE_BREAK.split(text) if s.strip()]


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
    """Strip system directive injection tokens from learner input.

    Repeated until nothing changes: one pass turned '<sys<system>tem>' into
    '<system>' and '<<|x|>|im_start|>' into '<|im_start|>' (security review
    2026-09-27)."""
    cleaned = user_input
    while True:
        before = cleaned
        cleaned = re.sub(r'<\|.*?\|>', '', cleaned)
        cleaned = re.sub(r'\[System:.*?\]', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'</?(?:system|user|assistant|think|vocab)>', '', cleaned, flags=re.IGNORECASE)
        if cleaned == before:
            return cleaned.strip()

# Japanese question detection. A polite question ends in か; it is OPEN when it
# carries an interrogative, and closed otherwise. Mirrors the English rule,
# where a wh-word likewise rescues a sentence from the closed-opener test.
# The word lists are _JA_INTERROGATIVES and _JA_NOT_QUESTIONS in tables.py.

_JA_KANA = re.compile('[ぁ-んァ-ヴ]')
_JA_QUESTION_END = re.compile('か[。．.？?！!\\s]*$')

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


# A request that asks the learner to TELL something is as answerable as a
# question. The stream path treated it as a statement: at the last slot it
# was dropped, and a canned salvage question took its place — replaying
# recorded turns, 「まずは車の問題を詳しく教えてください。」 ("tell me about the
# problem with your car") was deleted for "What else can I do for you?"-style
# filler (OPEN-52).
_EN_INVITE = re.compile(
    r"^(?:(?:so|now|first|then|okay|ok|alright|well),?\s+)?(?:please\s+)?"
    r"(?:tell|show|describe|explain|walk me through|let me know|talk me through)\b", re.I)
_JA_INVITE = re.compile(
    r'(?:教えて|聞かせて|知らせて|見せて|話して|伝えて|おっしゃって|お聞かせ|お知らせ|お教え|お見せ)'
    r'(?:ください|下さい)(?:ませ)?[。！!]?\s*$')


def invites_reply(sentence: str) -> bool:
    """A question, or a request that the learner tell or show something."""
    s = sentence.strip()
    return is_question(s) or bool(_EN_INVITE.search(s) or _JA_INVITE.search(s))


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


_HIRAGANA = re.compile('[\u3041-\u309f]')
_HAN = re.compile('[\u4e00-\u9fff]')


def reads_as_chinese(text: str) -> bool:
    """A run of six-plus kanji with no hiragana at all: Chinese written in
    characters Japanese shares (是, 的, 指, 意思), which find_wrong_script
    cannot see because none of them is simplified-only. 16 of 76 Japanese
    vocab-card explanations read like 「眼鏡店是指出售和配戴眼鏡的地方」
    (eval_rawactor samples, 2026-10-09). A Japanese explanation of that
    length always carries hiragana — particles, okurigana, です/ます."""
    return len(_HAN.findall(text)) >= 6 and not _HIRAGANA.search(text)


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
    sentences = split_sentences(spoken_only)
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


_PRESUPPOSES = {lang: re.compile(p, re.IGNORECASE) for lang, p in PRESUPPOSES_A_REQUEST.items()}


def presupposes_a_request(sentence: str, language: str) -> bool:
    """A sentence that only makes sense as a reply to something already asked."""
    pattern = _PRESUPPOSES.get(language)
    return bool(pattern and pattern.search(sentence))
