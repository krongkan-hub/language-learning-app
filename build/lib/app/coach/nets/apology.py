"""Apologising for nothing, anchored to who is actually late.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
from ..verdict import is_clean_verdict
from .tables import (_APOLOGY_FIX, _APOLOGY_MARKERS, _LATE_MARKERS, 
                     _SENTENCE_SPLIT, _ja_subject_is_someone_else)


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
