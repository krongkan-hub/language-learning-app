"""The NPC: its prompt, the repair loop, and the two ways it can be read.

`call_actor` assembles a whole turn; `stream_actor` yields sentences as they
arrive. dev/checks/check_actor_path_parity.py asserts the two treat the same
bytes identically — they have diverged twice. See BACKLOG OPEN-31, OPEN-32.
"""
import re

from . import client
import time
from typing import Optional, Callable
from .client import DEBUG
from .guards import (validate, sentence_rejection_reason, is_question,
                     is_closed_question, find_wrong_script, sanitize)
from .vocab import (match_vocab_block, strip_vocab_block)


ACTOR_OPTS = {'temperature': 0.6, 'max_tokens': 200}
NPC_MOODS = ['harried and rushing, keen to keep things moving', 'chatty and friendly, happy to chat while you work', 'curt and impatient, giving clipped answers', 'skeptical and questioning, wanting things spelled out', 'cheerful but scatterbrained, easily sidetracked', 'calm and unhurried, taking your time with the customer']
ACTOR_SYS = '{task_setup}\n\nSTOP AND THINK FIRST: {role} Setting: {place}.\nDoes the topic or request brought up by the learner actually belong in this setting and match your role? A pharmacy does not serve coffee, a hotel front desk does not fill prescriptions, and a highway patrol officer does not conduct job interviews. If the request does not belong here, you MUST push back in character and redirect — do NOT quietly comply.\n\nYou are a role-play character in a language-learning conversation.\n\nSETTING: {place}\nYOUR ROLE: {role}\nTODAY YOUR MOOD IS: {mood}. Let this colour your tone, pacing, and how much you\npush back — stay fully in character and never announce it out loud.{complication}\n\nCRITICAL LANGUAGE RULES:\n- You MUST speak ONLY 100% in {language}.\n- Do NOT speak Thai or any other language, even if you see Thai text in this prompt (such as the secret goal).\n- Your spoken dialogue, vocabulary explanation, and encouragement MUST all be in strictly {language}.\n- Stay fully in character. Act naturally as your role, whether you are an authority figure (interviewer, officer), service provider, neighbor, or colleague.\n- The learner is advanced (CEFR C1). Speak to them as you would to any fluent\n  adult native speaker — do not simplify, hedge, or slow down for them.\n- Write a COMPLETE turn: the spoken dialogue, then the vocabulary block below. EVERY turn carries the block, not just the first one.\n- Say 2-3 sentences of natural, spoken dialogue, then stop. NEVER exceed 3 sentences — a 4th sentence is a hard failure, so if you are close to the limit, end the turn.\n- Remember: this is role-play. YOU help lead the conversation — never leave the learner facing a blank, open question with nothing concrete to react to.\n- Give the learner something concrete to grab onto in your dialogue: name two explicit choices using "or" (e.g. "Would you prefer A or B?"), ask a wh-question related to {place}, or raise a realistic topic.\n- NEVER ask a yes/no question in ANY sentence of your turn (e.g. questions starting with Would, Do, Can, Is, Are, Have, Could, Will, Should, etc.). Single-option questions like "Would you like to see the case?" or "Are you interested?" are strict failures. Every question you ask MUST either start with a wh-word (what, which, how, why, when, where, who) or explicitly list two options separated by "or" (e.g. "Would you like A or B?").\n- Include at least one C1-level structure in every turn: an idiom, a nuanced\n  collocation, a conditional, a passive construction, or a cleft sentence.\n- Write ONLY spoken words. No narration, no stage directions, no asterisks,\n  no parentheses, no emojis, no character name prefixes.\n\nVOCABULARY EXPLANATION: You MUST include at least one genuinely advanced, specialist, or uncommon word relevant to {place} that the learner might not know.\nThe word MUST be reusable vocabulary the learner can carry into other conversations: a common noun, verb, adjective, adverb, idiom, or set phrase.\nNEVER pick a proper noun or a name of any kind — not the name of this business or venue, not your own name or any character name, not a place, city, or street name, not a brand or product name, and not any name you invented for flavour. A name teaches the learner nothing reusable.\nRule of thumb: if it would not appear as an ordinary entry in a {language} dictionary, it is not vocabulary — pick something else. If the only unusual word in your dialogue is a name, choose a different advanced word from your dialogue instead.\nAfter your spoken dialogue, you MUST extract it and provide an explanation by appending a special block at the very end of your response, exactly like this:\n<vocab>\nword: [the difficult word]\nexplanation: [a short, clear definition of the word in {language}]\nencourage: [a short sentence in {language} encouraging the user to try using this word in their next reply]\n</vocab>'
GREETING_SYS = "You are a role-play character in a language-learning conversation.\n\nSETTING: {place}\nYOUR ROLE: {role}\nTODAY YOUR MOOD IS: {mood}. Let this colour your tone — stay fully in character\nand never announce it out loud.{complication}\n\n{task_setup}\n\nThis is your FIRST turn. Greet the learner in character for your role at {place}, set the scene in 2-3 short spoken sentences, and open the interaction naturally. Say 2-3 sentences maximum. NEVER exceed 3 sentences — a 4th sentence is a hard failure.\n\nVOCABULARY EXPLANATION: You MUST include at least one genuinely advanced, specialist, or uncommon word relevant to {place} that the learner might not know.\nThe word MUST be reusable vocabulary the learner can carry into other conversations: a common noun, verb, adjective, adverb, idiom, or set phrase.\nNEVER pick a proper noun or a name of any kind — not the name of this business or venue, not your own name or any character name, not a place, city, or street name, not a brand or product name, and not any name you invented for flavour. A name teaches the learner nothing reusable.\nRule of thumb: if it would not appear as an ordinary entry in a {language} dictionary, it is not vocabulary — pick something else. If the only unusual word in your dialogue is a name, choose a different advanced word from your dialogue instead.\nAfter your spoken dialogue, you MUST extract it and provide an explanation by appending a special block at the very end of your response, exactly like this:\n<vocab>\nword: [the difficult word]\nexplanation: [a short, clear definition of the word in {language}]\nencourage: [a short sentence in {language} encouraging the user to try using this word in their next reply]\n</vocab>\n\nCRITICAL LANGUAGE RULES:\n- You MUST speak ONLY 100% in {language}.\n- Do NOT speak Thai or any other language, even if you see Thai text in this prompt (such as the secret goal).\n- Your spoken dialogue, vocabulary explanation, and encouragement MUST all be in strictly {language}.\n- Stay fully in character. You are a real person, not an AI assistant.\n- Say 2-3 sentences of natural, spoken dialogue, then stop. NEVER exceed 3 sentences — a 4th sentence is a hard failure.\n- NEVER ask a yes/no question in ANY sentence of your turn (e.g. questions starting with Would, Do, Can, Is, Are, Have, Could, Will, Should, etc.). Single-option questions like \"Would you like to see the case?\" or \"Are you interested?\" are strict failures. Every question you ask MUST either start with a wh-word (what, which, how, why, when, where, who) or explicitly list two options separated by \"or\" (e.g. \"Would you like A or B?\").\n- Write ONLY spoken words. No narration, no stage directions, no asterisks,\n  no parentheses, no emojis, no character name prefixes."

