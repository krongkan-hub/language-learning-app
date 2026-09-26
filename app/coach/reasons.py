"""Japanese particle corrections get a reason that names the particle.

Seen playing the web front end: ❌ "駅に行くのバス" → ✅ "駅に行くバス" came
with the reason (バス前を省略します) — "omit before bus", which names neither
the の that was removed nor why. The correction was right; the explanation
taught nothing, and it is the part a learner reads to avoid the mistake next
time. No eval reads Japanese reasons (eval_coachreason is English-only), so
this was invisible.

When the ❌ and ✅ sides differ by exactly one particle — removed, added, or
swapped — the change is known exactly, so the reason can be checked against
it: a reason that quotes the particle stays, one that does not is replaced by
a plain statement of the change. Nothing else is touched: a correction that
changes more than one particle, or anything that is not a particle, keeps the
model's reason whatever it says.
"""
import difflib
import re

from ..llm import find_english_clause

# No sentence-final か: probe_ja_reasons found the model "correcting"
# 「図書館に勉強しました」 into a question by adding か — a wrong correction a
# template reason ("ここには「か」が必要です") would only make more convincing.
_PARTICLES = frozenset('はがをにでへとのも') | {'から', 'まで', 'より'}
_BULLET = re.compile(r'^(\s*-\s*❌\s*"(.*?)"\s*→\s*✅\s*"(.*?)")\s*(?:\((.*)\))?\s*$')
_QUOTES = ('「{}」', '『{}』', '"{}"', '“{}”', "'{}'", '（{}）', '({})')


def particle_change(said: str, better: str):
    """('removed'|'added'|'swapped', old, new) for a one-particle edit, else None."""
    ops = [op for op in difflib.SequenceMatcher(None, said, better).get_opcodes()
           if op[0] != 'equal']
    if len(ops) != 1:
        return None
    tag, i1, i2, j1, j2 = ops[0]
    old, new = said[i1:i2], better[j1:j2]
    if tag == 'delete' and old in _PARTICLES:
        return ('removed', old, '')
    if tag == 'insert' and new in _PARTICLES:
        return ('added', '', new)
    if tag == 'replace' and old in _PARTICLES and new in _PARTICLES:
        return ('swapped', old, new)
    return None


def _names(reason: str, particle: str) -> bool:
    return any(q.format(particle) in reason for q in _QUOTES)


def _template(kind: str, old: str, new: str) -> str:
    if kind == 'removed':
        return f'ここに「{old}」は要りません'
    if kind == 'added':
        return f'ここには「{new}」が必要です'
    return f'「{old}」ではなく「{new}」を使います'


def explain_particle_changes(feedback: str, language: str) -> str:
    """Replace a Japanese particle-fix reason that never names the particle,
    and drop any Japanese bullet's reason that is written in English."""
    if language != 'Japanese':
        return feedback
    out = []
    for line in feedback.split('\n'):
        m = _BULLET.match(line)
        change = particle_change(m.group(2), m.group(3)) if m else None
        reason = (m.group(4) or '') if m else ''
        # An English reason in a Japanese session: find_wrong_script guards
        # Chinese, and Latin passes it — seen as (私 is a possessive pronoun,
        # so it should be followed by の), three times in 39.
        english = bool(reason) and bool(find_english_clause(reason, 'Japanese'))
        if change:
            kind, old, new = change
            if english or not any(_names(reason, p) for p in (old, new) if p):
                line = f'{m.group(1)} ({_template(kind, old, new)})'
        elif m and english:
            line = m.group(1)                 # keep the fix, drop the reason
        out.append(line)
    return '\n'.join(out)
