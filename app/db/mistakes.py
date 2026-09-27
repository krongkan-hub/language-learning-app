"""Coach corrections, grouped by shape, so a repeated mistake can be recognised."""
import re
import psycopg
from .common import _utcnow
from ..coach.verdict import _CORRECTION_BULLET


# ── mistakes ─────────────────────────────────────────────────────────────────

# A cardinal number, written as a word, collapses the same way a digit run
# does: "two bottle" / "three bottle" are the same missing-plural mistake, and
# the quantity itself is not the mistake. Small closed list, English only —
# see _normalize_mistake_text for why that's an accepted limit, not an
# oversight.
_CARDINAL_WORDS = {w: '#' for w in (
    'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
    'ten', 'eleven', 'twelve', 'hundred', 'thousand', 'million',
)}

# A subject pronoun is the other common "free variable" in a grammar mistake:
# "I go yesterday" / "he go yesterday" are the same missing-past-tense
# mistake, and who is doing it is not the mistake. Collapsed to a single
# placeholder distinct from '#' so a number mistake and a pronoun mistake
# never accidentally collide.
_SUBJECT_PRONOUNS = {w: '_who_' for w in (
    'i', 'you', 'he', 'she', 'it', 'we', 'they',
)}

_PUNCT_RE = re.compile(r'[^\w\s]', re.UNICODE)
_DIGIT_RUN_RE = re.compile(r'\d+')


def _normalize_mistake_text(text: str) -> str:
    """Fold incidental wording differences out of a ❌ or ✅ phrase.

    The goal is a key two phrases share exactly when they are instances of
    the same mistake, not merely similar. Three mechanical steps, applied in
    order:

      1. Lowercase, then drop punctuation (``\\w``/``\\s`` are Unicode-aware,
         so this also works on non-Latin scripts — it just strips their
         punctuation, e.g. Japanese `。` `、`, rather than English's).
      2. Collapse any run of digits to ``#``.
      3. Map a small closed list of English cardinal-number words and
         subject pronouns to fixed placeholders (``#`` and ``_who_``).

    Step 3 is deliberately narrow and English-specific — it is a heuristic,
    not a grammar. It exists because the two mistake classes named in the
    design brief ("two bottle"/"three bottle", "I go yesterday"/"he go
    yesterday") both vary in exactly a number word or a subject pronoun, and
    those are the two most common "the value doesn't matter, the shape does"
    slots in a corrected sentence. Anything more general — real
    tokenization, POS tagging, edit-distance diffing against the correction
    — is more machinery than this table needs; steps 1-2 alone already do
    most of the work language-agnostically, and step 3 is a small, testable,
    reviewable list rather than a model. For a non-English target language
    this step is a no-op (the words never match), and the key degrades to
    steps 1-2: still meaningful, just less aggressive at merging.
    """
    text = text.lower()
    text = _PUNCT_RE.sub(' ', text)
    text = _DIGIT_RUN_RE.sub('#', text)
    tokens = text.split()
    tokens = [_CARDINAL_WORDS.get(t, t) for t in tokens]
    tokens = [_SUBJECT_PRONOUNS.get(t, t) for t in tokens]
    return ' '.join(tokens)


def _mistake_key(quoted_text: str, correction: str) -> str:
    """The grouping key for one correction bullet.

    Built from both sides, not just one: the same wrong wording can be
    corrected differently in different contexts, and the same correction can
    be reached from different wrong wordings, so only the (wrong, right)
    pair together identifies a repeatable mistake class.
    """
    return _normalize_mistake_text(quoted_text) + '→' + _normalize_mistake_text(correction)


