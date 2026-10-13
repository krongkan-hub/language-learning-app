"""Deterministic nets for English. Each only ever overturns a CLEAN verdict.

See BACKLOG OPEN-39 for why this exists and what was measured against it.
"""
import re
from typing import Optional

from ..verdict import is_clean_verdict
from ..tables.english import _PAST_OF, _ED_BASES, _MORE_PAST
from ...lexicon import level


_PAST_MARKER = re.compile(
    r'\b(yesterday|last (?:night|week|month|year|monday|tuesday|wednesday|'
    r'thursday|friday|saturday|sunday)|(?:\d+|an?|one|two|three|four|five|six|'
    r'seven|eight|nine|ten|a few|several) (?:days?|weeks?|months?|years?) ago)\b',
    re.I)

_SUBJECT = r'(?:i|we|you|they|he|she|it|my \w+|the \w+)'
_PRESENT_AFTER_MARKER = re.compile(
    r'\b(' + _SUBJECT + r')\s+(' + '|'.join(sorted(_PAST_OF, key=len, reverse=True)) + r')\b',
    re.I)
_DID_PAST = re.compile(
    r"\b(did ?n[o']?t|did)\s+(" + '|'.join(sorted(set(_PAST_OF.values()), key=len, reverse=True))
    + r"|\w+ed)\b", re.I)
_BASE_OF = {past: pres for pres, past in _PAST_OF.items() if not pres.endswith('s')}
_THIRD_DONT = re.compile(r"\b(he|she|it)\s+(don ?'?t)\b", re.I)

# Issue #64: "yesterday" anywhere used to force the first present verb
# anywhere into the past — "I think I left it here yesterday" became "I
# thought". Now the marker and the verb must share a clause, and the clause
# must show no sign that the present is meant or the past already used.
_SENTENCE = re.compile(r'[^.!?;]+')
_CLAUSE_BREAK = re.compile(
    r'\b(?:but|and|so|because|when|while|if|although|though|then|that)\b', re.I)
_ALREADY_PAST = re.compile(
    r"\b(?:" + '|'.join(sorted(set(_PAST_OF.values()) | _MORE_PAST, key=len, reverse=True))
    + r"|didn'?t)\b"
    # a regular -ed, unless it is an adjective after a determiner ("a crowded
    # restaurant"); "need" counts too, which only ever makes the net quieter
    r"|(?<!\ba )(?<!\ban )(?<!\bthe )(?<!\bvery )(?<!\bso )(?<!\btoo )\b\w{2,}ed\b", re.I)
_PRESENT_MEANT = re.compile(
    r"\b(?:now|usually|always|every|often|normally|sometimes|today|tonight|"
    r"tomorrow|next|since|still|will|going to)\b|'ll\b|\bthe last\b"
    r"|\b(?:un)?like (?:yesterday|last)\b|\bas (?:yesterday|last)\b", re.I)
# "I think we meet a week ago": the verb that takes the past is the one in
# the complement, not "think".
_CLAUSE_FOLLOWS = re.compile(r'\s+(?:i|we|you|they|he|she|it|the|my|that)\b', re.I)
# a base form after these is not a finite verb: "Can you take the one from
# yesterday?", "What do you think about yesterday?"
_AUX = {'do', 'does', 'did', "don't", "doesn't", "didn't", 'can', 'could',
        'will', 'would', 'should', 'shall', 'may', 'might', 'must', 'to', 'let'}


def _regular_base(verb: str) -> Optional[str]:
    """The base form of a regular past, or None when it is not certain.

    Each way of undoing -ed is tried ("walked" -> walk, "liked" -> like,
    "stopped" -> stop, "studied" -> study) and kept only if it gives a common
    word; anything but exactly one survivor is silence. -eed verbs and
    _ED_BASES are base forms already ("didn't need", "didn't shed").
    """
    v = verb.lower()
    if v.endswith('eed') or v in _ED_BASES or verb[0].isupper():
        return None
    cands = {v[:-2], v[:-1]}
    if v.endswith('ied'):
        cands.add(v[:-3] + 'y')
    if len(v) > 4 and v[-3] == v[-4]:
        cands.add(v[:-3])
    common = [c for c in cands if len(c) >= 3 and level(c) <= 20]
    return common[0] if len(common) == 1 else None


def _past_time_slip(user_input: str):
    """The first present verb sharing a clause with a past-time word, in a
    clause that gives no reason for the present."""
    for sentence in _SENTENCE.findall(user_input):
        for clause in _CLAUSE_BREAK.split(sentence):
            if (not _PAST_MARKER.search(clause) or _ALREADY_PAST.search(clause)
                    or _PRESENT_MEANT.search(clause)):
                continue
            for hit in _PRESENT_AFTER_MARKER.finditer(clause):
                before = clause[:hit.start()].split()
                if before and before[-1].lower().strip(',') in _AUX:
                    continue
                if (hit.group(2).lower() in ('think', 'thinks')
                        and _CLAUSE_FOLLOWS.match(clause, hit.end())):
                    continue
                return hit
    return None


