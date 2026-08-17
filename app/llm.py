import os
import re
import threading
import time
from typing import Optional, Callable
from mlx_lm import load, generate, stream_generate
from mlx_lm.models.cache import make_prompt_cache, trim_prompt_cache, can_trim_prompt_cache, cache_length

TRANSLATE_OPTS = {'temperature': 0.0, 'max_tokens': 1024}
BASE_MODEL = 'mlx-community/Qwen2.5-7B-Instruct-4bit'

CLOSED_OPENERS = {'do', 'does', 'did', 'is', 'are', 'was', 'were', 'can', 'could', 'will', 'would', 'should', 'have', 'has', 'want', 'need', 'may', 'am'}
WH_WORDS = {'what', 'why', 'how', 'which', 'where', 'when', 'who'}
EMOJI_PATTERN = r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u27BF]'
DEBUG = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')

_llm_lock = threading.Lock()
_model = None
_tokenizer = None

_prompt_caches = {}
PROMPT_CACHE_MAX_ENTRIES = 3
PROMPT_CACHE_MAX_KV_SIZE = 4096
PROMPT_CACHE_PREFIX_THRESHOLD = 256

def reset_prompt_caches():
    """Clear all prompt KV caches."""
    with _llm_lock:
        _prompt_caches.clear()

def _longest_common_prefix(seq1: list, seq2: list) -> int:
    """Compute the length of the longest common prefix between two lists."""
    min_len = min(len(seq1), len(seq2))
    idx = 0
    while idx < min_len and seq1[idx] == seq2[idx]:
        idx += 1
    return idx

def _prepare_prompt_cache_for_call(model, tokenizer, prompt_text: str, cache_key: str):
    """Retrieve or initialize prompt cache for cache_key, trimming if prefix matches threshold.

    Must be called while holding `_llm_lock`.
    Returns (prompt_cache, prompt_arg, full_tokens).
    """
    full_tokens = tokenizer.encode(prompt_text)
    now = time.time()

    if cache_key in _prompt_caches:
        entry = _prompt_caches[cache_key]
        cached_cache = entry['cache']
        cached_tokens = entry['tokens']
        prefix_len = _longest_common_prefix(full_tokens, cached_tokens)

        if prefix_len == len(full_tokens):
            if len(full_tokens) > 1:
                prefix_len = len(full_tokens) - 1
            else:
                prefix_len = 0

        try:
            curr_len = cache_length(cached_cache)
        except Exception:
            curr_len = -1

        try:
            can_trim = can_trim_prompt_cache(cached_cache)
        except Exception:
            can_trim = False

        if (
            prefix_len >= PROMPT_CACHE_PREFIX_THRESHOLD
            and can_trim
            and curr_len >= prefix_len
        ):
            tokens_to_trim = curr_len - prefix_len
            try:
                trim_prompt_cache(cached_cache, tokens_to_trim)
                entry['last_used'] = now
                return cached_cache, full_tokens[prefix_len:], full_tokens
            except Exception:
                _prompt_caches.pop(cache_key, None)
        else:
            _prompt_caches.pop(cache_key, None)

    while len(_prompt_caches) >= PROMPT_CACHE_MAX_ENTRIES:
        lru_key = min(_prompt_caches.keys(), key=lambda k: _prompt_caches[k]['last_used'])
        del _prompt_caches[lru_key]

    new_cache = make_prompt_cache(model, max_kv_size=PROMPT_CACHE_MAX_KV_SIZE)
    return new_cache, full_tokens, full_tokens

def _save_prompt_cache_on_success(cache_key: str, cache_obj, full_tokens: list):
    """Store updated cache object and full tokens for cache_key on successful generation.

    Must be called while holding `_llm_lock`.
    """
    _prompt_caches[cache_key] = {
        'cache': cache_obj,
        'tokens': full_tokens,
        'last_used': time.time()
    }

