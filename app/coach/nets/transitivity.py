"""Transitive and intransitive pairs — つく/つける, 始まる/始める.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
from ..verdict import is_clean_verdict
from ..tables.japanese import (_TI_PAIRS, _TI_PATIENTS, _TI_SUFFIX_BLOCK)


def _ti_lookup(text: str, stems, offset: int):
    """Match a stem sitting IMMEDIATELY at `offset`, never merely later in the
    sentence. Searching ahead produced false positives on correct multi-clause
    Japanese — 「電気をつけて、窓が閉まりました。」 matched the intransitive 閉まり
    from the second clause against the を of the first and "corrected" it. The
    error shape this net targets is adjacent by construction (電気を+つきました),
    so adjacency costs nothing and removes the whole class."""
    for stem in stems:
        if text.startswith(stem, offset):
            after = text[offset + len(stem): offset + len(stem) + 2]
            if not any(after.startswith(b) for b in _TI_SUFFIX_BLOCK):
                return stem
    return None


def _ti_inflect(text: str, offset: int, hit: str, target_stems, wrong_cite: str,
                right_cite: str):
    """Quote the learner's own inflection back, not a dictionary form.

    The learner writes 「電気をつきました」; quoting 「をつきます → をつけます」 at
    them is a citation form they did not use and cannot copy. Splicing the
    correct stem onto their own ending gives 「をつきました → をつけました」, which
    is the sentence they meant and — since the repeat drill asks them to retype
    the ✅ text — the thing they should be practising.

    Falls back to the citation pair when the ending cannot be read, so a shape
    this does not understand degrades to the old behaviour rather than
    producing something wrong.
    """
    # The NEAREST clause boundary, not the first one in this tuple. Searching
    # in tuple order found the 。 at the end of 「窓を開きて、換気しました。」
    # before the 、 right after the verb, so the quote swallowed the next
    # clause and the reason read 「他動詞の『開けて、換気しました』になります」.
    tail = text[offset + len(hit):]
    cuts = [tail.find(stop) for stop in ('。', '、', '！', '？', '\n')]
    cuts = [c for c in cuts if c != -1]
    ending = tail[:min(cuts)] if cuts else tail
    if not ending or len(ending) > 8:
        return wrong_cite, right_cite
    # The ren'youkei stem is listed first in each tuple and is the one an
    # ending attaches to; the dictionary form takes no ending.
    replacement = target_stems[0]
    return f'{hit}{ending}', f'{replacement}{ending}'


def apply_transitivity_net(feedback: str, user_input: str, language: str) -> str:
    """Catch を+intransitive and inanimate-が+transitive, the two shapes the
    model calls natural. Only ever overturns a clean verdict."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    # Rule A only looks at を that follow a noun this table vouches for.
    # Reading every を was not the unambiguous test it was taken for: 嘘をつく,
    # ため息をつく, 息をつく and 手をつく are fixed idioms that take を with an
    # intransitive verb, and the rule "corrected" every one of them. This is
    # the discipline Rule B already had.
    wo_after_patient = sorted(
        user_input.find(patient + 'を') + len(patient)
        for patient in _TI_PATIENTS if patient + 'を' in user_input)

    for intrans, trans, intrans_cite, trans_cite in _TI_PAIRS:
        # Rule A: を + intransitive.
        for idx in wo_after_patient:
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