def apply_verbform_net(feedback: str, user_input: str, language: str) -> str:
    """Catch an English verb form the coach left alone.

    Only ever overturns a clean verdict, like every other net here: a real
    model correction always wins. Measured need — recall on these shapes was
    0/15 while the same model, asked plainly, called them wrong 21/21.
    """
    if language != 'English' or not is_clean_verdict(feedback, language):
        return feedback

    bullets = []

    third = _THIRD_DONT.search(user_input)
    if third:
        bullets.append((third.group(0), f"{third.group(1)} doesn't",
                        'he/she/it takes "doesn\'t"'))

    did = _DID_PAST.search(user_input)
    if did:
        aux, verb = did.group(1), did.group(2)
        base = _BASE_OF.get(verb.lower())
        if base is None and verb.lower().endswith('ed'):
            base = _regular_base(verb)
        if base:
            bullets.append((did.group(0), f'{aux} {base}',
                            f'"{aux.split()[0]}" already carries the past — the '
                            f'verb after it stays in its base form'))

    hit = _past_time_slip(user_input)
    if hit:
        subject, verb = hit.group(1), hit.group(2)
        past = _PAST_OF[verb.lower()]
        bullets.append((hit.group(0), f'{subject} {past}',
                        f'the sentence names a past time, so the verb takes '
                        f'the past tense: "{past}"'))

    if not bullets:
        return feedback
    # Up to two, matching COACH_SYS's own limit. Seen in a live session:
    # "Yesterday I buy a day pass but she don't work" produced only the
    # she/don't bullet, because this returned on its first match while the
    # coach itself is allowed two.
    lines = '\n'.join(f'- ❌ "{was}" → ✅ "{now}" ({why})'
                      for (was, now, why) in bullets[:2])
    return '\U0001f4a1 Feedback:\n' + lines


# "explain/suggest/say" take the listener with "to", never as a bare object.
# coachrecall's ditransitive case sits at 0/5 with the model calling it
# natural three times in five. "recommend me" and "describe me" are left out:
# both have correct readings ("recommend me a hotel" in British English,
# "describe me to the police").
_DITRANSITIVE = re.compile(r'\b(explain|explained|explains|suggest|suggested|suggests|say|said|says)\s+(me|us)\b', re.I)


def apply_ditransitive_net(feedback: str, user_input: str, language: str) -> str:
    """Catch "Can you explain me the rules?" when the coach called it natural."""
    if language != 'English' or not is_clean_verdict(feedback, language):
        return feedback
    hit = _DITRANSITIVE.search(user_input)
    if not hit:
        return feedback
    verb, obj = hit.group(1), hit.group(2)
    if verb.lower().startswith('sa'):
        tell = {'say': 'tell', 'says': 'tells', 'said': 'told'}[verb.lower()]
        return ('\U0001f4a1 Feedback:\n'
                f'- ❌ "{hit.group(0)}" → ✅ "{tell} {obj}" ("say" does not take the '
                f'listener as its object; "tell" does)')
    return ('\U0001f4a1 Feedback:\n'
            f'- ❌ "{hit.group(0)}" → ✅ "{verb} to {obj}" ("{verb.lower()}" takes the '
            f'listener with "to")')


# Playtest 2026-10-09: "Can I sit at outside?" came back "Perfectly natural!"
# with the fix filed under Level up — a grammar error, so no drill. These
# words are adverbs of place and take no preposition. "home" is left out
# ("at home" is right); "to" is only flagged before words nothing can be
# "to" ("go to abroad"), not before "outside the gate".
_PLACE_ADVERB = re.compile(
    r'\b(?:at\s+(?P<a>outside|inside|downstairs|upstairs|abroad|overseas|outdoors|indoors)'
    r'|to\s+(?P<t>abroad|overseas|downstairs|upstairs))\b(?!\s+(?:of|the)\b)', re.I)


def apply_place_adverb_net(feedback: str, user_input: str, language: str) -> str:
    """Catch "sit at outside" and "go to abroad" when the coach called it natural."""
    if language != 'English' or not is_clean_verdict(feedback, language):
        return feedback
    hit = _PLACE_ADVERB.search(user_input)
    if not hit:
        return feedback
    word = hit.group('a') or hit.group('t')
    return ('\U0001f4a1 Feedback:\n'
            f'- ❌ "{hit.group(0)}" → ✅ "{word}" ("{word.lower()}" already means a place, '
            f'so it takes no preposition)')
