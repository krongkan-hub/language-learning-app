"""Turning task objectives into the language being studied.

Rejects are retried ONE LINE AT A TIME — a batch primes the model into one
language and a run of Chinese continues as Chinese. See BACKLOG OPEN-40.
"""
import re

from . import client

from .client import strip_think_tags, TRANSLATE_OPTS
from .guards import find_wrong_script


_LATIN_RUN = re.compile(r'[A-Za-z]{2,}')
_KANA_OR_KANJI = re.compile(r'[々぀-ヿ㐀-䶿一-鿿]')


# A sentence break joins too: 「…です。 throatが痛いと…」 has 。 before the
# space, so requiring kana or kanji immediately before the joiner missed it.
_JOINERS = {'-', '\u2010', '\u2013', '\u2014', ' ', '\u3000', '(', '\uff08', '[',
            '\u300c', '\u3002', '\u3001', '\uff1a', '\uff1b'}


def _looks_untranslated(text: str, language: str) -> bool:
    """True when a Latin run is fused to Japanese script, or nothing was translated."""
    if language.strip().lower() not in ('japanese', 'ja'):
        return False
    if not _KANA_OR_KANJI.search(text):
        # Nothing Japanese at all: the line came back in English.
        return bool(_LATIN_RUN.search(text))
    # Direction matters, and only one direction is a defect. Japanese script
    # running straight into Latin — カ+atering, コンフィ+eti, ワ+heelchair — is a
    # transliteration the model abandoned mid-word. Latin running into Japanese
    # is the ordinary way real Japanese carries initialisms and loanwords:
    # Wi-Fiのパスワード, AV技術的な, eSIM. Flagging both directions rejected
    # those, and a false positive here costs a correct translation.
    for m in _LATIN_RUN.finditer(text):
        before = text[m.start() - 1] if m.start() else ''
        if _KANA_OR_KANJI.match(before):
            return True
        # A single joiner defeated the adjacency test above. Seen in a real
        # session: 「ゲートチケットが並び-timeを必要とするか確認してください。」
        # — the hyphen sits between び and the abandoned word, so nothing
        # fired. A space or an opening bracket does the same.
        #
        # Looking through the joiner unconditionally would reject correct
        # Japanese, which carries Latin constantly: 「その VIP パス」 would
        # flag on the space. Case is what separates the two. An abandoned
        # transliteration is a lowercase English word (time, atering, eti);
        # the Latin that belongs in Japanese is an acronym or a brand —
        # VIP, QR, AV, Wi-Fi, eSIM — none of which are all-lowercase.
        if m.start() >= 2 and before in _JOINERS and m.group(0).islower():
            j = m.start() - 1
            while j > 0 and text[j] in _JOINERS:
                j -= 1
            if _KANA_OR_KANJI.match(text[j]):
                return True
    return False


# Bounds the retry above. A session shows ten objectives, and a scenario
# that loses more than six of them to the wrong language has a problem a
# retry will not fix — spending ten more calls on the loading screen to
# find that out is the wrong trade.
TRANSLATE_RETRY_LIMIT = 6


# Chinese that survives find_wrong_script, which is a CODEPOINT table and so
# only sees simplified-only characters. These two are written in kanji Japanese
# uses every day, and both were seen in real runtime translations:
#
#   表演者と VIP ミーティング…      Chinese for 出演者
#   商業品の荷卸詳細と発票価値…     Chinese fāpiào; Japanese is 請求書
#
# Deliberately only what has been OBSERVED. A general rule needs a Japanese
# vocabulary, and a list assembled by guessing would reject real Japanese —
# 表現, 演者, 出演 are all ordinary words built from the same characters. This
# catches what is on it and nothing else, and says so.
_CHINESE_WORDS = ('表演者', '発票', '手套')

_KANJI_ONLY = re.compile(r'[\u4E00-\u9FFF]')

_KANA_ONLY = re.compile(r'[\u3040-\u309F\u30A0-\u30FF]')


def find_foreign_wording(text: str, language: str) -> str:
    """Chinese wording inside otherwise-Japanese text, or '' if clean.

    Scoped to TRANSLATED OBJECTIVES, not to dialogue. A full sentence of
    Japanese always carries kana — 0 of 118 accepted translations in a live
    sample had none — so kanji with no kana at all is Chinese. That is not
    true of a spoken turn, where 「了解」 and 「承知」 are correct Japanese and
    carry no kana either, which is why this is not wired into the actor path.
    """
    if language != 'Japanese' or not text:
        return ''
    for word in _CHINESE_WORDS:
        if word in text:
            return word
    if _KANJI_ONLY.search(text) and not _KANA_ONLY.search(text):
        return text.strip()
    return ''


