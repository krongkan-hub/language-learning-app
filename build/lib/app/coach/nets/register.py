"""Plain forms where the situation asks for polite ones.

Only ever overturns a CLEAN verdict — a real model correction always wins.
See BACKLOG OPEN-07 and OPEN-10.
"""
from ..verdict import is_clean_verdict
from .tables import (_CASUAL_PRONOUNS, _JA_POLITE_MARKERS, _PLAIN_ENDING, 
                     _PLAIN_TO_POLITE, _SUPERIOR_VOCATIVE)


def apply_register_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict when the learner addresses someone senior and
    then speaks to them in plain form or with a casual pronoun.

    Narrower than the situational rules on purpose: it fires only when the
    learner's own sentence names the listener, so it needs no scenario and
    cannot mistake an equal for a superior.
    """
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    if not _SUPERIOR_VOCATIVE.match(user_input.strip()):
        return feedback

    vocative = _SUPERIOR_VOCATIVE.match(user_input.strip()).group(0).rstrip('、,')
    for casual, polite in _CASUAL_PRONOUNS:
        if casual in user_input:
            if polite is None:
                # お前 → あなた would be trading one rudeness for another.
                # The learner has already named the listener in this very
                # sentence, so the fix is to keep using that.
                return (f'💡 Feedback:\n- ❌ "{casual}" → ✅ "{vocative}" '
                        f'(目上の人は「あなた」ではなく「{vocative}」と'
                        f'呼びます)')
            return (f'💡 Feedback:\n- ❌ "{casual}" → ✅ "{polite}" '
                    f'(目上の人には「{polite}」を使います)')

    if any(marker in user_input for marker in _JA_POLITE_MARKERS):
        return feedback
    match = _PLAIN_ENDING.search(user_input.strip())
    if match:
        verb, question = match.group('verb'), match.group('q') or ''
        polite = _PLAIN_TO_POLITE[verb]
        return (f'💡 Feedback:\n- ❌ "{verb}{question}" → ✅ "{polite}{question}" '
                f'(目上の人には「ます」の形で話します)')

    return feedback
