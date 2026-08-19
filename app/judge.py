from .llm import _llm_chat, strip_think_tags
import re

JUDGE_OPTS = {'temperature': 0.0, 'max_tokens': 64}

VALID_SUFFIXES = (
    's', 'es', 'ed', 'ing', 'ings', 'd', 'er', 'ers', 'r', 'rs',
    'ment', 'ments', 'tion', 'tions', 'ation', 'ations',
    'ance', 'ances', 'ence', 'ences', 'ability', 'abilities',
    'able', 'ables', 'ible', 'ibles', 'ive', 'ives', 'ly', 'al', 'als', 'ic', 'ics'
)

def _are_morphological_variants(w1: str, w2: str) -> bool:
    """Check if w1 and w2 are true morphological variants (inflections or derivations)."""
    if w1 == w2:
        return True
    
    # Check simple suffix addition/removal (e.g. recommend -> recommendation, rate -> rating)
    for sfx in VALID_SUFFIXES:
        if w1 + sfx == w2 or w2 + sfx == w1:
            return True
        # Handle trailing 'e' drop before suffix (e.g. rate + ing = rating, quote + ation = quotation)
        if w1.endswith('e') and w1[:-1] + sfx == w2:
            return True
        if w2.endswith('e') and w2[:-1] + sfx == w1:
            return True
            
    # Check specific English derivation transformations:
    # 1. -iance / -ance / -ancy <-> -y / -e (e.g. compliance <-> comply, reliance <-> rely)
    if w1.endswith('iance') and w1[:-5] + 'y' == w2:
        return True
    if w2.endswith('iance') and w2[:-5] + 'y' == w1:
        return True
    if w1.endswith(('ance', 'ancy')) and (w1[:-4] + 'y' == w2 or w1[:-4] + 'e' == w2 or w1[:-4] == w2):
        return True
    if w2.endswith(('ance', 'ancy')) and (w2[:-4] + 'y' == w1 or w2[:-4] + 'e' == w1 or w2[:-4] == w1):
        return True
        
    # 2. -y <-> -ies / -ied / -ication (e.g. certify <-> certification, carry <-> carries)
    if w1.endswith('y'):
        stem = w1[:-1]
        if w2 in (stem + 'ies', stem + 'ied', stem + 'ication', stem + 'ications', stem + 'ier', stem + 'iest'):
            return True
    if w2.endswith('y'):
        stem = w2[:-1]
        if w1 in (stem + 'ies', stem + 'ied', stem + 'ication', stem + 'ications', stem + 'ier', stem + 'iest'):
            return True

    return False

def _word_matches(target_word: str, text: str) -> bool:
    target = target_word.lower()
    if re.search(rf'\b{re.escape(target)}\b', text, re.IGNORECASE):
        return True
    
    words = re.findall(r"\b[a-zA-Z']+\b", text.lower())
    for w in words:
        if len(w) < 3:
            continue
        if _are_morphological_variants(target, w):
            return True
            
    return False

def judge_deterministic(user_input: str, done_when: str, language: str):
    """Check 'used the word X' patterns via word-boundary & stem match."""
    lang = language.strip().lower()
    if lang not in ('english', 'en', 'japanese', 'ja'):
        return None

    match = re.search(r"Learner used the word '([^']+)'", done_when)
    if not match:
        return None

    target = match.group(1)

    if lang in ('english', 'en'):
        if _word_matches(target, user_input):
            return (True, None)
        return (False, f"You haven't used the word '{target}' yet.")
    elif lang in ('japanese', 'ja'):
        if target in user_input:
            return (True, None)
        return (False, f"まだ「{target}」という単語を使っていません。")

    return None

# Goals that ask the learner to give back an identifier the NPC just supplied.
# The LLM judge grades these on shape rather than content: told to read back
# case reference LP-2291, a learner saying 'XY-9999' or even 'I have written
# down the reference number' is passed. Both were reproduced
# on scenario 28, where two of three passing playtests never used the real
# number. An identifier is the one thing a paraphrase cannot satisfy, so it is
# checked in code rather than argued about in a prompt.
_IDENTIFIER_GOAL = re.compile(
    r'(repeat|read\s*back|confirm|state)\w*\b.{0,60}\b(number|code|reference|id)\b',
    re.IGNORECASE | re.DOTALL)