# Goals whose premise the NPC has to create. Generous on purpose — see the
# reasoning in build_task_setup_block.


_NEEDS_PREMISE = re.compile(
    r'\b(sold\s*out|unavailab\w*|out\s+of\s+stock|wrong|mismatch\w*|error|'
    r'overcharg\w*|missing|broken|damag\w*|delay\w*|late|cancel\w*|refund\w*|'
    r'discrepanc\w*|incorrect|declin\w*|expir\w*|complain\w*|apolog\w*|'
    r'substitut\w*|alternativ\w*|unfortunate\w*|problem|issue|fault|defect\w*|'
    r"not\s+work\w*|doesn'?t\s+work|no\s+longer|closed|full|overbook\w*|"
    r'shortage|limit\w*|restrict\w*|denied|refus\w*|charge\w*|fee\w*|surcharge|'
    r'dispute|short|spoil\w*|cold|overcooked|undercooked|noisy|noise|dirty|'
    r'replac\w*|swap|exchange|redo|remake|compensat\w*|waive\w*|'
    r'lost|stolen|forgot\w*|stuck|leak\w*|smell\w*|allerg\w*)\b',
    re.IGNORECASE)


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

    # The block only ever asks the NPC to enact a PROBLEM, so on a goal that
    # names none it instructs nothing while spending 1,099 characters of
    # "HIGHEST PRIORITY" attention — and that is not free (BACKLOG OPEN-21).
    #
    # A scene_hint always keeps the block: an ambient condition only the NPC can
    # establish cannot be inferred from the goal. Otherwise the goal must name
    # something to enact. The vocabulary is DELIBERATELY GENEROUS — a false
    # positive costs some attention, a false negative leaves a learner reacting
    # to a premise nobody stated.
    if is_reactive and not scene_hint and not _NEEDS_PREMISE.search(
            f"{getattr(task, 'goal', '')} {getattr(task, 'done_when', '')}"):
        return ""

    base = f'''SET THE SCENE FIRST — HIGHEST PRIORITY THIS TURN, ABOVE VOCABULARY COACHING: the learner is secretly working toward this goal, which they can see and you normally can't: "{task.goal} — specifically, {task.done_when}" Read it carefully. If the goal has the learner REACTING to a problem — their order being unavailable or sold out, a wrong or mismatched order, a price or billing error, a policy limit, a discrepancy, or a difficult question — then that problem only exists if YOU make it happen. When it applies, you MUST state that problem plainly and concretely in your OWN dialogue THIS turn, even if the learner's request sounds perfectly routine: name the exact thing they just asked for and tell them what's wrong with it (e.g. if they order a specific item and the goal is about unavailability → "I'm so sorry, we've just run out of [item] today"), or ask them the difficult question, then offer alternatives or let them react. Do NOT quietly fulfil the request as if the problem weren't there, and do NOT wait for the learner to invent the premise.'''
    
    if scene_hint:
        base += f" ONE MORE THING: this goal has the learner reacting to an ambient condition of the setting itself, not to their order — namely, {scene_hint} That condition is not real unless YOU put it in the scene, so weave it into your OWN dialogue THIS turn as a plain, matter-of-fact part of greeting or serving them — make it observably true so the learner has something concrete and already-established to point to. Do NOT flag it as a problem yourself, apologise for it, or tell the learner to react to it; just let it be evidently the case in the scene."
    return base