def translate_hints(tasks: list, language: str) -> dict:
    """Batch-translate task goals and strategy hints into the target language in one LLM call.

    Returns a dict mapping (idx, text) to its translation for goals and hints.
    Falls back to original English text if the call fails or a line is missing.
    """
    if language.strip().lower() in ('english', 'en'):
        res = {}
        for (i, t) in enumerate(tasks):
            res[(i, t.goal)] = t.goal
            if getattr(t, 'hint', None):
                res[(i, t.hint)] = t.hint
        return res

    # A vocab goal with an authored target is composed from a template, not
    # translated, so it never reaches the model. This removes exactly the goal
    # shape that reproducibly came back in Chinese, and it removes the LLM call
    # from the judge path for those tasks too (OPEN-18). The HINT is a real
    # sentence and still needs translating, so it stays in the batch.
    from ..i18n import t as _t
    composed = {}
    items = []
    for (i, task) in enumerate(tasks):
        authored = (getattr(task, 'vocab_translations', {}) or {}).get(language)
        if authored:
            composed[(i, task.goal)] = _t('vocab_goal', language, word=authored[0])
        else:
            items.append((len(items) + 1, i, task.goal))
        if getattr(task, 'hint', None):
            items.append((len(items) + 1, i, task.hint))

    numbered = '\n'.join(f'{num}. {text}' for (num, i, text) in items)
    prompt = f'Translate each numbered instruction below into {language}. Keep the numbering. Write ONLY the translations, one per line, no commentary.\n\n{numbered}'
    try:
        response = client._llm_chat(messages=[{'role': 'user', 'content': prompt}], options=TRANSLATE_OPTS)
        raw = strip_think_tags(response['message']['content']).strip()
        lines = [l.strip() for l in raw.split('\n') if l.strip()]
        result = {}
        for (num, i, text) in items:
            prefix = f'{num}.'
            translated = next((l[len(prefix):].strip() for l in lines if l.startswith(prefix)), None)
            # A line in the wrong script is as unusable as a missing one, so it
            # takes the same fallback. Asking for Japanese and being handed
            # Chinese is not hypothetical here: a batch made up of the catalog's
            # "Use the word 'X'" goals reproducibly comes back as
            # 使用「voucher」这个词 — 12 of 12 goals, three runs running. The
            # learner is then shown their objective in a language they are not
            # studying. English is the honest fallback; a wrong-script retry
            # costs another call and can leak again.
            if translated and (find_wrong_script(translated, language)
                               or find_foreign_wording(translated, language)
                               or _looks_untranslated(translated, language)):
                translated = None
            result[(i, text)] = translated if translated else text

        # One retry for the lines that fell back, ONE LINE AT A TIME. The
        # comment above dismissed a retry as costing a call and able to leak
        # again. Both are true and neither is an argument against it: whatever
        # the retry fails to fix falls back to English exactly as before, so it
        # cannot do worse, and the calls are paid once at session start, on the
        # loading screen, not per turn.
        #
        # Singly rather than as a batch, because the batch is what causes the
        # failure. Measured on the scenario that fails hardest, the same ten
        # lines: 4/10 unusable asked together, 1/10 asked one at a time. A
        # batch primes the model into one language and a run of Chinese
        # continues as Chinese — which is also why retrying the rejects as a
        # smaller batch recovered almost nothing (16% -> 13%).
        #
        # Naming the script in the prompt was tried first, as the cheapest
        # lever, and measured inert: 2/100 wrong-script lines before, 3/100
        # after.
        missing = [(i, text) for (_num, i, text) in items
                   if result.get((i, text)) == text]
        for (i, text) in missing[:TRANSLATE_RETRY_LIMIT]:
            try:
                one = strip_think_tags(client._llm_chat(
                    messages=[{'role': 'user',
                               'content': f'Translate this instruction into '
                                          f'{language}. Write ONLY the '
                                          f'translation.\n\n{text}'}],
                    options=TRANSLATE_OPTS)['message']['content']).strip()
            except Exception:
                break       # the English fallbacks already in `result` stand
            one = one.split('\n')[0].strip()
            if one and not find_wrong_script(one, language) \
                   and not find_foreign_wording(one, language) \
                   and not _looks_untranslated(one, language):
                result[(i, text)] = one

        result.update(composed)
        return result
    except Exception:
        res = {}
        for (i, task) in enumerate(tasks):
            res[(i, task.goal)] = task.goal
            if getattr(task, 'hint', None):
                res[(i, task.hint)] = task.hint
        res.update(composed)
        return res
