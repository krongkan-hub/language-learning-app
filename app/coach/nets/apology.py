"""Apologising for nothing, anchored to who is actually late.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
import re
from ..verdict import is_clean_verdict
from ..tables.japanese import (_APOLOGY_FIX, _APOLOGY_MARKERS, _JA_FIRST_PERSON)


# Saying you are late, and NOT saying you will not be. The apology net tells
# the learner to apologise for what follows, so a promise not to be late —
# 「絶対に遅れません」, 「もう遅刻しません」, "I promise I am never late" — was
# answered with an apology for keeping the other person waiting.
_LATE_MARKERS = {
    'Japanese': re.compile('遅れ(?:ま(?!せん)|そう|る)'
                           '|遅刻(?!し(?:ま(?:せん|い)|ない|たく))'
                           '|遅くなり(?!ません)'),
    'English': re.compile(r"\b(?:i|we)(?:'m| am| will be|'ll be| are)\b"
                          r"(?:(?!\bnot\b|\bnever\b|n't)[^.!?]){0,40}?\blate\b",
                          re.IGNORECASE),
}


_JA_SUBJECT = re.compile(r'([^\s、。！？]{1,12}?)[がは]')


_SENTENCE_SPLIT = re.compile('(?<=[.!?。．！？])\\s*')


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


def apply_apology_net(feedback: str, user_input: str, language: str,
                      situational: bool = False) -> str:
    """Overturn a clean verdict when the learner reports being late and
    apologises for nothing. Both languages."""
    if not situational or not is_clean_verdict(feedback, language):
        return feedback
    late = _LATE_MARKERS.get(language)
    if late is None or not late.search(user_input):
        return feedback
    if any(marker in user_input.lower() for marker in _APOLOGY_MARKERS[language]):
        return feedback

    prefix, reason = _APOLOGY_FIX[language]
    said = next((s for s in _SENTENCE_SPLIT.split(user_input.strip())
                 if late.search(s)), user_input.strip())
    said = said.strip()
    if language == 'Japanese' and _ja_subject_is_someone_else(said, late):
        return feedback
    return (f'💡 Feedback:\n- ❌ "{said}" → ✅ "{prefix}{said}" ({reason})')
