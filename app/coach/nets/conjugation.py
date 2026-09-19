"""て-form 音便, い-adjective negatives and past, adverbial forms.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
from ..verdict import is_clean_verdict
from .tables import (_I_ADJ_ADVERB_ERROR, _I_ADJ_JANAI_ERROR, 
                     _I_ADJ_JANAI_TAIL, _I_ADJ_LIST_ERROR, 
                     _I_ADJ_PAST_ERROR, _TE_ONBIN, _TE_ONBIN_ERROR)


def apply_conjugation_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a mis-formed te-form or i-adjective past.

    Both are regular morphology the model does not enforce: it accepted 読みて
    and 行きたいでした as natural. Only ever overturns a clean verdict.
    """
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    match = _TE_ONBIN_ERROR.search(user_input)
    if match:
        stem = match.group(1)
        return (f'💡 Feedback:\n- ❌ "{stem}て" → ✅ "{_TE_ONBIN[stem]}" '
                f'(五段動詞のテ形は音便の形になります)')

    match = _I_ADJ_PAST_ERROR.search(user_input)
    if match:
        stem, adj = match.group('stem'), match.group('adj')
        past = 'たかったです' if adj == 'たい' else 'なかったです'
        return (f'💡 Feedback:\n- ❌ "{stem}{adj}でした" → ✅ "{stem}{past}" '
                f'(「{adj}」はい形容詞なので、過去形は「{past}」になります)')

    match = _I_ADJ_LIST_ERROR.search(user_input)
    if match:
        adj = match.group('adj')
        past = adj[:-1] + 'かったです'
        return (f'💡 Feedback:\n- ❌ "{adj}でした" → ✅ "{past}" '
                f'(い形容詞の過去形は「かったです」になります)')

    match = _I_ADJ_JANAI_ERROR.search(user_input)
    if match:
        adj, tail = match.group('adj'), match.group('tail')
        right = adj[:-1] + _I_ADJ_JANAI_TAIL[tail]
        return (f'💡 Feedback:\n- ❌ "{adj}じゃ{tail}" → ✅ "{right}" '
                f'(い形容詞の否定は「く」の形を使います)')

    match = _I_ADJ_ADVERB_ERROR.search(user_input)
    if match:
        adj, verb = match.group('adj'), match.group('verb')
        return (f'💡 Feedback:\n- ❌ "{adj}{verb}" → ✅ "{adj[:-1]}く{verb}" '
                f'(い形容詞が動詞を修飾するときは「く」の形になります)')

    return feedback
