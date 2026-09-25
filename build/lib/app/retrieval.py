"""Semantic retrieval over what the learner has already been taught.

The app collects a word every time the NPC teaches one, and then never brings
it back: `vocab_log` grows, `times_correct` mostly stays at 0, and the learner
meets each word once. Spaced repetition is the one thing every serious
language app does and this one did not.

Recency alone is the wrong selector. A learner at a flower shop does not want
the three oldest unpractised words from a customs hearing — the word has to
fit the conversation it is being smuggled back into, or the NPC cannot use it
without sounding deranged. Fitting is a meaning question, so it is answered
with embeddings: each word is stored as a vector alongside its row, and the
scenario the learner just started becomes the query.

    scenario ("Flower Shop Bouquet" + role + place)  ->  query vector
    every due word (times_correct < 3)               ->  stored vectors
    cosine, top k                                    ->  words the NPC is
                                                         nudged to reuse

WHY NOT A VECTOR DATABASE. The corpus is one learner's vocabulary — hundreds
of rows, thousands at the extreme. A brute-force dot product over that is
microseconds in numpy, while Pinecone or Weaviate would add a network service,
a schema to keep in sync and an operational story, to answer a query that fits
in L2 cache. The index goes in SQLite next to the row it belongs to.

OPTIONAL BY DESIGN. mlx-embeddings is an extra, not a runtime dependency: with
it absent, `due_words_for` falls back to least-recently-seen, which is what the
app did before. `app/` still installs with one runtime dependency.
"""
import json
import math
import os
from typing import Optional

# Small and multilingual: 118M parameters, so it loads beside the 7B without
# competing for memory, and it embeds English and Japanese into one space —
# which is the property the whole idea rests on. Calibrated against a bigger
# sibling on this project's own labelled data (BACKLOG OPEN-42): e5-LARGE
# scored no better and was worse at the top of the ranking.
EMBED_MODEL = os.environ.get('EMBED_MODEL', 'intfloat/multilingual-e5-small')

_model = None
_tokenizer = None
_unavailable = False


def available() -> bool:
    """True when embeddings can actually be computed."""
    return _load() is not None


def _load():
    """The embedder, or None if the extra is not installed.

    Failure is not an error: every caller has a non-semantic fallback, and a
    learner should never lose a session because an optional package is
    missing.
    """
    global _model, _tokenizer, _unavailable
    if _unavailable:
        return None
    if _model is None:
        try:
            from mlx_embeddings import load
            _model, _tokenizer = load(EMBED_MODEL)
        except Exception:
            _unavailable = True
            return None
    return _model


def embed(text: str, kind: str = 'query') -> Optional[list]:
    """A unit-length vector for `text`, or None when embeddings are off.

    `kind` is 'query' for the thing being searched WITH (the scenario) and
    'passage' for the thing being searched OVER (a stored word). The E5 family
    is trained with those two words literally prefixed onto the input, and
    dropping them costs accuracy on exactly this asymmetric query-vs-document
    shape. Applied only when the model name says E5, so a future swap to a
    model without the convention needs no change here.
    """
    model = _load()
    if model is None:
        return None
    import mlx.core as mx
    if 'e5' in EMBED_MODEL.lower():
        text = f'{kind}: {text}'
    ids = _tokenizer.encode(text, return_tensors='mlx')
    vec = model(ids).text_embeds[0]
    vec = vec / mx.linalg.norm(vec)
    return [float(x) for x in vec]


def cosine(a: list, b: list) -> float:
    """Cosine similarity. Vectors from `embed` are already unit-length, so
    this is a dot product — the normalisation is kept for vectors that came
    from somewhere else."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def pack(vector: Optional[list]) -> Optional[str]:
    """Vector -> the TEXT column it is stored in. JSON rather than a packed
    float32 blob: the whole table is a few hundred rows, and a column a human
    can read in `sqlite3` is worth more here than the bytes it saves."""
    return None if vector is None else json.dumps(vector)


def unpack(stored) -> Optional[list]:
    """The stored column -> vector, tolerating NULL and anything unreadable."""
    if not stored:
        return None
    try:
        return json.loads(stored)
    except (ValueError, TypeError):
        return None


def scenario_query(place: str, role: str, goals=()) -> str:
    """The text that stands for 'the conversation the learner is entering'.

    Place and role carry the setting; a few goals carry what will actually be
    talked about, which is what decides whether a word can be worked in.
    """
    parts = [p for p in (place, role) if p]
    parts.extend(list(goals)[:5])
    return '. '.join(parts)


def rank_by_similarity(query_vector: Optional[list], rows: list, limit: int) -> list:
    """`rows` (each a mapping with an `embedding` column) ranked by closeness.

    With no query vector — embeddings off, or the query failed — the rows come
    back in the order they arrived, which for the caller is least-recently-seen
    first. That is the pre-retrieval behaviour, deliberately unchanged.
    """
    if query_vector is None:
        return list(rows)[:limit]
    scored = []
    for row in rows:
        vector = unpack(row['embedding'] if 'embedding' in row.keys() else None)
        if vector is None:
            continue
        scored.append((cosine(query_vector, vector), row))
    if not scored:
        return list(rows)[:limit]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _score, row in scored[:limit]]


def embed_vocab(word: str, explanation: str = '') -> Optional[str]:
    """The packed vector to store with a taught word, or None.

    The explanation goes into the text as well as the word: "decant" alone is
    ambiguous across domains, while "decant — to pour wine off its sediment"
    lands where a restaurant scenario can find it. Never raises — a word that
    cannot be embedded is simply ranked by recency.
    """
    try:
        text = f'{word} — {explanation}'.strip(' —') if explanation else word
        return pack(embed(text, kind='passage'))
    except Exception:
        return None