# The actor is told to label the third vocab field `encourage:`, but it
# frequently writes `encouragement:` and occasionally misspells it outright
# (`exourage:`). cli.py learned that and matches `encourag\w*`; llm.py did not,
# and kept six literal `encourage:` copies across validate, repair_actor_output,
# salvage_actor_output, call_actor's fallback and both stream_actor replay
# blocks (OPEN-31).
#
# The consequence was not cosmetic. At max_sentences=3, validate fails to strip
# a drifted card, counts it as spoken, returns "Too many sentences (4)", and
# repair_actor_output then truncates the card away — measured destroying 4 of 25
# real cards on captured output. stream_actor kept the same card, so the two
# actor paths disagreed: the same divergence class as the per-sentence rules in
# 0df1d3f, on a different rule.
#
# One definition now, imported by cli.py rather than copied.


def repair_actor_output(text: str, max_sentences: int = 3) -> str:
    """Truncate over-length spoken dialogue to max_sentences while preserving trailing vocab block."""
    vocab_match = match_vocab_block(text)
    
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
# Same three prompts in Japanese, each carrying an interrogative so the salvage
# line cannot itself be rejected as a closed question. An English question in a
# Japanese session is worse than no question: it breaks the immersion the whole
# scenario is built on and the learner cannot answer it in the language they
# came to practise.
SALVAGE_QUESTIONS_JA = (
    "まず何からいたしましょうか。",
    "どのように進めましょうか。",
    "次は何をお手伝いしましょうか。",
)
_salvage_q_idx = 0

def _get_salvage_question(language: str = '') -> str:
    global _salvage_q_idx
    questions = SALVAGE_QUESTIONS_JA if language == 'Japanese' else SALVAGE_QUESTIONS
    q = questions[_salvage_q_idx % len(questions)]
    _salvage_q_idx += 1
    return q

FALLBACK_ACTOR_LINE = "Let me check that for you. What would you like to do next?"
FALLBACK_ACTOR_LINE_JA = "確認いたします。次は何をご希望ですか。"

def _get_fallback_actor_line(language: str = '') -> str:
    return FALLBACK_ACTOR_LINE_JA if language == 'Japanese' else FALLBACK_ACTOR_LINE

