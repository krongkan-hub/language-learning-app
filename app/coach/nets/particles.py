"""Case particles: を for に, に for で, and the partner particle.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
from ..verdict import is_clean_verdict
from .tables import (_BARE_TIME_NI_ERROR, _DE_ACTION_ERROR, 
                     _NI_PARTICLE_ERROR, _NI_PARTNER_ERROR, 
                     _NI_PARTNER_SURU, _NI_RESIDENCE_ERROR, 
                     _NI_TARGET_VERBS, _TO_PARTNER_ERROR, _TO_PARTNER_SURU, 
                     _clause_or_pair, _quote_through)


def apply_particle_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a particle the verb, not the meaning, fixes.

    Five shapes, all of them classes the model calls natural: を on a に-taking
    verb's target (会う/乗る, and the suru-verbs whose partner is a person),
    に where a reciprocal verb needs と, に where an action at a place needs で,
    and で where 住む/勤める need に.
    """
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    match = _NI_PARTICLE_ERROR.search(user_input)
    if match:
        noun = match.group('noun')
        reason = _NI_TARGET_VERBS[match.group('stem')[0]]
        return f'💡 Feedback:\n- ❌ "{noun}を" → ✅ "{noun}に" ({reason})'

    for pattern, table, wrong_particle, right_particle in (
        (_NI_PARTNER_ERROR, _NI_PARTNER_SURU, 'を', 'に'),
        (_TO_PARTNER_ERROR, _TO_PARTNER_SURU, 'に', 'と'),
    ):
        match = pattern.search(user_input)
        if not match:
            continue
        noun, verb, tail = match.group('noun'), match.group('verb'), match.group('tail')
        wrong, right = _quote_through(
            user_input, match, f'{noun}{right_particle}{verb}{tail}')
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'({table[verb]})')

    match = _DE_ACTION_ERROR.search(user_input)
    if match:
        noun, stem = match.group('noun'), match.group('stem')
        wrong, right = _quote_through(user_input, match, f'{noun}で{stem}')
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(動作を行う場所は「で」で示します)')

    match = _NI_RESIDENCE_ERROR.search(user_input)
    if match:
        noun, stem = match.group('noun'), match.group('stem')
        wrong, right = _quote_through(user_input, match, f'{noun}に{stem}')
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(「住む」「勤める」の場所は「に」で示します)')

    # Last, so the five shapes above keep priority on a sentence that carries
    # both: 「昨日に友達を会いました」 should be told about the を, which is the
    # error the learner is more likely to repeat.
    match = _BARE_TIME_NI_ERROR.search(user_input)
    if match:
        word = match.group('word')
        wrong, right = _clause_or_pair(user_input, match.start(), word)
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(「{word}」は時を表す副詞なので「に」は付けません)')

    return feedback
