from .llm import _llm_chat, strip_think_tags
import re
BASE_MODEL = 'qwen3:8b'
JUDGE_OPTS = {'temperature': 0.0, 'num_ctx': 4096, 'num_predict': 64}



def judge_deterministic(user_input: str, done_when: str, language: str):
    """Check 'used the word X' patterns via word-boundary match.

    The scenario data only ever names the English word (e.g. "decaf"), so
    this literal match is only meaningful when practicing English. For any
    other target language (e.g. Japanese), the learner would say the word's
    Japanese equivalent, which this regex can never match — defer to the
    LLM judge instead, which can recognize the concept regardless of language.

    Returns (done, hint) where hint is a note on what's missing when done is
    False (None when done), or None if LLM evaluation is needed instead.
    """
    if language.strip().lower() not in ('english', 'en'):
        return None
    match = re.search("Learner used the word '(\\w+)'", done_when)
    if match:
        word = match.group(1)
        if re.search(f'\\b{re.escape(word)}\\b', user_input, re.IGNORECASE):
            return (True, None)
        return (False, f"You haven't used the word '{word}' yet.")
    return None

def judge_llm(conversation: list, done_when: str, language: str='English') -> tuple:
    """Use LLM to evaluate task completion, anchored on the learner's own message.

    `done_when` is always about what the LEARNER says or does. Recent turns are
    passed as background so multi-clause goals that react to something the NPC
    established ("acknowledge the unavailability AND...") can still be judged,
    but the verdict must hinge on the learner's own contribution — never on
    whether they answered the NPC's latest follow-up question or offer, which is
    new material outside the goal unless the goal text names it.

    Returns (done, hint); on a miss, hint is the judge's own one-sentence
    reason naming the part of the goal not yet satisfied (None on success or
    when the judge gives no reason).
    """
    last_user_idx = next((i for i in range(len(conversation) - 1, -1, -1) if conversation[i]['role'] == 'user'), len(conversation) - 1)
    context = conversation[:last_user_idx + 1][-4:]
    context_str = '\n'.join((f"{m['role'].upper()}: {m['content']}" for m in context))
    learner_msg = next((m['content'] for m in reversed(context) if m['role'] == 'user'), '')
    prompt = f'''Conversation so far (background context only):\n{context_str}\n\nThe LEARNER's most recent message was:\n"{learner_msg}"\n\nGOAL: {done_when}\n\nDecide whether the LEARNER's OWN words satisfy this goal. Rules:\n- Judge ONLY what the learner said. The goal describes the learner's contribution, never the NPC's.\n- Judge by MEANING, not keywords. A message that merely mentions a related topic, or happens to share a word with the goal, does NOT count — the learner must actually DO what the goal describes. (E.g. idly comparing two products does not satisfy 'point out a discrepancy on the label and ask for clarification'.)\n- The learner need not use the goal's exact words; a clear paraphrase or equivalent expression counts (e.g. 'somewhere quiet' satisfies 'asked for a quiet room', and asking 'how much should I take each time' satisfies a goal about dosage even without the word 'dose').\n- The NPC's turns may raise new questions, offers, or options. Do NOT require the learner to have addressed any of those — they are NOT part of the goal unless the goal text literally names them.\n- If the goal has multiple clauses joined by AND, EVERY clause must be clearly met by the learner's words; if any one is missing, answer NO. Ignore anything the goal does not mention.\n- Be strict about the SUBSTANCE (is it on-topic, are all clauses present?) but generous about WORDING: a clear paraphrase, synonym, or equivalent phrasing fully counts (e.g. 'how often each day' satisfies 'how many times a day'). Reject off-topic or partial answers, not answers that merely use different words than the goal.\nIf the learner's own words already meet the goal, answer YES.\nOtherwise answer 'NO: <one short sentence, written in {language}, naming the specific part of the goal the learner has not yet expressed>'. /no_think'''
    response = _llm_chat(messages=[{'role': 'user', 'content': prompt}], options=JUDGE_OPTS)
    text = response['message']['content'].strip()
    text = strip_think_tags(text).strip()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    verdict = next((l for l in lines if l.upper().startswith(('YES', 'NO'))), lines[-1] if lines else '')
    if verdict.upper().startswith('YES'):
        return (True, None)
    reason = re.sub('^\\s*NO\\b[\\s:.,\\-]*', '', verdict, flags=re.IGNORECASE)
    return (False, reason.strip() or None)

def evaluate_task(user_input: str, done_when: str, conversation: list, language: str) -> tuple:
    """Evaluate task: deterministic first, LLM fallback.

    Returns (done, hint) — hint explains what's missing on a miss, else None.
    """
    result = judge_deterministic(user_input, done_when, language)
    if result is not None:
        return result
    return judge_llm(conversation, done_when, language)