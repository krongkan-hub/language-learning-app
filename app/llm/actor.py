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
from .guards import (SENTENCE_BREAK, split_sentences, validate, sentence_rejection_reason, invites_reply,
                     presupposes_a_request,
                     is_closed_question, find_wrong_script, sanitize,
                     open_service_questions)
from .vocab import (match_vocab_block, strip_vocab_block)
from .prompts import (FALLBACK_ACTOR_LINE, FALLBACK_ACTOR_LINE_JA,
                      GREETING_FALLBACK_LINE, GREETING_FALLBACK_LINE_JA,
                      SALVAGE_QUESTIONS, SALVAGE_QUESTIONS_JA)


ACTOR_OPTS = {'temperature': 0.6, 'max_tokens': 200}

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

    sentences = split_sentences(spoken_part)
    if len(sentences) <= max_sentences:
        return text
    
    truncated_spoken = " ".join(sentences[:max_sentences])
    if vocab_block:
        return f"{truncated_spoken}\n\n{vocab_block}"
    return truncated_spoken

_salvage_q_idx = 0

def _get_salvage_question(language: str = '') -> str:
    global _salvage_q_idx
    questions = SALVAGE_QUESTIONS_JA if language == 'Japanese' else SALVAGE_QUESTIONS
    q = questions[_salvage_q_idx % len(questions)]
    _salvage_q_idx += 1
    return q

def _get_fallback_actor_line(language: str = '') -> str:
    return FALLBACK_ACTOR_LINE_JA if language == 'Japanese' else FALLBACK_ACTOR_LINE

def open_up(closed_question: str, language: str = '') -> str:
    """A yes/no question turned into the A-or-B shape the rules accept.

    The model does ask — it asks yes/no ("Would you like to see the dessert
    menu?"), which the rules drop, and the turn then ended on a canned line
    ("What else can I do for you?") 9/40 English and 15/40 Japanese turns
    (OPEN-52). Offering "or something else" keeps the NPC's own question and
    still invites more than "Yes".
    """
    q = closed_question.rstrip().rstrip('?？。．.!！').rstrip()
    if language == 'Japanese':
        return q + '、それともほかに何かございますか？'
    return q + ', or something else?'


