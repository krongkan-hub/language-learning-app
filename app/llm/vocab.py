"""The vocabulary block the NPC appends to a turn, and reading it back."""
import re


_ENCOURAGE_LABELS = (r'encourag\w*', r'[A-Za-z]{4,20}')


# Bounds on what a vocabulary field may be, applied in the PARSER so that
# nothing longer ever reaches the database. The word is stored and later
# spliced back into the actor's own system prompt in a different session
# (app/session.py, build_review_block), so an unbounded `(.*?)` here is the
# first link in a model -> storage -> instruction loop. 40 characters is
# already generous for a word or a short set phrase; the two prose fields get
# room to be sentences and no more.
_MAX_WORD = 40
_MAX_PROSE = 400


def _vocab_patterns():
    """Tagged and untagged block patterns, most specific label first."""
    word = r'(.{1,%d}?)' % _MAX_WORD
    prose = r'(.{1,%d}?)' % _MAX_PROSE
    for enc in _ENCOURAGE_LABELS:
        body = (r'word:\s*' + word + r'\s+explanation:\s*' + prose
                + r'\s+' + enc + r':\s*' + prose)
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
