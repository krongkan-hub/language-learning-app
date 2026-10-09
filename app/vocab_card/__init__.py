"""The vocabulary card: parse it from an NPC turn and decide whether to show it.

Used by the web turn workers (app/web/turns.py). A card is dropped when its word is
trivial (a stopword or a word from the scenario's own name), a venue or job
title (修理店, 運転手), or a name the NPC used — see the tables in tables.py.
"""
from typing import Optional
from ..i18n import t
from ..llm import match_vocab_fields
from ..llm.guards import reads_as_chinese
from ..scenarios.models import Scenario
import re


from ..lexicon import level
from .tables import (EVERYDAY_MAX_LEVEL, NOUN_CAPITALIZING_LANGUAGES, ROOM_SUFFIX_MIN_LEN, STOPWORDS,
                     VENUE_ROLE_SUFFIXES)


CJK_CHARS = re.compile(r'[぀-ヿ㐀-䶿一-鿿]')


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOPWORDS and len(w) > 2}


def _is_trivial_vocab(word: str, scenario: Optional[Scenario]) -> bool:
    """True when candidate word appears in scenario's name, place, role, or speaker (case-insensitive & stemmed)."""
    if not scenario or not word:
        return False
    identity = _words(f"{scenario.name} {scenario.place} {scenario.role} {scenario.speaker}")
    word_clean = word.strip().lower()
    if not word_clean:
        return False
    if word_clean in identity or any(word_clean == w.rstrip('s') or w == word_clean.rstrip('s') for w in identity):
        return True
    cand_tokens = _words(word_clean)
    for cw in cand_tokens:
        if cw in identity or any(cw == w.rstrip('s') or w == cw.rstrip('s') for w in identity):
            return True
    return False


def _is_everyday_word(word: str, language: str) -> bool:
    """True for an English card whose words are all among the commonest in
    the language (SCOWL size <= EVERYDAY_MAX_LEVEL): nothing to teach a C1
    learner, and three uses of it would be needed to clear it from review.
    A word SCOWL does not list (NOT_A_WORD) is never everyday."""
    if language != 'English':
        return False
    # Single words only. A phrase built from everyday words — "take off",
    # "put up with", "floor-to-ceiling" — is often exactly the C1 idiom the
    # prompt asks for, and its parts' commonness says nothing about it.
    parts = re.findall(r'[a-z]+', word.lower())
    if len(parts) != 1 or not re.fullmatch(r'[A-Za-z]+', word.strip()):
        return False

    def commonest(part):
        forms = [part]
        for suffix, repl in (('ies', 'y'), ('es', ''), ('s', ''), ('ing', ''), ('ing', 'e'), ('ed', ''), ('ed', 'e')):
            if part.endswith(suffix) and len(part) - len(suffix) >= 3:
                forms.append(part[:-len(suffix)] + repl)
        return min(level(f) for f in forms)

    return all(commonest(p) <= EVERYDAY_MAX_LEVEL for p in parts)


def _is_venue_noun(word: str) -> bool:
    """True when the word names the kind of place or job the NPC already is.

    `_is_trivial_vocab` compares the word against the scenario's identity, but
    that identity is stored in English while a Japanese tip is Japanese, so
    `_words` tokenizes it to the empty set and the comparison can never match —
    measured on 108 captured Japanese cards, it caught 0 of the 23 junk tips
    written in Japanese script.

    A translated identity is available (`scenario_name`/`scenario_place`), but
    comparing against it scored worse than this rule on the same corpus: the
    translations are partly Chinese or garbled, and the good ones embed ordinary
    vocabulary (旅行情報センター contains 旅行, 現代美術ギャラリー contains 美術),
    so it dropped 10 legitimate cards to catch 13 junk ones. Matching the word's
    own shape instead caught 16 with no legitimate card lost.
    """
    word_clean = word.strip()
    if len(word_clean) < 2 or not CJK_CHARS.search(word_clean):
        return False
    # Every suffix is also a standing common noun — 受付 alone is "a reception
    # desk" — while the junk tips are always compounds naming one specific venue
    # (緊急医療受付, 動物病院), so require the word to outgrow its own suffix.
    for suffix in VENUE_ROLE_SUFFIXES:
        if word_clean.endswith(suffix) and len(word_clean) > len(suffix):
            return True
    return len(word_clean) >= ROOM_SUFFIX_MIN_LEN and word_clean.endswith('室')