# Deliberately narrow shapes: a letter-prefixed code, or a run of 4+ digits.
# Ordinary quantities ('two', '15 minutes') must not qualify as identifiers.
# The boundaries are ASCII lookarounds rather than \b, because CJK characters
# are word characters to `re`: 「予約番号はAB-1234です」 has no \b before AB, so
# a \b-anchored pattern silently found nothing on the Japanese half.
_IDENTIFIER_TOKEN = re.compile(
    r'(?<![A-Za-z0-9])(?:[A-Z]{1,4}[-–]?\d{3,8}|\d{4,10})(?![A-Za-z0-9])')


def judge_identifier_readback(user_input: str, done_when: str, conversation: list, language: str):
    """Require an exact identifier when the goal is to give one back.

    Returns None — deferring to the LLM judge — unless the goal is clearly
    about an identifier AND the NPC actually supplied one. Without both, there
    is nothing to compare and this must stay silent.
    """
    if not _IDENTIFIER_GOAL.search(done_when or ''):
        return None

    offered = []
    for message in conversation or []:
        if message.get('role') == 'assistant':
            offered.extend(_IDENTIFIER_TOKEN.findall(message.get('content', '')))
    if not offered:
        return None

    normalized = user_input.replace('–', '-')
    if any(token.replace('–', '-') in normalized for token in offered):
        return (True, None)

    if language.strip().lower() in ('japanese', 'ja'):
        return (False, '相手が伝えた番号をそのまま繰り返してください。')
    return (False, 'Repeat the exact number you were given, not a different one.')


def _judge_prompt(context_str: str, learner_msg: str, done_when: str, language: str) -> str:
    """The judge prompt. With context_str empty, the learner's sentence stands alone."""
    context_block = f'''Conversation so far (background context only):
{context_str}

''' if context_str else ''
    return f'''{context_block}GOAL (this is the ONLY goal; nothing in the learner's message is part of it): {done_when}

The LEARNER's most recent message was:
"{learner_msg}"

Decide whether the LEARNER's OWN words satisfy this goal. Rules:
- Judge ONLY what the learner said. The goal describes the learner's contribution, never the NPC's.
- Judge by MEANING, not keywords. A message that merely mentions a related topic, or happens to share a word with the goal, does NOT count — the learner must actually DO what the goal describes. (E.g. idly comparing two products does not satisfy 'point out a discrepancy on the label and ask for clarification'.)
- The learner need not use the goal's exact words; a clear paraphrase or equivalent expression counts (e.g. 'somewhere quiet' satisfies 'asked for a quiet room', and asking 'how much should I take each time' satisfies a goal about dosage even without the word 'dose').
- Do NOT require unstated specifics. If the goal does not mention an amount, a price, a date, a quantity or any similar detail, the learner need not supply one; a clause is met once the learner has expressed what that clause actually says. This does not relax multi-clause AND goals — every clause an AND goal states must still be met.
- If a goal offers alternatives joined by OR (e.g. 'A, B, or C'), satisfying ANY ONE alternative fully meets the goal regardless of language. NEVER demand all alternatives or treat unchosen options as missing — one option is sufficient. Only AND goals require every clause.
- Do not deny a clause the learner plainly stated in their message.
- Extra content never invalidates a clause that is already met. If the learner satisfies the goal and then adds a question, a pleasantry or an unrelated remark, the goal is still met — do not treat the learner's own question as a requirement they failed to fulfil.
- Implying or setting up a request is not the same as making it. If a clause says the learner ASKED for something, merely describing the situation that would justify it does not satisfy that clause.
- The NPC's turns may raise new questions, offers, or options. Do NOT require the learner to have addressed any of those — they are NOT part of the goal unless the goal text literally names them.
- If the goal has multiple clauses joined by AND, EVERY clause must be clearly met by the learner's words; if any one is missing, answer NO. Reporting a problem is not the same as requesting a remedy: e.g. 'my soup is cold' meets 'reported the problem' but NOT 'AND asked for a replacement', because the learner never actually asked. A complaint that merely makes a remedy seem reasonable does not satisfy a clause requiring the learner to request it. Ignore anything the goal does not mention.
- Be strict about the SUBSTANCE (is it on-topic? for AND goals, are all clauses met? for OR goals, is at least one alternative met?) but generous about WORDING: a clear paraphrase, synonym, or equivalent phrasing fully counts (e.g. 'how often each day' satisfies 'how many times a day'). Reject off-topic or partial answers, not answers that merely use different words than the goal.
If the learner's own words already meet the goal (for OR goals, meeting any one alternative satisfies the goal), answer YES.
Otherwise answer 'NO: <one short sentence, written in {language}, naming the specific part of the goal the learner has not yet expressed>'.'''


