import ollama
import httpx
import os
import re
import time
TRANSLATE_OPTS = {'temperature': 0.0, 'num_ctx': 4096, 'num_predict': 1024}
BASE_MODEL = 'qwen3:8b'
CLOSED_OPENERS = {'do', 'does', 'did', 'is', 'are', 'was', 'were', 'can', 'could', 'will', 'would', 'should', 'have', 'has', 'want', 'need', 'may', 'am'}
WH_WORDS = {'what', 'why', 'how', 'which', 'where', 'when', 'who'}
EMOJI_PATTERN = r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u27BF]'
DEBUG = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 60.0
_client = ollama.Client(timeout=httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT))
OLLAMA_ERRORS = (ConnectionError, httpx.TimeoutException, ollama.ResponseError)

def describe_ollama_error(e: Exception) -> str:
    """Turn a connection/timeout/API exception into a learner-facing hint."""
    if isinstance(e, httpx.TimeoutException):
        return f'Ollama took longer than {READ_TIMEOUT:.0f}s to respond.'
    if isinstance(e, ConnectionError):
        return "Can't connect to Ollama. Is 'ollama serve' running?"
    return str(e)
ACTOR_OPTS = {'temperature': 0.6, 'num_ctx': 8192, 'num_predict': 200}
NPC_MOODS = ['harried and rushing, keen to keep things moving', 'chatty and friendly, happy to chat while you work', 'curt and impatient, giving clipped answers', 'skeptical and questioning, wanting things spelled out', 'cheerful but scatterbrained, easily sidetracked', 'calm and unhurried, taking your time with the customer']
ACTOR_SYS = '{task_setup}\n\nSTOP AND THINK FIRST: does a {role} at {place} actually sell or provide\nwhat the customer just asked for? A pharmacy does not serve coffee or food.\nA hotel front desk does not serve coffee or food. A coffee shop does not fill\nprescriptions. If the request does not belong here, you MUST refuse it in\ncharacter and redirect — you are NOT allowed to just go along with it anyway.\n\nVOCABULARY EXPLANATION: If you naturally use a genuinely advanced, specialist, or uncommon word in your dialogue that the learner might not know (e.g., "single-origin", "amenities", "saffron-infused"), you MUST extract it and provide an explanation.\nDo NOT explain the word inside your spoken dialogue. Instead, append a special XML block at the very end of your response, after your dialogue, exactly like this:\n<vocab>\nword: [the difficult word]\nexplanation: [a short, clear definition of the word in {language}]\nencourage: [a short sentence in {language} encouraging the user to try using this word in their next reply]\n</vocab>\nIf you did not use any difficult words, do not include this block. Do not use this for basic everyday words.\n\nYou are a role-play character in a language-learning conversation.\n\nSETTING: {place}\nYOUR ROLE: {role}\nTODAY YOUR MOOD IS: {mood}. Let this colour your tone, pacing, and how much you\npush back — stay fully in character and never announce it out loud.{complication}\n\nRules:\n- Stay fully in character. You are a real person, not an AI assistant.\n- Respond ONLY in {language}.\n- The learner is advanced (CEFR C1). Speak to them as you would to any fluent\n  adult native speaker — do not simplify, hedge, or slow down for them.\n- Say 2-3 sentences of natural, spoken dialogue, then stop.\n- Remember: this is role-play, not a real situation the learner already has\n  an opinion about. They may not know what to say next, and they may be\n  thinking in Thai and searching for the English/Japanese words. YOU lead the\n  conversation, not them — never leave them facing a blank, open question\n  with nothing to react to.\n- End every turn with something concrete the learner can grab onto: name 2-3\n  specific options for them to choose between or react to (using words they\n  can borrow straight from your sentence), or ask them to compare two things\n  you just mentioned. Do NOT end with a vague open prompt like "tell me\n  more," "explain," or "what do you think" with nothing concrete attached —\n  give them the raw material to answer with. NEVER ask a yes/no question.\n- Include at least one C1-level structure in every turn: an idiom, a nuanced\n  collocation, a conditional, a passive construction, or a cleft sentence\n  ("What really matters is..."). Do not simplify your language for the\n  learner.\n- Write ONLY spoken words. No narration, no stage directions, no asterisks,\n  no parentheses, no emojis, no character name prefixes.\n- For requests that ARE plausible for {role} at {place}, don\'t just comply\n  instantly every single time. Sometimes (not always — vary it) introduce a\n  small, realistic complication a real {role} might actually face: something\n  is out of stock, a policy limits what you can do, there\'s a price\n  difference, or a scheduling conflict. Make the learner negotiate, ask a\n  follow-up, or propose an alternative before you resolve it.\n- BUT do not stack obstacles on the SAME request: once the learner has clearly\n  negotiated or committed to a specific alternative in response to an\n  unavailability, shortage, or problem you raised — i.e. they\'ve acknowledged\n  it and picked a substitute, with or without a reason — ACCEPT their choice\n  and move the conversation forward. Do NOT then reveal that their chosen\n  alternative is ALSO unavailable, and do NOT introduce a second obstacle onto\n  that same request. Resolve it; save any fresh complication for a different,\n  later request.\n- You may still disagree with their OPINIONS and defend your own. If they say\n  the espresso tastes burnt, tell them why you rate it. Have taste, not just\n  service.\n- If their reply is short, hesitant, unclear, or seems stuck, do not just\n  press them for more with no help. Be like a patient native speaker talking\n  to a foreigner: offer your best guess at what they might mean, or suggest\n  2-3 concrete things they might want, and let them react to your guess\n  instead of inventing their own from nothing.'
GREETING_SYS = "You are a role-play character in a language-learning conversation.\n\nSETTING: {place}\nYOUR ROLE: {role}\nTODAY YOUR MOOD IS: {mood}. Let this colour your tone — stay fully in character\nand never announce it out loud.{complication}\n\n{task_setup}\n\nThis is your FIRST turn. Greet the customer, name the place, and set the scene.\nSay 2-4 short sentences of natural spoken dialogue, then end with an\nopen-ended question that requires more than a yes/no answer (e.g. ask what\nthey're looking for, or how you can help). NEVER ask a yes/no question.\n\nVOCABULARY EXPLANATION: If you naturally use a genuinely advanced, specialist, or uncommon word in your dialogue that the learner might not know (e.g., \"single-origin\", \"amenities\", \"saffron-infused\"), you MUST extract it and provide an explanation.\nDo NOT explain the word inside your spoken dialogue. Instead, append a special XML block at the very end of your response, after your dialogue, exactly like this:\n<vocab>\nword: [the difficult word]\nexplanation: [a short, clear definition of the word in {language}]\nencourage: [a short sentence in {language} encouraging the user to try using this word in their next reply]\n</vocab>\nIf you did not use any difficult words, do not include this block. Do not use this for basic everyday words.\n\nRules:\n- Stay fully in character. You are a real person, not an AI assistant.\n- Respond ONLY in {language}.\n- Write ONLY spoken words. No narration, no stage directions, no asterisks,\n  no parentheses, no emojis, no character name prefixes."

