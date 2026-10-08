"""Keep a Japanese generation from writing characters Japanese does not use.

The actor's first attempt in Japanese is rejected 59-66% of the time, and
the largest single cause is wrong script — 22-23 of 80 samples drop into
simplified Chinese (eval_rawactor, 2026-10-04). The guards catch it after
the fact: the sentence is thrown away, and the turn ends short or on a
canned line. This stops it at the source: every token whose text contains a
character `find_wrong_script` would flag is given -inf before sampling, so
the model picks its next-best token instead.

The banned set is exactly the guard's definition, applied to each token's
own text, so nothing the guard accepts can be banned. A token that is only
part of a character's UTF-8 bytes decodes to U+FFFD and is left alone; the
common simplified characters are single tokens in this vocabulary, which is
what makes the mask bite.
"""
import json
import os
from pathlib import Path
from typing import Callable, Optional

from .guards import find_wrong_script

_CACHE_DIR = Path(os.environ.get('LANGUAGE_COACH_CACHE', Path.home() / '.cache' / 'language-coach'))
_banned_ids: dict = {}          # cache key -> list of token ids


def _banned_for(tokenizer, language: str) -> list:
    key = f'{getattr(tokenizer, "name_or_path", "model")}:{language}'
    if key in _banned_ids:
        return _banned_ids[key]
    path = _CACHE_DIR / ('script_mask_' + key.replace('/', '_').replace(':', '_') + '.json')
    try:
        ids = json.loads(path.read_text())
    except (OSError, ValueError):
        ids = []
        for i in range(len(tokenizer.get_vocab())):
            text = tokenizer.decode([i])
            if text and '�' not in text and find_wrong_script(text, language):
                ids.append(i)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(ids))
        except OSError:
            pass                                   # recomputed next run
    _banned_ids[key] = ids
    return ids


def script_processor(tokenizer, language: str) -> Optional[Callable]:
    """A logits processor banning other scripts' tokens, or None when the
    language needs none."""
    if language != 'Japanese':
        return None
    import mlx.core as mx
    ids = _banned_for(tokenizer, language)
    if not ids:
        return None
    penalty = {}

    def process(tokens, logits):
        size = logits.shape[-1]
        if size not in penalty:
            vec = mx.zeros((size,), dtype=logits.dtype)
            vec[mx.array([i for i in ids if i < size])] = -float('inf')
            penalty[size] = vec
        return logits + penalty[size]
    return process
