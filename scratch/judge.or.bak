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
    if language.strip().lower() not in ('english', 'en'):
        return None
    match = re.search("Learner used the word '(\\w+)'", done_when)
    if match:
        word = match.group(1)
        if _word_matches(word, user_input):
            return (True, None)
        return (False, f"You haven't used the word '{word}' yet.")
    return None

def judge_llm(conversation: list, done_when: str, language: str='English') -> tuple:
    """Use LLM to evaluate task completion, anchored on the learner's own message."""
    last_user_idx = next((i for i in range(len(conversation) - 1, -1, -1) if conversation[i]['role'] == 'user'), len(conversation) - 1)
    context = conversation[:last_user_idx + 1][-4:]
    context_str = '\n'.join((f"{m['role'].upper()}: {m['content']}" for m in context))
    learner_msg = next((m['content'] for m in reversed(context) if m['role'] == 'user'), '')
    prompt = f'''Conversation so far (background context only):\n{context_str}\n\nGOAL (this is the ONLY goal; nothing in the learner's message is part of it): {done_when}\n\nThe LEARNER's most recent message was:\n"{learner_msg}"\n\nDecide whether the LEARNER's OWN words satisfy this goal. Rules:\n- Judge ONLY what the learner said. The goal describes the learner's contribution, never the NPC's.\n- Judge by MEANING, not keywords. A message that merely mentions a related topic, or happens to share a word with the goal, does NOT count — the learner must actually DO what the goal describes. (E.g. idly comparing two products does not satisfy 'point out a discrepancy on the label and ask for clarification'.)\n- The learner need not use the goal's exact words; a clear paraphrase or equivalent expression counts (e.g. 'somewhere quiet' satisfies 'asked for a quiet room', and asking 'how much should I take each time' satisfies a goal about dosage even without the word 'dose').\n- Do NOT require unstated specifics. If the goal does not mention an amount, a price, a date, a quantity or any similar detail, the learner need not supply one; a clause is met once the learner has expressed what that clause actually says. This does not relax multi-clause goals — every clause the goal states must still be met.\n- If a goal offers alternatives joined by OR, ANY ONE of them satisfies it; never demand all of them. Only AND requires every clause.\n- Do not deny a clause the learner plainly stated in their message.\n- Extra content never invalidates a clause that is already met. If the learner satisfies the goal and then adds a question, a pleasantry or an unrelated remark, the goal is still met — do not treat the learner's own question as a requirement they failed to fulfil.\n- Implying or setting up a request is not the same as making it. If a clause says the learner ASKED for something, merely describing the situation that would justify it does not satisfy that clause.\n- The NPC's turns may raise new questions, offers, or options. Do NOT require the learner to have addressed any of those — they are NOT part of the goal unless the goal text literally names them.\n- If the goal has multiple clauses joined by AND, EVERY clause must be clearly met by the learner's words; if any one is missing, answer NO. Reporting a problem is not the same as requesting a remedy: e.g. 'my soup is cold' meets 'reported the problem' but NOT 'AND asked for a replacement', because the learner never actually asked. A complaint that merely makes a remedy seem reasonable does not satisfy a clause requiring the learner to request it. Ignore anything the goal does not mention.\n- Be strict about the SUBSTANCE (is it on-topic, are all clauses present?) but generous about WORDING: a clear paraphrase, synonym, or equivalent phrasing fully counts (e.g. 'how often each day' satisfies 'how many times a day'). Reject off-topic or partial answers, not answers that merely use different words than the goal.\nIf the learner's own words already meet the goal, answer YES.\nOtherwise answer 'NO: <one short sentence, written in {language}, naming the specific part of the goal the learner has not yet expressed>'.'''
    response = _llm_chat(messages=[{'role': 'user', 'content': prompt}], options=JUDGE_OPTS, cache_key='judge')
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

def evaluate_task(user_input: str, done_when: str, conversation: list, language: str) -> tuple:
    """Evaluate task: deterministic first, LLM fallback.

    Returns (done, hint) — hint explains what's missing on a miss, else None.
    """
    result = judge_deterministic(user_input, done_when, language)
    if result is not None:
        return result
    return judge_llm(conversation, done_when, language)