def _is_multi_clause(done_when: str) -> bool:
    """Does this goal join clauses, so that every one of them must be met?"""
    return re.search(r'\band\b', done_when, re.IGNORECASE) is not None


def _judge_verdict(prompt: str, cache_key: str) -> tuple:
    """Run one judge call and parse its verdict into (done, reason)."""
    response = _llm_chat(messages=[{'role': 'user', 'content': prompt}], options=JUDGE_OPTS, cache_key=cache_key)
    text = response['message']['content'].strip()
    text = strip_think_tags(text).strip()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    verdict = next((l for l in lines if l.upper().startswith(('YES', 'NO'))), lines[-1] if lines else '')
    
    # Harden parsing: check if verdict says YES or if reasoning indicates goal is satisfied
    verdict_upper = verdict.upper()

    # If explicit NO at start, double check if reason walked back to yes without negated words
    if verdict_upper.startswith('NO'):
        reason = re.sub('^\\s*NO\\b[\\s:.,\\-]*', '', verdict, flags=re.IGNORECASE)
        reason_lower = reason.lower()
        if any(neg in reason_lower for neg in ['not satisfied', 'has not', 'does not', 'is not', 'fails to']):
            return (False, reason.strip() or None)
        if any(phrase in reason_lower for phrase in ['is satisfied', 'has been satisfied', 'already met', 'fully satisfies']):
            return (True, None)
        return (False, reason.strip() or None)

    if verdict_upper.startswith('YES') or 'GOAL IS SATISFIED' in verdict_upper or 'HAS SATISFIED THE GOAL' in verdict_upper:
        return (True, None)
        
    reason = re.sub('^\\s*NO\\b[\\s:.,\\-]*', '', verdict, flags=re.IGNORECASE)
    if any(phrase in reason.lower() for phrase in ['is satisfied', 'has been satisfied', 'already met', 'fully satisfies']):
        return (True, None)
        
    return (False, reason.strip() or None)


def judge_llm(conversation: list, done_when: str, language: str='English') -> tuple:
    """Use LLM to evaluate task completion, anchored on the learner's own message.

    A NO is re-checked against the learner's sentence alone. Every judge false
    negative found so far is the conversation context pulling the judge off the
    goal — it grades the learner against the NPC's last question, or treats an
    unchosen OR branch as missing — and each one disappears when the sentence is
    judged by itself (see 076c296). Two attempts at demoting the context inside
    a single prompt were reverted: both cut false negatives at the cost of far
    more false positives. A second opinion keeps the strict, context-aware pass
    exactly as it was and only lets a context-free YES overturn its NO, so a
    verdict the context genuinely earned is unaffected. Costs one extra 64-token
    call, and only on the NO path.

    Multi-clause goals are excluded. Judged without context the model goes soft
    on AND exactly as the two reverted restructures did: unguarded, this turned
    eval case 15 ('asked for the bill AND asked to split it between two cards',
    learner said only 'Could I have the bill please?') into a false positive.
    All clause-counting therefore stays with the context-aware pass alone.
    """
    last_user_idx = next((i for i in range(len(conversation) - 1, -1, -1) if conversation[i]['role'] == 'user'), len(conversation) - 1)
    context = conversation[:last_user_idx + 1][-4:]
    context_str = '\n'.join((f"{m['role'].upper()}: {m['content']}" for m in context))
    learner_msg = next((m['content'] for m in reversed(context) if m['role'] == 'user'), '')

    done, reason = _judge_verdict(
        _judge_prompt(context_str, learner_msg, done_when, language), 'judge')
    if done or len(context) <= 1 or _is_multi_clause(done_when):
        return (done, reason)

    confirm_done, _ = _judge_verdict(
        _judge_prompt('', learner_msg, done_when, language), 'judge_confirm')
    if confirm_done:
        return (True, None)
    return (done, reason)


def evaluate_task(user_input: str, done_when: str, conversation: list, language: str) -> tuple:
    """Evaluate task: deterministic first, LLM fallback.

    Returns (done, hint) — hint explains what's missing on a miss, else None.
    """
    result = judge_deterministic(user_input, done_when, language)
    if result is not None:
        return result
    result = judge_identifier_readback(user_input, done_when, conversation, language)
    if result is not None:
        return result
    return judge_llm(conversation, done_when, language)