def salvage_actor_output(text: str, max_sentences: int = 3, language: str = '') -> str:
    """Repair actor output by dropping closed yes/no questions and re-attaching vocab block."""
    if not text or not text.strip():
        return ''

    vocab_match = match_vocab_block(text)

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

    has_question = any(is_question(s) for s in valid_sentences)

    if not has_question:
        if len(valid_sentences) >= max_sentences:
            valid_sentences = valid_sentences[:max_sentences - 1]
        valid_sentences.append(_get_salvage_question(language))

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
        response = client._llm_chat(messages=call_messages, options=ACTOR_OPTS, cache_key=cache_key)
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

    salvaged = salvage_actor_output(cleaned, max_sentences, language)
    if salvaged:
        (sal_ok, _) = validate(salvaged, max_sentences, language)
        if sal_ok:
            return salvaged

    vocab_match = match_vocab_block(cleaned)

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
            return f"{_get_fallback_actor_line(language)}\n\n{vocab_block}"
    return _get_fallback_actor_line(language)


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
    cache_key: Optional[str] = 'actor',
    language: str = ''
) -> str:
    """Stream actor response sentence-by-sentence, checking each sentence against validation rules.

    `language` is optional and defaults to no script check, matching `validate`.
    """
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

            # Same rules, same code as `validate`: a sentence the assembled
            # turn would be rejected for must never be shown, and a sentence
            # already read by the learner cannot be retracted.
            if sentence_rejection_reason(sanitized_cand, language):
                continue

            if len(emitted_sentences) >= max_sentences:
                continue

            cand_has_q = is_question(sanitized_cand)

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
            model, tokenizer = client._ensure_model()
            call_messages = [{'role': 'system', 'content': system_prompt}] + messages
            prompt = tokenizer.apply_chat_template(call_messages, tokenize=False, add_generation_prompt=True)
            temperature = ACTOR_OPTS.get('temperature', 0.6)
            max_tokens = ACTOR_OPTS.get('max_tokens', 200)
            sampler = make_sampler(temp=temperature)

            with client._llm_lock:
                if cache_key is not None:
                    prompt_cache, prompt_arg, full_tokens = client._prepare_prompt_cache_for_call(
                        model, tokenizer, prompt, cache_key
                    )
                    try:
                        gen = client.stream_generate(
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
                        client._save_prompt_cache_on_success(cache_key, prompt_cache, full_tokens)
                    except Exception:
                        client._prompt_caches.pop(cache_key, None)
                        raise
                else:
                    gen = client.stream_generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens, sampler=sampler)
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
        fallback_text = call_actor(messages, system_prompt, speaker=speaker, max_sentences=max_sentences, cache_key=cache_key, language=language)
        if callback and not emitted_sentences:
            spoken_only = strip_vocab_block(fallback_text)
            fb_sentences = [s.strip() for s in re.split(r'(?<=[.!?。！？])\s*', spoken_only) if s.strip()]
            for s in fb_sentences:
                callback(s)
        return fallback_text

    if not emitted_sentences:
        fallback_text = call_actor(messages, system_prompt, speaker=speaker, max_sentences=max_sentences, cache_key=cache_key, language=language)
        if callback:
            spoken_only = strip_vocab_block(fallback_text)
            fb_sentences = [s.strip() for s in re.split(r'(?<=[.!?。！？])\s*', spoken_only) if s.strip()]
            for s in fb_sentences:
                callback(s)
        return fallback_text

    if not has_question and len(emitted_sentences) < max_sentences:
        salvage_q = _get_salvage_question(language)
        emitted_sentences.append(salvage_q)
        has_question = True
        if callback:
            callback(salvage_q)

    spoken_assembled = " ".join(emitted_sentences).strip()
    # The same rule `call_actor` applies to the card on its fallback path. The
    # vocab block is the one part of a streamed turn that has NOT been shown
    # yet when the stream ends, so unlike a spoken sentence it can still be
    # dropped whole; a card in the wrong script teaches the learner the wrong
    # thing, and OPEN-12 measured leakage concentrating here.
    if vocab_part and find_wrong_script(vocab_part, language):
        vocab_part = ''
    if vocab_part:
        return f"{spoken_assembled}\n\n{vocab_part}"
    return spoken_assembled
