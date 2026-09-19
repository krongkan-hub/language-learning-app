"""Deterministic nets for English. Each only ever overturns a CLEAN verdict.

See BACKLOG OPEN-39 for why this exists and what was measured against it.
"""
import re

from ..verdict import is_clean_verdict


_PAST_MARKER = re.compile(
    r'\b(yesterday|last (?:night|week|month|year|monday|tuesday|wednesday|'
    r'thursday|friday|saturday|sunday)|\d+ (?:days?|weeks?|months?|years?) ago)\b',
    re.I)

# present form -> past form. Only verbs whose present form is not also a common
# noun ("work", "order", "book", "call" are deliberately absent: "last week's
# work" must not look like a verb).
_PAST_OF = {
    'buy': 'bought', 'go': 'went', 'goes': 'went', 'eat': 'ate', 'eats': 'ate',
    'see': 'saw', 'sees': 'saw', 'come': 'came', 'comes': 'came',
    'take': 'took', 'takes': 'took', 'get': 'got', 'gets': 'got',
    'give': 'gave', 'gives': 'gave', 'find': 'found', 'finds': 'found',
    'meet': 'met', 'meets': 'met', 'pay': 'paid', 'pays': 'paid',
    'drive': 'drove', 'drives': 'drove', 'write': 'wrote', 'writes': 'wrote',
    'speak': 'spoke', 'speaks': 'spoke', 'break': 'broke', 'breaks': 'broke',
    'lose': 'lost', 'loses': 'lost', 'leave': 'left', 'leaves': 'left',
    'bring': 'brought', 'brings': 'brought', 'catch': 'caught',
    'catches': 'caught', 'teach': 'taught', 'teaches': 'taught',
    'think': 'thought', 'thinks': 'thought',
    'forget': 'forgot', 'forgets': 'forgot', 'send': 'sent', 'sends': 'sent',
    'spend': 'spent', 'spends': 'spent', 'wear': 'wore', 'wears': 'wore',
    'choose': 'chose', 'chooses': 'chose', 'arrive': 'arrived',
    'arrives': 'arrived', 'travel': 'travelled', 'travels': 'travelled',
    'visit': 'visited', 'visits': 'visited', 'stay': 'stayed',
    'stays': 'stayed', 'walk': 'walked', 'walks': 'walked',
}
_SUBJECT = r'(?:i|we|you|they|he|she|it|my \w+|the \w+)'
_PRESENT_AFTER_MARKER = re.compile(
    r'\b(' + _SUBJECT + r')\s+(' + '|'.join(sorted(_PAST_OF, key=len, reverse=True)) + r')\b',
    re.I)
_DID_PAST = re.compile(
    r"\b(did ?n[o']?t|did)\s+(" + '|'.join(sorted(set(_PAST_OF.values()), key=len, reverse=True))
    + r"|\w+ed)\b", re.I)
_BASE_OF = {past: pres for pres, past in _PAST_OF.items() if not pres.endswith('s')}
_THIRD_DONT = re.compile(r"\b(he|she|it)\s+(don ?'?t)\b", re.I)


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
            # "studied" -> "study", "walked" -> "walk". Deliberately not
            # attempting doubled consonants ("stopped" -> "stop"): a wrong
            # base is a wrong correction, and the -ed forms this reaches are
            # the ones the closed list above already vouches for.
            base = verb[:-3] + 'y' if verb.lower().endswith('ied') else verb[:-2]
        if base:
            bullets.append((did.group(0), f'{aux} {base}',
                            f'"{aux.split()[0]}" already carries the past — the '
                            f'verb after it stays in its base form'))

    if _PAST_MARKER.search(user_input):
        hit = _PRESENT_AFTER_MARKER.search(user_input)
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