def build_task_setup_block(task) -> str:
    """Task-awareness slot for the actor/greeting prompt.

    The actor is otherwise decoupled from the task judge, so an objective that
    presupposes a situation the NPC must create (an item out of stock, a wrong
    order, a billing error) would never get set up — the learner is left
    reacting to a premise nobody stated. This tells the actor to enact that
    premise in its OWN turn when the current goal needs it. The judge never
    sees this; it only shapes dialogue.
    """
    is_reactive = getattr(task, 'reactive', False)
    scene_hint = getattr(task, 'scene_hint', '')
    
    if not is_reactive and not scene_hint:
        return "" # Do not leak the learner's goal to the NPC if the NPC doesn't need to set up anything.

    base = f'''SET THE SCENE FIRST — HIGHEST PRIORITY THIS TURN, ABOVE VOCABULARY COACHING: the learner is secretly working toward this goal, which they can see and you normally can't: "{task.goal} — specifically, {task.done_when}" Read it carefully. If the goal has the learner REACTING to a problem — their order being unavailable or sold out, a wrong or mismatched order, a price or billing error, a policy limit, a discrepancy, or a difficult question — then that problem only exists if YOU make it happen. When it applies, you MUST state that problem plainly and concretely in your OWN dialogue THIS turn, even if the learner's request sounds perfectly routine: name the exact thing they just asked for and tell them what's wrong with it (e.g. if they order a specific item and the goal is about unavailability → "I'm so sorry, we've just run out of [item] today"), or ask them the difficult question, then offer alternatives or let them react. Do NOT quietly fulfil the request as if the problem weren't there, and do NOT wait for the learner to invent the premise.'''
    
    if scene_hint:
        base += f" ONE MORE THING: this goal has the learner reacting to an ambient condition of the setting itself, not to their order — namely, {scene_hint} That condition is not real unless YOU put it in the scene, so weave it into your OWN dialogue THIS turn as a plain, matter-of-fact part of greeting or serving them — make it observably true so the learner has something concrete and already-established to point to. Do NOT flag it as a problem yourself, apologise for it, or tell the learner to react to it; just let it be evidently the case in the scene."
    return base

