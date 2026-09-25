"""The vocabulary block the NPC appends to a turn, and reading it back."""
import re


_ENCOURAGE_LABELS = (r'encourag\w*', r'[A-Za-z]{4,20}')


def _vocab_patterns():
    """Tagged and untagged block patterns, most specific label first."""
    for enc in _ENCOURAGE_LABELS:
        body = r'word:\s*(.*?)\s+explanation:\s*(.*?)\s+' + enc + r':\s*(.*?)'
        yield r'<vocab>\s*' + body + r'\s*</vocab>'
        yield r'(?:<vocab>\s*)?' + body + r'(?:\s*</vocab>)?\s*$'


def match_vocab_fields(text: str):
    """The vocab block with (word, explanation, encourage) captured, or None.

    Group-bearing, so callers that need the fields — parse_vocab — can read
    them. Kept separate from match_vocab_block because a bare <vocab>…</vocab>
    match has no groups, and returning one from here raised "no such group".
    """
    for pattern in _vocab_patterns():
        match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match
    return None


def match_vocab_block(text: str):
    """The vocab block in `text`, or None — the widest match, for locating and
    stripping. A tagged block counts even when its inner labels are unreadable,
    which is why this is tried first and why it cannot carry field groups."""
    tagged = re.search(r'<vocab>.*?</vocab>', text, flags=re.DOTALL | re.IGNORECASE)
    if tagged:
        return tagged
    return match_vocab_fields(text)


def strip_vocab_block(text: str) -> str:
    """`text` with its vocab block removed, leaving the spoken dialogue."""
    stripped = re.sub(r'<vocab>.*?</vocab>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
    match = match_vocab_block(stripped)
    if match:
        stripped = (stripped[:match.start()] + stripped[match.end():]).strip()
    return stripped
