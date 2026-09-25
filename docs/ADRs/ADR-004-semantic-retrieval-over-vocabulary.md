# ADR-004: Semantic retrieval over the learner's own vocabulary

**Status:** Accepted
**Owner:** `architect_agent`

## Context

The app taught a word, logged it to `vocab_log`, and never used it again:
`times_correct` mostly stayed at 0 and the learner met each word exactly
once. Spaced repetition is the one thing every serious language app does
and this one did not — the fix is to bring due words back into the NPC's
own dialogue, since a word met again inside a conversation is worth more
than the same word on a flashcard.

Recency alone is the wrong selector. A learner at a flower shop does not
want the three oldest unpractised words from a customs hearing — the word
has to fit the conversation it is being reintroduced into, or the NPC
cannot use it without sounding deranged. Fitting is a meaning question, so
`app/retrieval.py` answers it with embeddings: the scenario the learner
just started (name, role, place) becomes a query vector, every due word
(`times_correct < 3`) is a stored vector, and cosine similarity over that
pair is what the NPC gets nudged to reuse.

## Decision

1. **Embeddings, computed with `mlx-embeddings`.** Each vocab row stores a
   unit-length vector alongside it; the scenario becomes the query at
   retrieval time.
2. **`intfloat/multilingual-e5-small` as the model**, not a larger sibling.
   Compared against `multilingual-e5-large` on this project's own 80
   labelled lines (`docs/BACKLOG.md` OPEN-42): e5-small reads AUC 0.774 with
   precision@5 of 5/5; e5-large reads AUC 0.788 but precision@5 of only 3/5 —
   five times the parameter count for a worse top of the ranking, so the
   small model is the one this repo uses. (That OPEN-42 measurement was for
   a different detector — cross-lingual objective-translation scoring — but
   it is the same embedder and the same question: does the larger model earn
   its cost, and the answer was no both times.)
3. **No vector database.** The corpus is one learner's vocabulary — hundreds
   of rows, thousands at the extreme. A brute-force dot product over that is
   microseconds in numpy; Pinecone or Weaviate would add a network service,
   a schema to keep in sync, and an operational story, to answer a query
   that fits in L2 cache. The index lives in SQLite next to the row it
   belongs to, as a JSON-encoded TEXT column — readable in `sqlite3` by a
   human, which was judged worth more here than the bytes a packed float32
   blob would save.
4. **Optional, not a runtime dependency.** `mlx-embeddings` ships as the
   `retrieval` extra in `pyproject.toml`, not in `dependencies`. With it
   absent, `available()` returns false and the caller falls back to
   least-recently-seen — which is what the app did before this ADR, so
   losing the extra loses a ranking quality, not a feature. `app/` keeps
   installing with one runtime dependency (`mlx-lm`).
5. **The reintroduction wording is measured, not chosen.** `build_review_block`
   in `app/session.py` turns the retrieved word into one line asking the NPC
   to work it into dialogue. Three wordings were run against the same twenty
   scenarios, two turns each, against a no-block control
   (`dev/tools/probe_review_reuse.py`):

       control                                          1/40 reuse
       permission, three words offered                  7/40
       instruction, one word, named twice                2/16 (subset)
       ONE word, named as ordinary for the setting,      19/40  <- shipped
         next to the vocabulary instruction

   The winner is not the firmest-sounding version. Naming ONE word and
   placing it beside the vocabulary instruction it competes with beat both a
   menu of three and a direct order. The vocabulary card itself survives
   either way (38/40 against 37/40 control) — this is the thing prior work
   (`docs/BACKLOG.md` OPEN-21, OPEN-14) measured an added prompt block
   destroying, and it does not happen here.

## Consequences

- **Positive:** due words come back inside conversation instead of sitting
  unused in `vocab_log`, without adding a second always-on model or a
  network dependency — `mlx-embeddings` loads alongside the 7B without
  competing meaningfully for memory (118M parameters).
- **Positive:** the fallback path means a learner never loses the feature
  entirely because an optional package failed to install; retrieval quality
  degrades to the pre-ADR behavior instead of erroring.
- **Negative — accepted:** without the `retrieval` extra installed, ranking
  silently degrades to recency. There is currently no user-visible signal
  that this happened; a learner (or a developer debugging a review-block
  complaint) has to know to check `available()`.
- **Rejected:** a vector database, for the operational-cost reasons above —
  the corpus size never approaches where one would pay for itself.
- **Rejected:** the larger embedding model, e5-large, on measured evidence
  rather than the general assumption that bigger embeddings rank better.
- **Rejected, with measurement:** a firmer or more generous review-block
  wording. The instinct that "ask harder" or "offer more words" would
  reuse more words was wrong at every alternative tried.

## Follow-up

The e5-small vs. e5-large comparison this decision leans on (OPEN-42) was
run for a different task — scoring translation quality, not vocabulary
retrieval. If retrieval quality is ever measured directly against the
labelled vocabulary data rather than borrowed from a neighboring
measurement, record that number here rather than leaving this ADR resting
on an analogy.