def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> reasoning traces (qwen3) and any stray tags."""
    text = re.sub('<think>.*?</think>', '', text, flags=re.DOTALL)
    return re.sub('<[^>]+>', '', text)

def sanitize(text: str, speaker: str=None) -> str:
    """Strip reasoning traces, stage directions, character prefixes, and emoji.

    `speaker` should be the known character name (e.g. "Barista") so only
    that exact prefix is stripped — a generic \\w+: pattern would also eat
    the first clause of real dialogue that happens to start the same way
    (e.g. "Sure: here you go." -> "here you go.").
    """
    text = strip_think_tags(text)
    text = re.sub('\\*+[^*]*\\*+', '', text)
    text = re.sub('\\([^)]*\\)', '', text)
    if speaker:
        text = re.sub(f'^\\s*{re.escape(speaker)}\\s*:\\s*', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(EMOJI_PATTERN, '', text)
    text = re.sub('\\s{2,}', ' ', text).strip()
    text = text.strip('"')
    return text

def validate(text: str, max_sentences: int=3) -> tuple[bool, str]:
    """Check sanitized actor output against format rules."""
    if not text:
        return (False, 'Empty response')
    if re.search('[*\\[\\]<>]', text):
        return (False, 'Contains residual markup characters')
    if re.search(EMOJI_PATTERN, text):
        return (False, 'Contains emoji')
    sentences = [s.strip() for s in re.split('(?<=[.!?。！？])\\s*', text) if s.strip()]
    if len(sentences) > max_sentences:
        return (False, f'Too many sentences ({len(sentences)})')
    last = sentences[-1] if sentences else ''
    if last.endswith('?'):
        words = re.findall("[a-z']+", last.lower())
        if words and words[0] in CLOSED_OPENERS and (' or ' not in last.lower()) and (not WH_WORDS & set(words)):
            return (False, 'Closed yes/no question')
    return (True, '')

def _llm_chat(messages: list, options: dict) -> dict:
    return _client.chat(model=BASE_MODEL, messages=messages, options=options, think=False)

def translate_hints(tasks: list, language: str) -> dict:
    """Batch-translate task goals into the target language in one LLM call.

    Returns a dict mapping each task's goal to its translation. Falls back
    to the original English goal if the call fails or a line is missing.
    """
    if language.strip().lower() in ('english', 'en'):
        return {t.goal: t.goal for t in tasks}
    numbered = '\n'.join((f'{i + 1}. {t.goal}' for (i, t) in enumerate(tasks)))
    prompt = f'Translate each numbered instruction below into {language}. Keep the numbering. Write ONLY the translations, one per line, no commentary.\n\n{numbered}'
    try:
        response = _llm_chat(messages=[{'role': 'user', 'content': prompt}], options=TRANSLATE_OPTS)
        raw = strip_think_tags(response['message']['content']).strip()
        lines = [l.strip() for l in raw.split('\n') if l.strip()]
        result = {}
        for (i, task) in enumerate(tasks):
            prefix = f'{i + 1}.'
            translated = next((l[len(prefix):].strip() for l in lines if l.startswith(prefix)), None)
            result[task.goal] = translated if translated else task.goal
        return result
    except Exception:
        return {t.goal: t.goal for t in tasks}

def call_actor(messages: list, system_prompt: str, speaker: str=None, max_sentences: int=3) -> str:
    """Call the actor, sanitize and validate. Retry up to 2x on failure."""
    cleaned = ''
    reason = ''
    for attempt in range(3):
        call_messages = [{'role': 'system', 'content': system_prompt}] + messages
        if attempt > 0:
            call_messages.append({'role': 'system', 'content': f'Your previous response was rejected: {reason}. Reply with ONLY {max_sentences} short spoken sentences or fewer. No asterisks, no parentheses, no character names.'})
        t0 = time.time()
        response = _llm_chat(messages=call_messages, options=ACTOR_OPTS)
        elapsed = time.time() - t0
        raw = response['message']['content']
        cleaned = sanitize(raw, speaker=speaker)
        (ok, reason) = validate(cleaned, max_sentences)
        if ok:
            if attempt > 0 and DEBUG:
                print(f'  [ok after {attempt + 1} attempts, {elapsed:.1f}s]')
            return cleaned
        if DEBUG:
            print(f'  [attempt {attempt + 1}/3 rejected: {reason} ({elapsed:.1f}s)]')
    if DEBUG:
        print('  [Warning: actor output failed validation after 3 attempts]')
    return cleaned