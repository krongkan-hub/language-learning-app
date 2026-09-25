"""The clean verdict, and reading corrections back out of the feedback."""
import re

from ..llm import find_wrong_script


CLEAN_SENTINEL = 'Perfectly natural!'
CLEAN_MARKERS = {'Japanese': '特に直すところは見つかりませんでした。'}


def clean_marker(language: str) -> str:
    """The clean verdict as the learner should see it in their language."""
    return CLEAN_MARKERS.get(language, CLEAN_SENTINEL)


def is_clean_verdict(feedback: str, language: str) -> bool:
    """True for a clean verdict in either the internal or the localized form."""
    return (CLEAN_SENTINEL.lower() in feedback.lower()
            or clean_marker(language) in feedback)


def localize_clean_verdict(feedback: str, language: str) -> str:
    """Swap the internal sentinel for the learner's language. Must run last."""
    marker = clean_marker(language)
    if marker == CLEAN_SENTINEL:
        return feedback
    return feedback.replace(CLEAN_SENTINEL, marker)


_CORRECTION_BULLET = re.compile('❌\\s*"(.*?)"\\s*→\\s*✅\\s*"(.*?)"')


def correction_targets(feedback: str) -> list:
    """The ✅ forms the learner should retype, in bullet order.

    Feedback bullets only: a Level up suggestion is optional polish on an
    already-correct sentence, not something the learner got wrong.
    """
    feedback_block = re.split('⬆️\\s*Level up:', feedback)[0]
    targets = []
    for (_said, better) in _CORRECTION_BULLET.findall(feedback_block):
        better = better.strip()
        if better and better not in targets:
            targets.append(better)
    return targets



_BULLET_REASON = re.compile(r'\s*[（(]([^）)]*)[）)]\s*$')


def _drop_foreign_reasons(feedback: str, language: str) -> str:
    """Strip a bracketed reason that is in the wrong language, keep the bullet.

    Returns '' when a line is unusable for any other reason, so the caller
    still falls back rather than shipping half a correction.
    """
    kept = []
    for line in feedback.split('\n'):
        if not find_wrong_script(line, language):
            kept.append(line)
            continue
        stripped = _BULLET_REASON.sub('', line)
        if stripped != line and not find_wrong_script(stripped, language):
            kept.append(stripped.rstrip())
            continue
        return ''          # the wrong script is in the correction itself
    return '\n'.join(kept)
