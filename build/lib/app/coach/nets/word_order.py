"""Stranded degree adverbs, and たくさん in front of a count.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
from ..verdict import is_clean_verdict
from .tables import (_STRANDED_ADVERB, _TAKUSAN_NO)


def apply_word_order_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a stranded degree adverb or a bare
    たくさん modifying a subject noun."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    match = _STRANDED_ADVERB.search(user_input)
    if match:
        pred, cop, adv = match.group('pred'), match.group('cop'), match.group('adv')
        return (f'💡 Feedback:\n- ❌ "{pred}{cop}{adv}" → ✅ "{adv}{pred}{cop}" '
                f'(程度を表す副詞は述語の前に置きます)')

    match = _TAKUSAN_NO.search(user_input)
    if match:
        noun = match.group('noun')
        return (f'💡 Feedback:\n- ❌ "たくさん{noun}" → ✅ "たくさんの{noun}" '
                f'(「たくさん」が名詞を修飾するときは「の」が必要です)')

    return feedback