def log_mistakes(conn: psycopg.Connection, user_id: int, language: str, session_id: int,
                 scenario_name: str, feedback: str) -> list:
    """Parse one coach feedback block and store one row per correction bullet.

    Reuses _CORRECTION_BULLET from app.coach.verdict — the same ❌/✅ pattern
    correction_targets reads the drill targets out of — rather than
    re-deriving it here. A Level up suggestion is excluded the same way
    correction_targets excludes it: it polishes an already-correct sentence,
    it is not a mistake.

    Returns the ids of the rows inserted, in bullet order.
    """
    feedback_block = re.split(r'⬆️\s*Level up:', feedback)[0]
    now = _utcnow()
    ids = []
    for quoted_text, correction in _CORRECTION_BULLET.findall(feedback_block):
        quoted_text, correction = quoted_text.strip(), correction.strip()
        if not quoted_text or not correction:
            continue
        cur = conn.execute(
            "INSERT INTO mistakes "
            "(user_id, language, session_id, scenario_name, quoted_text, correction, "
            " normalized_key, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (user_id, language, session_id, scenario_name, quoted_text, correction,
             _mistake_key(quoted_text, correction), now)
        )
        ids.append(cur.fetchone()[0])
    conn.commit()
    return ids


def repeats_among(conn: psycopg.Connection, mistake_ids: list) -> list:
    """Which of the just-logged mistakes this learner has made before.

    Takes the ids log_mistakes returned for one turn and answers, per row,
    how many times its normalized_key has appeared for the same learner and
    language: every earlier turn's rows, plus this one. Rows from THIS turn
    are not history — "I dont know and I dont care" logs the same mistake
    twice in one turn, and that is still a first occurrence. Only counts
    above one are returned, once per class, in mistake_ids order so the
    notice lines up with the coach's bullets.
    """
    ids = list(mistake_ids)
    if not ids:
        return []
    marks = ','.join(['%s'] * len(ids))
    out, seen = [], set()
    for mid in ids:
        row = conn.execute(
            "SELECT m.quoted_text, m.correction, m.normalized_key, "
            "  (SELECT COUNT(*) FROM mistakes o WHERE o.user_id = m.user_id "
            "   AND o.language = m.language AND o.normalized_key = m.normalized_key "
            f"  AND o.id NOT IN ({marks})) AS earlier "
            "FROM mistakes m WHERE m.id = %s", (*ids, mid)
        ).fetchone()
        if not row or row['normalized_key'] in seen or row['earlier'] < 1:
            continue
        seen.add(row['normalized_key'])
        out.append({"quoted": row['quoted_text'],
                    "correction": row['correction'],
                    "occurrences": row['earlier'] + 1})
    return out


def repeated_mistakes(conn: psycopg.Connection, user_id: int, language: str,
                      limit: int = 3) -> list:
    """The mistake classes this learner keeps making, most-repeated first.

    Only classes seen more than once qualify — a single occurrence isn't a
    pattern yet, it's just a mistake. Each result carries the count and the
    most recent ❌/✅ example, so a caller (a front end, a progress report)
    can show "you have made this mistake N times" — most recently: '...' →
    '...' — without a second query.
    """
    groups = conn.execute(
        "SELECT normalized_key, COUNT(*) as occurrences, MAX(created_at) as last_seen "
        "FROM mistakes WHERE user_id = %s AND language = %s "
        "GROUP BY normalized_key HAVING COUNT(*) > 1 "
        "ORDER BY occurrences DESC, last_seen DESC LIMIT %s",
        (user_id, language, limit)
    ).fetchall()
    results = []
    for group in groups:
        example = conn.execute(
            "SELECT quoted_text, correction, scenario_name FROM mistakes "
            "WHERE user_id = %s AND language = %s AND normalized_key = %s "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (user_id, language, group['normalized_key'])
        ).fetchone()
        results.append({
            "normalized_key": group['normalized_key'],
            "occurrences": group['occurrences'],
            "last_seen": group['last_seen'],
            "example_quoted": example['quoted_text'] if example else None,
            "example_correction": example['correction'] if example else None,
            "scenario_name": example['scenario_name'] if example else None,
        })
    return results
