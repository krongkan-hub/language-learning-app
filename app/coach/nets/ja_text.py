"""Small Japanese text helpers shared by more than one net."""

_CLAUSE_END = '。、！？!?\n'


def _quote_through(user_input: str, match, replacement: str) -> tuple:
    """Quote the learner's own words from the noun through the verb.

    Quoting the bare particle (「先生を」 → 「先生に」) names the fix but not the
    sentence: the repeat drill asks the learner to retype the ✅ text, and a
    two-character fragment is not something to retype. Spanning the verb gives
    them the clause they actually meant.
    """
    return user_input[match.start():match.end()], replacement
