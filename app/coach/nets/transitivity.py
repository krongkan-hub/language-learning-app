"""Transitive and intransitive pairs — つく/つける, 始まる/始める.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
from ..verdict import is_clean_verdict
from .tables import (_TI_PAIRS, _TI_PATIENTS, _ti_inflect, _ti_lookup)


def apply_transitivity_net(feedback: str, user_input: str, language: str) -> str:
    """Catch を+intransitive and inanimate-が+transitive, the two shapes the
    model calls natural. Only ever overturns a clean verdict."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    for intrans, trans, intrans_cite, trans_cite in _TI_PAIRS:
        # Rule A: を + intransitive. Unambiguous — an intransitive verb takes no
        # object. (Motion verbs take を for a path, but none are in this table.)
        idx = user_input.find('を')
        if idx != -1:
            hit = _ti_lookup(user_input, intrans, idx + 1)
            if hit:
                wrong, right = _ti_inflect(user_input, idx + 1, hit, trans,
                                           intrans_cite, trans_cite)
                return (f'💡 Feedback:\n- ❌ "を{wrong}" → ✅ "を{right}" '
                        f'(「を」を使うときは他動詞の「{right}」になります)')

        # Rule B: inanimate patient + が + transitive.
        for patient in _TI_PATIENTS:
            marker = patient + 'が'
            pos = user_input.find(marker)
            if pos == -1:
                continue
            hit = _ti_lookup(user_input, trans, pos + len(marker))
            if hit:
                wrong, right = _ti_inflect(user_input, pos + len(marker), hit,
                                           intrans, trans_cite, intrans_cite)
                return (f'💡 Feedback:\n- ❌ "{patient}が{wrong}" → ✅ '
                        f'"{patient}が{right}" '
                        f'(「{patient}」が主語のときは自動詞の「{right}」を使います)')
    return feedback