def _ensure_model():
    """Load the MLX model on first use. Raises with the original cause on failure."""
    global _model, _tokenizer
    if _model is not None and _tokenizer is not None:
        return _model, _tokenizer
    with _llm_lock:
        if _model is not None and _tokenizer is not None:
            return _model, _tokenizer
        try:
            m, t = load(BASE_MODEL)
            _model, _tokenizer = m, t
            return _model, _tokenizer
        except Exception as e:
            _model, _tokenizer = None, None
            raise RuntimeError(
                f"Failed to load MLX model '{BASE_MODEL}'. "
                f"Please run setup.sh or check the model cache under ~/.cache/huggingface/hub/."
            ) from e

# Deliberately broad because MLX_ERRORS is used at top-level user-facing CLI boundaries
# to present clean error messages rather than tracebacks to learners.
MLX_ERRORS = (RuntimeError, ValueError, OSError, FileNotFoundError)

def describe_llm_error(e: Exception) -> str:
    """Turn an MLX exception into a learner-facing hint."""
    return f"MLX Engine Error: {str(e)}"
ACTOR_OPTS = {'temperature': 0.6, 'max_tokens': 200}
NPC_MOODS = ['harried and rushing, keen to keep things moving', 'chatty and friendly, happy to chat while you work', 'curt and impatient, giving clipped answers', 'skeptical and questioning, wanting things spelled out', 'cheerful but scatterbrained, easily sidetracked', 'calm and unhurried, taking your time with the customer']
ACTOR_SYS = '{task_setup}\n\nSTOP AND THINK FIRST: {role} Setting: {place}.\nDoes the topic or request brought up by the learner actually belong in this setting and match your role? A pharmacy does not serve coffee, a hotel front desk does not fill prescriptions, and a highway patrol officer does not conduct job interviews. If the request does not belong here, you MUST push back in character and redirect — do NOT quietly comply.\n\nVOCABULARY EXPLANATION: You MUST include at least one genuinely advanced, specialist, or uncommon word relevant to {place} that the learner might not know.\nThe word MUST be reusable vocabulary the learner can carry into other conversations: a common noun, verb, adjective, adverb, idiom, or set phrase.\nNEVER pick a proper noun or a name of any kind — not the name of this business or venue, not your own name or any character name, not a place, city, or street name, not a brand or product name, and not any name you invented for flavour. A name teaches the learner nothing reusable.\nRule of thumb: if it would not appear as an ordinary entry in a {language} dictionary, it is not vocabulary — pick something else. If the only unusual word in your dialogue is a name, choose a different advanced word from your dialogue instead.\nAfter your spoken dialogue, you MUST extract it and provide an explanation by appending a special block at the very end of your response, exactly like this:\n<vocab>\nword: [the difficult word]\nexplanation: [a short, clear definition of the word in {language}]\nencourage: [a short sentence in {language} encouraging the user to try using this word in their next reply]\n</vocab>\n\nYou are a role-play character in a language-learning conversation.\n\nSETTING: {place}\nYOUR ROLE: {role}\nTODAY YOUR MOOD IS: {mood}. Let this colour your tone, pacing, and how much you\npush back — stay fully in character and never announce it out loud.{complication}\n\nCRITICAL LANGUAGE RULES:\n- You MUST speak ONLY 100% in {language}.\n- Do NOT speak Thai or any other language, even if you see Thai text in this prompt (such as the secret goal).\n- Your spoken dialogue, vocabulary explanation, and encouragement MUST all be in strictly {language}.\n- Stay fully in character. Act naturally as your role, whether you are an authority figure (interviewer, officer), service provider, neighbor, or colleague.\n- The learner is advanced (CEFR C1). Speak to them as you would to any fluent\n  adult native speaker — do not simplify, hedge, or slow down for them.\n- Say 2-3 sentences of natural, spoken dialogue, then stop. NEVER exceed 3 sentences — a 4th sentence is a hard failure, so if you are close to the limit, end the turn.\n- Remember: this is role-play. YOU help lead the conversation — never leave the learner facing a blank, open question with nothing concrete to react to.\n- End every turn with something concrete the learner can grab onto: name two explicit choices using "or" (e.g. "Would you prefer A or B?"), ask a wh-question related to {place}, or raise a realistic topic.\n- NEVER ask a yes/no question in ANY sentence of your turn (e.g. questions starting with Would, Do, Can, Is, Are, Have, Could, Will, Should, etc.). Single-option questions like "Would you like to see the case?" or "Are you interested?" are strict failures. Every question you ask MUST either start with a wh-word (what, which, how, why, when, where, who) or explicitly list two options separated by "or" (e.g. "Would you like A or B?").\n- Include at least one C1-level structure in every turn: an idiom, a nuanced\n  collocation, a conditional, a passive construction, or a cleft sentence.\n- Write ONLY spoken words. No narration, no stage directions, no asterisks,\n  no parentheses, no emojis, no character name prefixes.'
GREETING_SYS = "You are a role-play character in a language-learning conversation.\n\nSETTING: {place}\nYOUR ROLE: {role}\nTODAY YOUR MOOD IS: {mood}. Let this colour your tone — stay fully in character\nand never announce it out loud.{complication}\n\n{task_setup}\n\nThis is your FIRST turn. Greet the learner in character for your role at {place}, set the scene in 2-3 short spoken sentences, and open the interaction naturally. Say 2-3 sentences maximum. NEVER exceed 3 sentences — a 4th sentence is a hard failure.\n\nVOCABULARY EXPLANATION: You MUST include at least one genuinely advanced, specialist, or uncommon word relevant to {place} that the learner might not know.\nThe word MUST be reusable vocabulary the learner can carry into other conversations: a common noun, verb, adjective, adverb, idiom, or set phrase.\nNEVER pick a proper noun or a name of any kind — not the name of this business or venue, not your own name or any character name, not a place, city, or street name, not a brand or product name, and not any name you invented for flavour. A name teaches the learner nothing reusable.\nRule of thumb: if it would not appear as an ordinary entry in a {language} dictionary, it is not vocabulary — pick something else. If the only unusual word in your dialogue is a name, choose a different advanced word from your dialogue instead.\nAfter your spoken dialogue, you MUST extract it and provide an explanation by appending a special block at the very end of your response, exactly like this:\n<vocab>\nword: [the difficult word]\nexplanation: [a short, clear definition of the word in {language}]\nencourage: [a short sentence in {language} encouraging the user to try using this word in their next reply]\n</vocab>\n\nCRITICAL LANGUAGE RULES:\n- You MUST speak ONLY 100% in {language}.\n- Do NOT speak Thai or any other language, even if you see Thai text in this prompt (such as the secret goal).\n- Your spoken dialogue, vocabulary explanation, and encouragement MUST all be in strictly {language}.\n- Stay fully in character. You are a real person, not an AI assistant.\n- Say 2-3 sentences of natural, spoken dialogue, then stop. NEVER exceed 3 sentences — a 4th sentence is a hard failure.\n- NEVER ask a yes/no question in ANY sentence of your turn (e.g. questions starting with Would, Do, Can, Is, Are, Have, Could, Will, Should, etc.). Single-option questions like \"Would you like to see the case?\" or \"Are you interested?\" are strict failures. Every question you ask MUST either start with a wh-word (what, which, how, why, when, where, who) or explicitly list two options separated by \"or\" (e.g. \"Would you like A or B?\").\n- Write ONLY spoken words. No narration, no stage directions, no asterisks,\n  no parentheses, no emojis, no character name prefixes."

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