_QUESTION = re.compile(r'[?？]\s*$|(ますか|ですか|でしょうか)\s*$')


def _is_question(word: str) -> bool:
    """True when the "word" is a whole question lifted from the dialogue.

    Playtest 2026-09-27: the NPC opened with the ungrammatical
    今日は何をお探しいただけますか, and the card then taught
    「お探しいただけますか」 as the word of the turn — a broken clause, in a
    teaching slot. A question is never a vocabulary item; a set phrase that
    is (お願いします, "put up with") does not end like one.
    """
    return bool(_QUESTION.search(word.strip()))


def _is_name(word: str, dialogue: str, language: str) -> bool:
    """True when the vocab word is a proper noun rather than reusable vocabulary.

    A name — the venue, the NPC, a brand, a city — teaches the learner nothing
    they can carry to another conversation. The actor prompt forbids picking
    one; this is the backstop for when the model does it anyway. Capitalization
    alone is too weak a signal, since the model also capitalizes ordinary words
    in the vocab field, so we additionally require the word to appear
    capitalized mid-sentence in the NPC's own dialogue — which only an
    inherently capitalized word does. Scripts without letter case (Japanese,
    Chinese) never match and are unaffected.

    The NOUN_CAPITALIZING_LANGUAGES guard cannot fire in production —
    normalize_language admits English and Japanese only and main() exits on
    anything else (OPEN-34). It is kept as the backstop for the day a third
    language is admitted, since German capitalizes every noun and would make
    this whole heuristic fire on ordinary vocabulary.
    """
    if language.strip().lower() in NOUN_CAPITALIZING_LANGUAGES:
        return False
    tokens = re.findall(r'[^\W\d_]+', word)
    if not tokens or not all(t[0].isupper() for t in tokens):
        return False
    return bool(re.search(r'[^.!?]\s+' + re.escape(word), dialogue))


# The vocab block's shape — including the tolerant third label — lives in
# app/llm.py so the actor paths and the CLI cannot disagree about what a card
# is. It was defined in both places once, and they diverged (OPEN-31).
_match_vocab = match_vocab_fields


def parse_vocab(text: str) -> Optional[tuple[str, str, str]]:
    """Parse (word, explanation, encourage) from text with or without <vocab> tags, or return None."""

    if not text:
        return None
    match = _match_vocab(text)
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    return None


def extract_and_format_vocab(text: str, language: str = "", scenario: Optional[Scenario] = None) -> tuple[str, str]:
    """Extract vocab blocks from text (with or without <vocab> tags) and return (clean_text, formatted_vocab_box).

    A tip whose word is a proper noun or trivial scenario word is dropped: the block is still stripped
    from the dialogue, but no box is returned.
    """
    vocab_box = ""
    match = _match_vocab(text)
    if match:
        word_text = match.group(1).strip()
        exp_text = match.group(2).strip()
        enc_text = match.group(3).strip()

        if match:
            text = (text[:match.start()] + " " + text[match.end():]).strip()
            text = re.sub(r'</?vocab>', '', text, flags=re.IGNORECASE).strip()
            text = re.sub(r'\s+', ' ', text)

        if (not _is_name(word_text, text, language)
                and not _is_trivial_vocab(word_text, scenario)
                and not _is_venue_noun(word_text)
                and not _is_question(word_text)
                and not (language == 'Japanese' and reads_as_chinese(exp_text))
                and not _is_everyday_word(word_text, language)):
            vocab_box = t('vocab_tip_box', language, word=word_text, exp=exp_text, enc=enc_text)

    return text, vocab_box


def words_used(text: str, words, language: str) -> list:
    """Which of `words` the learner's `text` uses, in the order given.

    Using a taught word in conversation is how a word is practised now that
    the web is the only front end (the CLI's warm-up quiz was the only other
    way, and it was retired with the CLI). English matches the whole word or
    phrase, allowing a regular -s/-es/-d/-ed/-ing; Japanese has no spaces, so
    it matches the word as written — but only words of two or more
    characters, or 水 would be "used" in every 水曜日.
    """
    found = []
    for word in words:
        w = (word or '').strip()
        if not w:
            continue
        if language == 'Japanese':
            hit = len(w) >= 2 and w in text
        else:
            hit = re.search(r'(?<![A-Za-z])' + re.escape(w) + r'(?:s|es|d|ed|ing)?(?![A-Za-z])',
                            text, re.IGNORECASE)
        if hit:
            found.append(word)
    return found