def _closing_question(dropped_closed: list, language: str) -> str:
    """The question a turn without one ends on: its own last yes/no question
    opened up, or a canned line when it asked none."""
    # English only. Measured in play, the Japanese opened-up questions read
    # worse than the canned lines (「何か特別な注文がありますか、それとも
    # ほかに何かございますか」 says "anything" twice; one began with 或いは).
    if dropped_closed and language != 'Japanese':
        candidate = open_up(dropped_closed[-1], language)
        if not sentence_rejection_reason(candidate, language):
            return candidate
    return _get_salvage_question(language)


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

    sentences = split_sentences(spoken_part)
    if not sentences:
        return ''

    valid_sentences = [s for s in sentences if not is_closed_question(s)]
    dropped_closed = [s for s in sentences if is_closed_question(s)]

    if len(valid_sentences) > max_sentences:
        valid_sentences = valid_sentences[:max_sentences]

    has_question = any(invites_reply(s) for s in valid_sentences)

    if not has_question:
        if len(valid_sentences) >= max_sentences:
            valid_sentences = valid_sentences[:max_sentences - 1]
        valid_sentences.append(_closing_question(dropped_closed, language))

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
        response = client._llm_chat(messages=call_messages, options={**ACTOR_OPTS, 'script': language},
                                    cache_key=cache_key)
        elapsed = time.time() - t0
        raw = response['message']['content']
        cleaned = open_service_questions(sanitize(raw, speaker=speaker), language)
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
    language: str = '',
    trace: Optional[list] = None,
) -> str:
    """Stream actor response sentence-by-sentence, checking each sentence against validation rules.

    `trace`, when given, collects one {'sentence', 'fate'} per candidate —
    shown, or why it was not — and {'salvage': line} if a canned question had
    to be appended (OPEN-52: which sentences a turn loses, and why).

    `language` is optional and defaults to no script check, matching `validate`.
    """
    emitted_sentences = []
    dropped_closed = []           # yes/no questions dropped for that reason alone
    has_question = False
    processed_sentence_count = 0
    raw_text = ""
    vocab_part = ""

    def process_spoken(spoken_chunk: str, is_final: bool = False):
        nonlocal processed_sentence_count, has_question
        parts = SENTENCE_BREAK.split(spoken_chunk)
        complete_parts = []
        for i, part in enumerate(parts):
            p_str = part.strip()
            if not p_str:
                continue
            # The last part is only finished at a Japanese stop. An ASCII one
            # may still be "$3." with the "50" on its way, and a sentence once
            # shown cannot be taken back; the next whitespace splits it.
            if i < len(parts) - 1 or is_final or re.search(r'[。！？]$', p_str):
                complete_parts.append(p_str)

        while processed_sentence_count < len(complete_parts):
            cand = complete_parts[processed_sentence_count]
            processed_sentence_count += 1

            sanitized_cand = open_service_questions(sanitize(cand, speaker=speaker), language)
            if not sanitized_cand:
                continue

            # Same rules, same code as `validate`: a sentence the assembled
            # turn would be rejected for must never be shown, and a sentence
            # already read by the learner cannot be retracted.
            reason = sentence_rejection_reason(sanitized_cand, language)
            if reason:
                if reason == 'Closed yes/no question':
                    dropped_closed.append(sanitized_cand)
                if trace is not None:
                    trace.append({'sentence': sanitized_cand, 'fate': reason})
                continue

            if len(emitted_sentences) >= max_sentences:
                if trace is not None:
                    trace.append({'sentence': sanitized_cand, 'fate': 'over the sentence limit'})
                continue

            cand_has_q = invites_reply(sanitized_cand)

            if len(emitted_sentences) == max_sentences - 1 and not has_question and not cand_has_q:
                if trace is not None:
                    trace.append({'sentence': sanitized_cand, 'fate': 'last slot kept for a question'})
                continue

            emitted_sentences.append(sanitized_cand)
            if trace is not None:
                trace.append({'sentence': sanitized_cand, 'fate': 'shown'})
            if cand_has_q:
                has_question = True

            if callback:
                callback(sanitized_cand)

    def _consume(gen):
        """Accumulate a streamed turn, emitting each finished sentence.

        One copy, called from all three branches below. It was written out
        three times — a supplied generator, a prompt-cached call, an uncached
        one — with identical bodies, which is two places to forget when the
        vocab boundary or the sentence rules change.
        """
        nonlocal raw_text
        for item in gen:
            chunk = item.text if hasattr(item, 'text') else str(item)
            raw_text += chunk
            v_idx = _find_vocab_start(raw_text)
            process_spoken(raw_text[:v_idx] if v_idx != -1 else raw_text,
                           is_final=False)

    try:
        if generator_fn is not None:
            _consume(generator_fn())
        else:
            from mlx_lm.sample_utils import make_sampler
            model, tokenizer = client._ensure_model()
            call_messages = [{'role': 'system', 'content': system_prompt}] + messages
            prompt = tokenizer.apply_chat_template(call_messages, tokenize=False, add_generation_prompt=True)
            temperature = ACTOR_OPTS.get('temperature', 0.6)
            max_tokens = ACTOR_OPTS.get('max_tokens', 200)
            sampler = make_sampler(temp=temperature)
            from .script_mask import script_processor
            mask = script_processor(tokenizer, language)
            extra = {'logits_processors': [mask]} if mask else {}

            with client._llm_lock:
                if cache_key is not None:
                    prompt_cache, prompt_arg, full_tokens = client._prepare_prompt_cache_for_call(
                        model, tokenizer, prompt, cache_key
                    )
                    try:
                        _consume(client.stream_generate(
                            model, tokenizer, prompt=prompt_arg, max_tokens=max_tokens,
                            sampler=sampler, prompt_cache=prompt_cache, **extra
                        ))
                        client._save_prompt_cache_on_success(cache_key, prompt_cache, full_tokens)
                    except Exception:
                        client._prompt_caches.pop(cache_key, None)
                        raise
                else:
                    _consume(client.stream_generate(
                        model, tokenizer, prompt=prompt, max_tokens=max_tokens,
                        sampler=sampler, **extra
                    ))

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
            fb_sentences = split_sentences(spoken_only)
            for s in fb_sentences:
                callback(s)
        return fallback_text

    if not emitted_sentences:
        fallback_text = call_actor(messages, system_prompt, speaker=speaker, max_sentences=max_sentences, cache_key=cache_key, language=language)
        if callback:
            spoken_only = strip_vocab_block(fallback_text)
            fb_sentences = split_sentences(spoken_only)
            for s in fb_sentences:
                callback(s)
        return fallback_text

    if not has_question and len(emitted_sentences) < max_sentences:
        salvage_q = _closing_question(dropped_closed, language)
        if trace is not None:
            trace.append({'opened_up' if dropped_closed and salvage_q not in SALVAGE_QUESTIONS + SALVAGE_QUESTIONS_JA
                          else 'salvage': salvage_q})
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


def drop_presupposing_greeting(text: str, language: str = '') -> str:
    """The NPC's first turn without the sentences that answer a request
    nobody made — 確認いたします, "coming right up" (OPEN-41). If nothing is
    left, the canned greeting stands in. The vocabulary card is kept."""
    vocab_match = match_vocab_block(text)
    vocab = vocab_match.group(0).strip() if vocab_match else ''
    spoken = strip_vocab_block(text)
    kept = [s for s in split_sentences(spoken) if not presupposes_a_request(s, language)]
    if len(kept) == len(split_sentences(spoken)):
        return text
    if not kept:
        kept = [GREETING_FALLBACK_LINE_JA if language == 'Japanese' else GREETING_FALLBACK_LINE]
    joiner = '' if language == 'Japanese' else ' '
    return joiner.join(kept) + (f'\n\n{vocab}' if vocab else '')
