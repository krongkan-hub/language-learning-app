"""Vocabulary the NPC taught, and the spaced review that brings it back."""
import json

import psycopg
from .common import _utcnow


# ── vocab_log ────────────────────────────────────────────────────────────────

def log_vocab(conn: psycopg.Connection, user_id: int, language: str,
              word: str, explanation: str, scenario_name: str,
              embedding: 'str | None' = None) -> None:
    """Log or update a taught vocabulary word, incrementing times_taught if already seen.

    `embedding` is the packed vector from app.retrieval, or None when the
    optional embedder is not installed. It
    is written on insert and backfilled on update, so a word first met before
    retrieval existed gains its vector the next time it is taught.
    """
    now = _utcnow()
    row = conn.execute(
        "SELECT id FROM vocab_log WHERE user_id = %s AND language = %s AND LOWER(word) = LOWER(%s)",
        (user_id, language, word)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE vocab_log "
            "SET times_taught = times_taught + 1, last_seen_at = %s, explanation = %s, "
            "    scenario_name = %s, embedding = COALESCE(%s::vector, embedding) "
            "WHERE id = %s",
            (now, explanation, scenario_name, embedding, row['id'])
        )
    else:
        conn.execute(
            "INSERT INTO vocab_log "
            "(user_id, language, word, explanation, scenario_name, times_taught, "
            " times_correct, first_taught_at, last_seen_at, embedding) "
            "VALUES (%s, %s, %s, %s, %s, 1, 0, %s, %s, %s::vector)",
            (user_id, language, word, explanation, scenario_name, now, now, embedding)
        )
    conn.commit()


def due_words_for(conn: psycopg.Connection, user_id: int, language: str,
                  query_vector: 'list | None' = None, limit: int = 3) -> list:
    """Words still due, ranked by how well they fit the conversation ahead.

    The candidate set is the same one the drill uses (times_correct < 3); what
    changes is the ORDER. Recency answers "what has the learner not seen
    lately", which is the wrong question for an NPC that has to work the word
    into a flower shop without sounding deranged — that is a meaning question,
    so it is answered with the embedding stored beside each row.

    With no query vector (the embedder is an optional extra) this is exactly
    least-recently-seen, which is what the app did before. With one, the
    ranking is pgvector's cosine distance (<=>) in SQL — only rows that carry
    an embedding take part, and if none do, recency again.
    """
    columns = ("SELECT id, word, explanation, scenario_name, times_taught, "
               "       times_correct, last_seen_at, embedding "
               "FROM vocab_log "
               "WHERE user_id = %s AND language = %s AND times_correct < 3 ")
    if query_vector is not None:
        rows = conn.execute(
            columns + "AND embedding IS NOT NULL "
            "ORDER BY embedding <=> %s::vector, last_seen_at LIMIT %s",
            (user_id, language, json.dumps(list(query_vector)), limit)
        ).fetchall()
        if rows:
            return rows
    return conn.execute(columns + "ORDER BY last_seen_at ASC, id ASC LIMIT %s",
                        (user_id, language, limit)).fetchall()


def count_vocab_due(conn: psycopg.Connection, user_id: int, language: str) -> int:
    """How many collected words are still short of the times_correct >= 3 bar.

    The same condition get_vocab_for_review selects on — that function takes a
    limit (it feeds a drill of three), so counting its rows would have capped
    the answer at three and quietly said "3 words" forever.
    """
    cur = conn.execute(
        "SELECT COUNT(*) AS n FROM vocab_log "
        "WHERE user_id = %s AND language = %s AND times_correct < 3",
        (user_id, language)
    )
    row = cur.fetchone()
    return row['n'] if row else 0


def get_vocab_for_review(conn: psycopg.Connection, user_id: int, language: str,
                         limit: 'int | None' = 3) -> list:
    """Return words worth re-testing (least-recently-seen first, times_correct < 3).
    limit=None returns them all."""
    cur = conn.execute(
        "SELECT id, user_id, language, word, explanation, scenario_name, "
        "       times_taught, times_correct, first_taught_at, last_seen_at "
        "FROM vocab_log "
        "WHERE user_id = %s AND language = %s AND times_correct < 3 "
        "ORDER BY last_seen_at ASC, id ASC "
        "LIMIT %s",
        (user_id, language, limit)
    )
    return cur.fetchall()


def mark_vocab_reviewed(conn: psycopg.Connection, user_id: int, language: str,
                        word: str, correct: bool) -> None:
    """Update review status for a word. Increments times_correct if correct is True, always updates last_seen_at."""
    now = _utcnow()
    if correct:
        conn.execute(
            "UPDATE vocab_log "
            "SET times_correct = times_correct + 1, last_seen_at = %s "
            "WHERE user_id = %s AND language = %s AND LOWER(word) = LOWER(%s)",
            (now, user_id, language, word)
        )
    else:
        conn.execute(
            "UPDATE vocab_log "
            "SET last_seen_at = %s "
            "WHERE user_id = %s AND language = %s AND LOWER(word) = LOWER(%s)",
            (now, user_id, language, word)
        )
    conn.commit()