def sanitize_learner_input(user_input: str) -> str:
    """Strip system directive injection tokens from learner input."""
    cleaned = re.sub(r'<\|.*?\|>', '', user_input)
    cleaned = re.sub(r'\[System:.*?\]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'</?(?:system|user|assistant|think|vocab)>', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

# Japanese question detection. A polite question ends in か; it is OPEN when it
# carries an interrogative, and closed otherwise. Mirrors the English rule,
# where a wh-word likewise rescues a sentence from the closed-opener test.
#
# いかが is treated as open for exactly that parity: English "How about a
# coffee?" opens with a wh-word and passes, so 「コーヒーはいかがですか」 must too.
# そうですか is excluded because it is an acknowledgement, not a question, and
# would otherwise be rejected as closed.
_JA_KANA = re.compile('[ぁ-んァ-ヴ]')
_JA_QUESTION_END = re.compile('か[。．.？?！!\\s]*$')
_JA_INTERROGATIVES = ('何', 'なに', 'なん', 'どこ', 'いつ', '誰', 'だれ', 'どちら', 'どっち',
                      'どの', 'どれ', 'どう', 'どんな', 'いくつ', 'いくら', 'なぜ', 'いかが')
_JA_NOT_QUESTIONS = ('そうですか',)


def _is_closed_question_ja(sentence: str) -> bool:
    """Japanese branch: ends in か, carries no interrogative."""
    s = sentence.strip()
    if not _JA_QUESTION_END.search(s):
        return False
    if any(phrase in s for phrase in _JA_NOT_QUESTIONS):
        return False
    return not any(word in s for word in _JA_INTERROGATIVES)


def is_closed_question(sentence: str) -> bool:
    """Check if a single sentence is a closed yes/no question.

    Dispatches on script rather than on a language argument, so the ~15
    existing single-argument callers keep working: English text never contains
    kana. The Japanese branch was added after the actor suite was found to be
    enforcing this rule on only half the catalog — `列車のチケットが必要ですか。`
    passed because the test matched ASCII `?` and `[a-z']+` only.
    """
    if _JA_KANA.search(sentence):
        return _is_closed_question_ja(sentence)
    s_lower = sentence.lower()
    if s_lower.endswith('?'):
        words = re.findall("[a-z']+", s_lower)
        if words:
            leading_words = set(words[:3])
            found_opener = leading_words.intersection(CLOSED_OPENERS)
            if found_opener and not (WH_WORDS & set(words)):
                if ' or ' not in s_lower or ' or not' in s_lower or ' or no' in s_lower:
                    return True
    return False

# Simplified-Chinese-only forms plus Chinese function words. Qwen2.5 drifts
# into Chinese on Japanese turns — measured 9 of 30 sampled greetings — and it
# lands most often inside the vocab explanation, which is exactly the text the
# learner reads as a study aid ('explanation: 书店，专门卖书的地方。').
#
# This is a denylist of forms that do not occur in modern Japanese, NOT a Han
# character check: Japanese uses kanji throughout, so rejecting Han would fail
# every correct Japanese turn. 没 is deliberately absent — unlike its
# simplified neighbours it is an ordinary Japanese kanji (没収, 埋没) and would
# be a false positive. Verified quiet against 105 genuine Japanese strings
# drawn from the eval fixtures and the i18n table.
_SIMPLIFIED_ONLY = set('您请欢迎这们说吗呢书门买卖问语汉关闭亚东车长时电见给让还对话讲种业务')


def find_wrong_script(text: str, language: str) -> str:
    """Characters betraying another language's script, or '' if clean."""
    if language != 'Japanese' or not text:
        return ''
    return ''.join(sorted(set(text) & _SIMPLIFIED_ONLY))


def validate(text: str, max_sentences: int=3, language: str='') -> tuple[bool, str]:
    """Check sanitized actor output against format rules.

    `language` is optional and defaults to no script check, so callers that do
    not know it behave exactly as before.
    """
    if not text:
        return (False, 'Empty response')
    # Checked against the FULL text, before the vocab block is stripped below:
    # most leakage is inside the vocab explanation, so checking spoken_only
    # would miss the majority of it.
    leaked = find_wrong_script(text, language)
    if leaked:
        return (False, f'Wrong script for {language}: {leaked}')
    # Strip vocab block (both explicit <vocab> tags and fallback word/explanation/encourage block)
    spoken_only = re.sub(r'<vocab>.*?</vocab>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
    spoken_only = re.sub(r'(?:<vocab>\s*)?word:\s*(.*?)\s+explanation:\s*(.*?)\s+encourage:\s*(.*?)(?:\s*</vocab>)?\s*$', '', spoken_only, flags=re.DOTALL | re.IGNORECASE).strip()
    if re.search(EMOJI_PATTERN, spoken_only):
        return (False, 'Contains emoji')
    if re.search('[*\\[\\]<>]', spoken_only):
        return (False, 'Contains residual markup characters')
    sentences = [s.strip() for s in re.split('(?<=[.!?。！？])\\s*', spoken_only) if s.strip()]
    if len(sentences) > max_sentences:
        return (False, f'Too many sentences ({len(sentences)})')
    
    # Check all sentences for closed yes/no questions (English only per design contract)
    for sentence in sentences:
        if is_closed_question(sentence):
            return (False, 'Closed yes/no question')
    return (True, '')

def _llm_chat(messages: list, options: dict, cache_key: Optional[str] = None) -> dict:
    from mlx_lm.sample_utils import make_sampler
    
    model, tokenizer = _ensure_model()
    
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    temperature = options.get('temperature', 0.6)
    max_tokens = options.get('max_tokens', options.get('num_predict', 200))
    
    sampler = make_sampler(temp=temperature)
    with _llm_lock:
        if cache_key is not None:
            prompt_cache, prompt_arg, full_tokens = _prepare_prompt_cache_for_call(
                model, tokenizer, prompt, cache_key
            )
            try:
                response_text = generate(
                    model, tokenizer, prompt=prompt_arg, max_tokens=max_tokens,
                    sampler=sampler, prompt_cache=prompt_cache
                )
                _save_prompt_cache_on_success(cache_key, prompt_cache, full_tokens)
            except Exception:
                _prompt_caches.pop(cache_key, None)
                raise
        else:
            response_text = generate(
                model, tokenizer, prompt=prompt, max_tokens=max_tokens, sampler=sampler
            )
    return {'message': {'content': response_text}}

def translate_hints(tasks: list, language: str) -> dict:
    """Batch-translate task goals and strategy hints into the target language in one LLM call.

    Returns a dict mapping (idx, text) to its translation for goals and hints.
    Falls back to original English text if the call fails or a line is missing.
    """
    if language.strip().lower() in ('english', 'en'):
        res = {}
        for (i, t) in enumerate(tasks):
            res[(i, t.goal)] = t.goal
            if getattr(t, 'hint', None):
                res[(i, t.hint)] = t.hint
        return res

    items = []
    for (i, t) in enumerate(tasks):
        items.append((len(items) + 1, i, t.goal))
        if getattr(t, 'hint', None):
            items.append((len(items) + 1, i, t.hint))

    numbered = '\n'.join(f'{num}. {text}' for (num, i, text) in items)
    prompt = f'Translate each numbered instruction below into {language}. Keep the numbering. Write ONLY the translations, one per line, no commentary.\n\n{numbered}'
    try:
        response = _llm_chat(messages=[{'role': 'user', 'content': prompt}], options=TRANSLATE_OPTS)
        raw = strip_think_tags(response['message']['content']).strip()
        lines = [l.strip() for l in raw.split('\n') if l.strip()]
        result = {}
        for (num, i, text) in items:
            prefix = f'{num}.'
            translated = next((l[len(prefix):].strip() for l in lines if l.startswith(prefix)), None)
            result[(i, text)] = translated if translated else text
        return result
    except Exception:
        res = {}
        for (i, t) in enumerate(tasks):
            res[(i, t.goal)] = t.goal
            if getattr(t, 'hint', None):
                res[(i, t.hint)] = t.hint
        return res

def repair_actor_output(text: str, max_sentences: int = 3) -> str:
    """Truncate over-length spoken dialogue to max_sentences while preserving trailing vocab block."""
    vocab_match = re.search(r'<vocab>.*?</vocab>', text, flags=re.DOTALL | re.IGNORECASE)
    if not vocab_match:
        vocab_match = re.search(
            r'(?:<vocab>\s*)?word:\s*(.*?)\s+explanation:\s*(.*?)\s+encourage:\s*(.*?)(?:\s*</vocab>)?\s*$',
            text,
            flags=re.DOTALL | re.IGNORECASE
        )
    
    if vocab_match:
        vocab_block = vocab_match.group(0).strip()
        spoken_part = (text[:vocab_match.start()] + text[vocab_match.end():]).strip()
    else:
        vocab_block = ''
        spoken_part = text.strip()

    sentences = [s.strip() for s in re.split(r'(?<=[.!?。！？])\s*', spoken_part) if s.strip()]
    if len(sentences) <= max_sentences:
        return text
    
    truncated_spoken = " ".join(sentences[:max_sentences])
    if vocab_block:
        return f"{truncated_spoken}\n\n{vocab_block}"
    return truncated_spoken

SALVAGE_QUESTIONS = (
    "What would you like to sort out first?",
    "How would you like to proceed?",
    "What can I help you with next?",
)
_salvage_q_idx = 0

def _get_salvage_question() -> str:
    global _salvage_q_idx
    q = SALVAGE_QUESTIONS[_salvage_q_idx % len(SALVAGE_QUESTIONS)]
    _salvage_q_idx += 1
    return q

FALLBACK_ACTOR_LINE = "Let me check that for you. What would you like to do next?"

def salvage_actor_output(text: str, max_sentences: int = 3) -> str:
    """Repair actor output by dropping closed yes/no questions and re-attaching vocab block."""
    if not text or not text.strip():
        return ''

    vocab_match = re.search(r'<vocab>.*?</vocab>', text, flags=re.DOTALL | re.IGNORECASE)
    if not vocab_match:
        vocab_match = re.search(
            r'(?:<vocab>\s*)?word:\s*(.*?)\s+explanation:\s*(.*?)\s+encourage:\s*(.*?)(?:\s*</vocab>)?\s*$',
            text,
            flags=re.DOTALL | re.IGNORECASE
        )

    if vocab_match:
        vocab_block = vocab_match.group(0).strip()
        spoken_part = (text[:vocab_match.start()] + text[vocab_match.end():]).strip()
    else:
        vocab_block = ''
        spoken_part = text.strip()

    sentences = [s.strip() for s in re.split(r'(?<=[.!?。！？])\s*', spoken_part) if s.strip()]
    if not sentences:
        return ''

    valid_sentences = [s for s in sentences if not is_closed_question(s)]

    if len(valid_sentences) > max_sentences:
        valid_sentences = valid_sentences[:max_sentences]

    has_question = any('?' in s for s in valid_sentences)

    if not has_question:
        if len(valid_sentences) >= max_sentences:
            valid_sentences = valid_sentences[:max_sentences - 1]
        valid_sentences.append(_get_salvage_question())

    salvaged_spoken = " ".join(valid_sentences).strip()
    if not salvaged_spoken:
        return ''

    if vocab_block:
        return f"{salvaged_spoken}\n\n{vocab_block}"
    return salvaged_spoken

def call_actor(messages: list, system_prompt: str, speaker: str=None, max_sentences: int=3, cache_key: Optional[str] = 'actor', language: str='') -> str:
    """Call the actor, sanitize and validate. Retry up to 2x on failure, repairing over-length output when possible."""
    cleaned = ''
    reason = ''
    for attempt in range(3):
        call_messages = [{'role': 'system', 'content': system_prompt}] + messages
        if attempt > 0:
            retry_note = f'Your previous response was rejected: {reason}. Reply with ONLY {max_sentences} short spoken sentences or fewer. No asterisks, no parentheses, no character names.'
            if reason.startswith('Wrong script'):
                # The generic note is about length and would not tell the model
                # what actually went wrong; the drift is usually in the vocab
                # explanation rather than the spoken line.
                retry_note = (f'Your previous response was rejected: {reason}. '
                              f'Write EVERY word in {language}, including the vocab '
                              f'explanation and encouragement. Do not use Chinese characters '
                              f'or words that are not {language}.')
            call_messages.append({'role': 'system', 'content': retry_note})
        t0 = time.time()
        response = _llm_chat(messages=call_messages, options=ACTOR_OPTS, cache_key=cache_key)
        elapsed = time.time() - t0
        raw = response['message']['content']
        cleaned = sanitize(raw, speaker=speaker)
        (ok, reason) = validate(cleaned, max_sentences, language)
        if ok:
            if attempt > 0 and DEBUG:
                print(f'  [ok after {attempt + 1} attempts, {elapsed:.1f}s]')
            return cleaned
        
        if reason.startswith('Too many sentences'):
            repaired = repair_actor_output(cleaned, max_sentences)
            (rep_ok, rep_reason) = validate(repaired, max_sentences, language)
            if rep_ok:
                if DEBUG:
                    print(f'  [attempt {attempt + 1}/3 repaired ({reason} -> ok), {elapsed:.1f}s]')
                return repaired
            reason = rep_reason

        if DEBUG:
            print(f'  [attempt {attempt + 1}/3 rejected: {reason} ({elapsed:.1f}s)]')

    if DEBUG:
        print(f'  [Warning: actor output failed validation after 3 attempts: {reason}]')

    salvaged = salvage_actor_output(cleaned, max_sentences)
    if salvaged:
        (sal_ok, _) = validate(salvaged, max_sentences, language)
        if sal_ok:
            return salvaged

    vocab_match = re.search(r'<vocab>.*?</vocab>', cleaned, flags=re.DOTALL | re.IGNORECASE)
    if not vocab_match:
        vocab_match = re.search(
            r'(?:<vocab>\s*)?word:\s*(.*?)\s+explanation:\s*(.*?)\s+encourage:\s*(.*?)(?:\s*</vocab>)?\s*$',
            cleaned,
            flags=re.DOTALL | re.IGNORECASE
        )

    if vocab_match:
        vocab_block = vocab_match.group(0).strip()
        # This block comes from output that just failed validation three times,
        # so it cannot be re-attached unchecked. Enforcing the script rule in
        # the retry loop cut Japanese leakage from 30% to 13%, and every
        # remaining leak arrived here: the fallback line is clean but the card
        # stapled to it still held Chinese. A missing vocab card costs the
        # learner one tip; a card written in the wrong language teaches them
        # the wrong thing.
        if not find_wrong_script(vocab_block, language):
            return f"{FALLBACK_ACTOR_LINE}\n\n{vocab_block}"
    return FALLBACK_ACTOR_LINE


def _find_vocab_start(text: str) -> int:
    """Find the start index of the vocab block (<vocab> or trailing word:/explanation:/encourage:)."""
    m = re.search(r'<vocab>', text, flags=re.IGNORECASE)
    if m:
        return m.start()
    m = re.search(r'(?:^|\n|\s)word:\s*.*?\bexplanation:\s*', text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.start()
    m = re.search(r'(?:\n\s*|^)word:\s*', text, flags=re.IGNORECASE)
    if m:
        return m.start()
    return -1


def stream_actor(
    messages: list,
    system_prompt: str,
    speaker: str = None,
    max_sentences: int = 3,
    callback: Optional[Callable[[str], None]] = None,
    generator_fn = None,
    cache_key: Optional[str] = 'actor'
) -> str:
    """Stream actor response sentence-by-sentence, checking each sentence against validation rules."""
    emitted_sentences = []
    has_question = False
    processed_sentence_count = 0
    raw_text = ""
    vocab_part = ""

    def process_spoken(spoken_chunk: str, is_final: bool = False):
        nonlocal processed_sentence_count, has_question
        parts = re.split(r'(?<=[.!?。！？])\s*', spoken_chunk)
        complete_parts = []
        for i, part in enumerate(parts):
            p_str = part.strip()
            if not p_str:
                continue
            if i < len(parts) - 1 or is_final or re.search(r'[.!?。！？]$', p_str):
                complete_parts.append(p_str)

        while processed_sentence_count < len(complete_parts):
            cand = complete_parts[processed_sentence_count]
            processed_sentence_count += 1

            sanitized_cand = sanitize(cand, speaker=speaker)
            if not sanitized_cand:
                continue

            if re.search(EMOJI_PATTERN, sanitized_cand):
                continue
            if re.search(r'[*\\[\\]<>]', sanitized_cand):
                continue
            if is_closed_question(sanitized_cand):
                continue

            if len(emitted_sentences) >= max_sentences:
                continue

            cand_has_q = '?' in sanitized_cand

            if len(emitted_sentences) == max_sentences - 1 and not has_question and not cand_has_q:
                continue

            emitted_sentences.append(sanitized_cand)
            if cand_has_q:
                has_question = True

            if callback:
                callback(sanitized_cand)

    try:
        if generator_fn is not None:
            gen = generator_fn()
            for item in gen:
                chunk = item.text if hasattr(item, 'text') else str(item)
                raw_text += chunk
                v_idx = _find_vocab_start(raw_text)
                if v_idx != -1:
                    spoken_part = raw_text[:v_idx]
                else:
                    spoken_part = raw_text
                process_spoken(spoken_part, is_final=False)
        else:
            from mlx_lm.sample_utils import make_sampler
            model, tokenizer = _ensure_model()
            call_messages = [{'role': 'system', 'content': system_prompt}] + messages
            prompt = tokenizer.apply_chat_template(call_messages, tokenize=False, add_generation_prompt=True)
            temperature = ACTOR_OPTS.get('temperature', 0.6)
            max_tokens = ACTOR_OPTS.get('max_tokens', 200)
            sampler = make_sampler(temp=temperature)

            with _llm_lock:
                if cache_key is not None:
                    prompt_cache, prompt_arg, full_tokens = _prepare_prompt_cache_for_call(
                        model, tokenizer, prompt, cache_key
                    )
                    try:
                        gen = stream_generate(
                            model, tokenizer, prompt=prompt_arg, max_tokens=max_tokens,
                            sampler=sampler, prompt_cache=prompt_cache
                        )
                        for item in gen:
                            chunk = item.text if hasattr(item, 'text') else str(item)
                            raw_text += chunk
                            v_idx = _find_vocab_start(raw_text)
                            if v_idx != -1:
                                spoken_part = raw_text[:v_idx]
                            else:
                                spoken_part = raw_text
                            process_spoken(spoken_part, is_final=False)
                        _save_prompt_cache_on_success(cache_key, prompt_cache, full_tokens)
                    except Exception:
                        _prompt_caches.pop(cache_key, None)
                        raise
                else:
                    gen = stream_generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens, sampler=sampler)
                    for item in gen:
                        chunk = item.text if hasattr(item, 'text') else str(item)
                        raw_text += chunk
                        v_idx = _find_vocab_start(raw_text)
                        if v_idx != -1:
                            spoken_part = raw_text[:v_idx]
                        else:
                            spoken_part = raw_text
                        process_spoken(spoken_part, is_final=False)

        v_idx = _find_vocab_start(raw_text)
        if v_idx != -1:
            spoken_part = raw_text[:v_idx]
            vocab_part = raw_text[v_idx:].strip()
        else:
            spoken_part = raw_text
            vocab_part = ""

        process_spoken(spoken_part, is_final=True)

    except Exception as e:
        if DEBUG:
            print(f"stream_actor exception: {e}")
        fallback_text = call_actor(messages, system_prompt, speaker=speaker, max_sentences=max_sentences, cache_key=cache_key)
        if callback and not emitted_sentences:
            spoken_only = re.sub(r'<vocab>.*?</vocab>', '', fallback_text, flags=re.DOTALL | re.IGNORECASE).strip()
            spoken_only = re.sub(r'(?:<vocab>\s*)?word:\s*(.*?)\s+explanation:\s*(.*?)\s+encourage:\s*(.*?)(?:\s*</vocab>)?\s*$', '', spoken_only, flags=re.DOTALL | re.IGNORECASE).strip()
            fb_sentences = [s.strip() for s in re.split(r'(?<=[.!?。！？])\s*', spoken_only) if s.strip()]
            for s in fb_sentences:
                callback(s)
        return fallback_text

    if not emitted_sentences:
        fallback_text = call_actor(messages, system_prompt, speaker=speaker, max_sentences=max_sentences, cache_key=cache_key)
        if callback:
            spoken_only = re.sub(r'<vocab>.*?</vocab>', '', fallback_text, flags=re.DOTALL | re.IGNORECASE).strip()
            spoken_only = re.sub(r'(?:<vocab>\s*)?word:\s*(.*?)\s+explanation:\s*(.*?)\s+encourage:\s*(.*?)(?:\s*</vocab>)?\s*$', '', spoken_only, flags=re.DOTALL | re.IGNORECASE).strip()
            fb_sentences = [s.strip() for s in re.split(r'(?<=[.!?。！？])\s*', spoken_only) if s.strip()]
            for s in fb_sentences:
                callback(s)
        return fallback_text

    if not has_question and len(emitted_sentences) < max_sentences:
        salvage_q = _get_salvage_question()
        emitted_sentences.append(salvage_q)
        has_question = True
        if callback:
            callback(salvage_q)

    spoken_assembled = " ".join(emitted_sentences).strip()
    if vocab_part:
        return f"{spoken_assembled}\n\n{vocab_part}"
    return spoken_assembled