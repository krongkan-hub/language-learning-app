import ollama
import httpx
import os
import re
import random
import sys
import time
from scenarios import SCENARIOS

BASE_MODEL = 'qwen3:8b'

# Retry/validation diagnostics are developer noise, not part of the learner's
# conversation — keep them off the transcript unless explicitly requested.
DEBUG = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')

# Connect fast (fail fast if Ollama isn't running); allow generous read time
# for local model generation, but still bound it so the CLI can't hang forever.
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 60.0
_client = ollama.Client(
    timeout=httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT)
)

# The ollama client re-raises httpx.ConnectError as a builtin ConnectionError,
# but lets httpx timeout errors through unchanged — both must be caught.
OLLAMA_ERRORS = (ConnectionError, httpx.TimeoutException, ollama.ResponseError)


def describe_ollama_error(e: Exception) -> str:
    """Turn a connection/timeout/API exception into a learner-facing hint."""
    if isinstance(e, httpx.TimeoutException):
        return f"Ollama took longer than {READ_TIMEOUT:.0f}s to respond."
    if isinstance(e, ConnectionError):
        return "Can't connect to Ollama. Is 'ollama serve' running?"
    return str(e)

ACTOR_OPTS = {'temperature': 0.6, 'num_ctx': 8192, 'num_predict': 200}
COACH_OPTS = {'temperature': 0.2, 'num_ctx': 4096, 'num_predict': 250}
JUDGE_OPTS = {'temperature': 0.0, 'num_ctx': 4096, 'num_predict': 64}

CLOSED_OPENERS = {'do','does','did','is','are','was','were','can','could',
                  'will','would','should','have','has','want','need','may','am'}
WH_WORDS = {'what','why','how','which','where','when','who'}

MAX_TASK_ATTEMPTS = 4

# One mood is picked per playthrough (see main()) and injected into the actor
# prompt so replaying the same scenario doesn't reuse the same NPC tone every
# time. Purely a flavour lever — the task judge never sees this.
NPC_MOODS = [
    "harried and rushing, keen to keep things moving",
    "chatty and friendly, happy to chat while you work",
    "curt and impatient, giving clipped answers",
    "skeptical and questioning, wanting things spelled out",
    "cheerful but scatterbrained, easily sidetracked",
    "calm and unhurried, taking your time with the customer",
]

ACTOR_SYS = """\
{task_setup}

STOP AND THINK FIRST: does a {role} at {place} actually sell or provide
what the customer just asked for? A pharmacy does not serve coffee or food.
A hotel front desk does not serve coffee or food. A coffee shop does not fill
prescriptions. If the request does not belong here, you MUST refuse it in
character and redirect — you are NOT allowed to just go along with it anyway.

VOCABULARY — RARE, NEVER A REFLEX: your default is to explain NOTHING. The
learner is a fluent adult; glossing ordinary words ("Paris", "muffin", "have
a great day") is insulting and breaks immersion, so never do it. ONLY when a
genuinely specialist or uncommon term for {place} happens to come up on its
own — something a fluent non-specialist might not know (e.g. "single-origin",
"over-the-counter", "amenities") — you MAY, occasionally, gloss it in passing
with a short "which means ..." or "that means ..." definition in {language}.
Hard limits: at most one glossed word per turn, never on two turns in a row,
and if no genuinely specialist term arises naturally, gloss nothing at all —
silence is correct and expected. Do NOT hunt for a word to explain, and do
NOT bolt a definition onto everyday vocabulary just to have one.

You are a role-play character in a language-learning conversation.

SETTING: {place}
YOUR ROLE: {role}
TODAY YOUR MOOD IS: {mood}. Let this colour your tone, pacing, and how much you
push back — stay fully in character and never announce it out loud.{complication}

Rules:
- Stay fully in character. You are a real person, not an AI assistant.
- Respond ONLY in {language}.
- The learner is advanced (CEFR C1). Speak to them as you would to any fluent
  adult native speaker — do not simplify, hedge, or slow down for them.
- Say 2-3 sentences of natural, spoken dialogue, then stop.
- Remember: this is role-play, not a real situation the learner already has
  an opinion about. They may not know what to say next, and they may be
  thinking in Thai and searching for the English/Japanese words. YOU lead the
  conversation, not them — never leave them facing a blank, open question
  with nothing to react to.
- End every turn with something concrete the learner can grab onto: name 2-3
  specific options for them to choose between or react to (using words they
  can borrow straight from your sentence), or ask them to compare two things
  you just mentioned. Do NOT end with a vague open prompt like "tell me
  more," "explain," or "what do you think" with nothing concrete attached —
  give them the raw material to answer with. NEVER ask a yes/no question.
- Include at least one C1-level structure in every turn: an idiom, a nuanced
  collocation, a conditional, a passive construction, or a cleft sentence
  ("What really matters is..."). Do not simplify your language for the
  learner.
- Write ONLY spoken words. No narration, no stage directions, no asterisks,
  no parentheses, no emojis, no character name prefixes.
- For requests that ARE plausible for {role} at {place}, don't just comply
  instantly every single time. Sometimes (not always — vary it) introduce a
  small, realistic complication a real {role} might actually face: something
  is out of stock, a policy limits what you can do, there's a price
  difference, or a scheduling conflict. Make the learner negotiate, ask a
  follow-up, or propose an alternative before you resolve it.
- BUT do not stack obstacles on the SAME request: once the learner has clearly
  negotiated or committed to a specific alternative in response to an
  unavailability, shortage, or problem you raised — i.e. they've acknowledged
  it and picked a substitute, with or without a reason — ACCEPT their choice
  and move the conversation forward. Do NOT then reveal that their chosen
  alternative is ALSO unavailable, and do NOT introduce a second obstacle onto
  that same request. Resolve it; save any fresh complication for a different,
  later request.
- You may still disagree with their OPINIONS and defend your own. If they say
  the espresso tastes burnt, tell them why you rate it. Have taste, not just
  service.
- If their reply is short, hesitant, unclear, or seems stuck, do not just
  press them for more with no help. Be like a patient native speaker talking
  to a foreigner: offer your best guess at what they might mean, or suggest
  2-3 concrete things they might want, and let them react to your guess
  instead of inventing their own from nothing."""

GREETING_SYS = """\
You are a role-play character in a language-learning conversation.

SETTING: {place}
YOUR ROLE: {role}
TODAY YOUR MOOD IS: {mood}. Let this colour your tone — stay fully in character
and never announce it out loud.{complication}

{task_setup}

This is your FIRST turn. Greet the customer, name the place, and set the scene.
Say 2-4 short sentences of natural spoken dialogue, then end with an
open-ended question that requires more than a yes/no answer (e.g. ask what
they're looking for, or how you can help). NEVER ask a yes/no question.

Rules:
- Stay fully in character. You are a real person, not an AI assistant.
- Respond ONLY in {language}.
- Write ONLY spoken words. No narration, no stage directions, no asterisks,
  no parentheses, no emojis, no character name prefixes."""

COACH_SYS = """\
You are a language coach. The learner is practicing {language}.

Analyze ONLY the learner's most recent message. Everything you write — quotes,
corrections, suggestions, and reasons — must be in {language}, with the sole
exception of the two fixed section labels below, which stay in English.

YOUR STRONGEST BIAS IS TOWARD "Perfectly natural!". Most learner messages are
already correct. Your job is NOT to find something to fix in every message — it
is to catch genuine mistakes and otherwise get out of the way. A correction you
are not sure about does more harm than good.

Always begin with the Feedback section:

💡 Feedback:
- ❌ "[exact quote]" → ✅ "[correction]" (short reason in {language})

Rules for Feedback:
- This section is ONLY for a CLEAR, UNAMBIGUOUS error a teacher would mark
  wrong: broken grammar, a real spelling mistake, or a genuinely wrong word —
  a word a native speaker simply would not use for that meaning in that context
  (in Japanese, e.g. たくさん to mean "very much" should be とても).
- The following are NOT errors — never "correct" them: a correct sentence, a
  valid synonym or equally-natural phrasing (in Japanese, e.g. 何時 vs いつ are
  both fine — do not swap one for the other; ～から vs ～まで have DIFFERENT
  meanings, so never switch them), a different-but-also-natural politeness
  level, or a stylistic preference.
- Never change the MEANING of what the learner said. If your "correction" says
  something different from their sentence, it is wrong — discard it.
- When you are not certain something is a real error, treat the message as
  correct.
- If the grammar, spelling, and word choice are all fine, write EXACTLY this
  and nothing more (no Feedback bullets, no Level up):
  💡 Feedback: Perfectly natural!
- Maximum 2 corrections. Quote their exact words. Keep their pronouns. Every
  Feedback bullet MUST use the "❌ ... → ✅ ..." shape; if you would write
  "✅ ... → ✅ ...", the message was correct, so write "Perfectly natural!"
  instead.

EXAMPLES (copy this behaviour exactly):
Learner: "ブラックコーヒーをください。"
💡 Feedback: Perfectly natural!
Learner: "朝ごはんは何時からですか"
💡 Feedback: Perfectly natural!
Learner: "わたし、猫が好きだ、たくさん。"
💡 Feedback:
- ❌ "たくさん" → ✅ "とても" ("とても"が程度を表す自然な語です)
Learner: "I want to finding a book."
💡 Feedback:
- ❌ "I want to finding" → ✅ "I want to find" (after "to", use the base verb)

After Feedback you MAY add a Level up section — but ONLY when the message is
already correct AND you have a genuinely better, more natural phrasing a native
speaker would clearly prefer:

⬆️ Level up:
- "[their phrase]" → "[better phrase]" (short reason in {language})

Rules for Level up:
- OMIT this section entirely — write nothing at all after Feedback — when there
  is no real improvement to offer. Most correct messages need no Level up. Do
  NOT fill it in just to have something, and NEVER suggest replacing a phrase
  with the same phrase.
- The suggested phrase must be meaningfully different from and better than the
  learner's own.
- A phrase may appear in Feedback OR Level up, never in both.

Keep the labels "💡 Feedback:" and "⬆️ Level up:" exactly as written, in
English. If the learner used a non-{language} word, show the {language}
equivalent."""


def build_task_setup_block(task) -> str:
    """Task-awareness slot for the actor/greeting prompt.

    The actor is otherwise decoupled from the task judge, so an objective that
    presupposes a situation the NPC must create (an item out of stock, a wrong
    order, a billing error) would never get set up — the learner is left
    reacting to a premise nobody stated. This tells the actor to enact that
    premise in its OWN turn when the current goal needs it. The judge never
    sees this; it only shapes dialogue.
    """
    base = (
        f"SET THE SCENE FIRST — HIGHEST PRIORITY THIS TURN, ABOVE VOCABULARY "
        f"COACHING: the learner is secretly working toward this goal, which "
        f"they can see and you normally can't: \"{task.goal} — specifically, "
        f"{task.done_when}\" Read it carefully. If the goal has the learner "
        f"REACTING to a problem — their order being unavailable or sold out, a "
        f"wrong or mismatched order, a price or billing error, a policy limit, "
        f"a discrepancy — then that problem only exists if YOU make it happen. "
        f"When it applies, you MUST state that problem plainly and concretely "
        f"in your OWN dialogue THIS turn, even if the learner's request sounds "
        f"perfectly routine: name the exact thing they just asked for and tell "
        f"them what's wrong with it (e.g. they order a large caramel latte and "
        f"the goal is about unavailability → \"I'm so sorry, we've just run out "
        f"of large cups\" or \"we're out of caramel today\"), then offer "
        f"alternatives for them to react to. Do NOT quietly fulfil the request "
        f"as if the problem weren't there, and do NOT wait for the learner to "
        f"invent the premise. Only ignore all this when the goal is purely "
        f"something the learner initiates with no built-in problem (ordering, "
        f"asking a question, small talk) — then just respond normally and "
        f"don't manufacture an obstacle."
    )
    # Category (c): the goal is learner-initiated, but it's a complaint or
    # request about the SHARED ambient environment (noise/music, cleanliness,
    # temperature, lighting, crowding) that only makes sense if that condition
    # is already true in the scene. The actor isn't announcing a problem AT the
    # learner (that's the block above), but the learner has nothing to point to
    # unless the actor makes the ambient fact observably real first.
    scene_hint = getattr(task, "scene_hint", "")
    if scene_hint:
        base += (
            f" ONE MORE THING, AND IT OVERRIDES THE 'respond normally' NOTE "
            f"ABOVE FOR THIS DETAIL: this goal has the learner reacting to an "
            f"ambient condition of the setting itself, not to their order — "
            f"namely, {scene_hint} That condition is not real unless YOU put it "
            f"in the scene, so weave it into your OWN dialogue THIS turn as a "
            f"plain, matter-of-fact part of greeting or serving them — make it "
            f"observably true so the learner has something concrete and "
            f"already-established to point to. Do NOT flag it as a problem "
            f"yourself, apologise for it, or tell the learner to react to it; "
            f"just let it be evidently the case in the scene."
        )
    return base


# ---------------------------------------------------------------------------
# Sanitization & Validation
# ---------------------------------------------------------------------------

EMOJI_PATTERN = r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u27BF]'


def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> reasoning traces (qwen3) and any stray tags."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return re.sub(r'<[^>]+>', '', text)


def sanitize(text: str, speaker: str = None) -> str:
    """Strip reasoning traces, stage directions, character prefixes, and emoji.

    `speaker` should be the known character name (e.g. "Barista") so only
    that exact prefix is stripped \u2014 a generic \\w+: pattern would also eat
    the first clause of real dialogue that happens to start the same way
    (e.g. "Sure: here you go." -> "here you go.").
    """
    # 1. Remove <think>...</think> blocks (qwen3 reasoning traces)
    text = strip_think_tags(text)
    # 2. Remove markdown bold/italic wrapping actions: *(grins)*, **Barista:**
    text = re.sub(r'\*+[^*]*\*+', '', text)
    # 3. Remove parenthetical actions: (glancing up briefly)
    text = re.sub(r'\([^)]*\)', '', text)
    # 4. Remove leading character name prefix: "Barista: "
    if speaker:
        text = re.sub(rf'^\s*{re.escape(speaker)}\s*:\s*', '', text,
                      flags=re.MULTILINE | re.IGNORECASE)
    # 5. Remove emoji
    text = re.sub(EMOJI_PATTERN, '', text)
    # 6. Collapse whitespace and strip wrapping quotes
    text = re.sub(r'\s{2,}', ' ', text).strip()
    text = text.strip('"')
    return text


def validate(text: str, max_sentences: int = 3) -> tuple[bool, str]:
    """Check sanitized actor output against format rules."""
    if not text:
        return False, "Empty response"
    if re.search(r'[*\[\]<>]', text):
        return False, "Contains residual markup characters"
    if re.search(EMOJI_PATTERN, text):
        return False, "Contains emoji"
    # Split on both ASCII (. ! ?) and full-width Japanese (。！？) sentence
    # enders. Japanese has no space between sentences, so \s* (not \s+) is
    # required — otherwise a whole Japanese reply counts as a single
    # "sentence" and max_sentences never triggers.
    sentences = [s.strip() for s in re.split(r'(?<=[.!?。！？])\s*', text)
                if s.strip()]
    if len(sentences) > max_sentences:
        return False, f"Too many sentences ({len(sentences)})"
    last = sentences[-1] if sentences else ""
    if last.endswith('?'):
        # Closed-question detection is English-specific (word-level check on
        # ASCII openers/WH-words). Japanese has no word boundaries to key off
        # without real tokenization, so this intentionally does not attempt
        # to flag Japanese yes/no questions — it would rather under-enforce
        # than misfire (e.g. "何か" ("something") contains 何 ("what") as a
        # substring without being a WH-question).
        words = re.findall(r"[a-z']+", last.lower())
        if (words and words[0] in CLOSED_OPENERS
                and ' or ' not in last.lower()
                and not (WH_WORDS & set(words))):
            return False, "Closed yes/no question"
    return True, ""


# ---------------------------------------------------------------------------
# LLM Call Wrappers
# ---------------------------------------------------------------------------

TRANSLATE_OPTS = {'temperature': 0.0, 'num_ctx': 4096, 'num_predict': 1024}

def _llm_chat(messages: list, options: dict) -> dict:
    return _client.chat(model=BASE_MODEL, messages=messages, options=options,
                        think=False)


def translate_hints(tasks: list, language: str) -> dict:
    """Batch-translate task hints into the target language in one LLM call.

    Returns a dict mapping each task's hint to its translation. Falls back
    to the original English hint if the call fails or a line is missing.
    """
    # English targets don't need translation.
    if language.strip().lower() in ('english', 'en'):
        return {t.hint: t.hint for t in tasks}

    numbered = "\n".join(f"{i+1}. {t.hint}" for i, t in enumerate(tasks))
    prompt = (
        f"Translate each numbered instruction below into {language}. "
        f"Keep the numbering. Write ONLY the translations, one per line, "
        f"no commentary.\n\n{numbered}"
    )
    try:
        response = _llm_chat(
            messages=[{"role": "user", "content": prompt}],
            options=TRANSLATE_OPTS
        )
        raw = strip_think_tags(response['message']['content']).strip()
        lines = [l.strip() for l in raw.split('\n') if l.strip()]
        result = {}
        for i, task in enumerate(tasks):
            # Try to find the line starting with the right number
            prefix = f"{i+1}."
            translated = next(
                (l[len(prefix):].strip() for l in lines if l.startswith(prefix)),
                None
            )
            result[task.hint] = translated if translated else task.hint
        return result
    except Exception:
        return {t.hint: t.hint for t in tasks}

def call_actor(messages: list, system_prompt: str, speaker: str = None,
               max_sentences: int = 3) -> str:
    """Call the actor, sanitize and validate. Retry up to 2x on failure."""
    cleaned = ""
    reason = ""
    for attempt in range(3):
        call_messages = [{"role": "system", "content": system_prompt}] + messages
        if attempt > 0:
            call_messages.append({
                "role": "system",
                "content": f"Your previous response was rejected: {reason}. "
                           f"Reply with ONLY {max_sentences} short spoken "
                           "sentences or fewer. "
                           "No asterisks, no parentheses, no character names."
            })
        t0 = time.time()
        response = _llm_chat(messages=call_messages, options=ACTOR_OPTS)
        elapsed = time.time() - t0
        raw = response['message']['content']
        cleaned = sanitize(raw, speaker=speaker)
        ok, reason = validate(cleaned, max_sentences)
        if ok:
            if attempt > 0 and DEBUG:
                print(f"  [ok after {attempt + 1} attempts, {elapsed:.1f}s]")
            return cleaned
        if DEBUG:
            print(f"  [attempt {attempt + 1}/3 rejected: {reason} ({elapsed:.1f}s)]")
    if DEBUG:
        print("  [Warning: actor output failed validation after 3 attempts]")
    return cleaned


def _normalize_phrase(s: str) -> str:
    # Case is intentionally preserved: a capitalization-only fix (e.g.
    # "hello" -> "Hello") is a real, teachable correction for a language
    # learner and must not collapse into a no-op alongside it.
    s = s.strip()
    s = re.sub(r'[.!?]+$', '', s).strip()
    s = re.sub(r'\s+', ' ', s)
    return s


def _normalize_quotes(text: str) -> str:
    text = text.replace('->', '→').replace('=>', '→')
    text = text.replace('“', '"').replace('”', '"')
    # Some languages (e.g. Japanese) quote with corner/guillemet brackets
    # instead of straight double quotes even when asked for exact format.
    for open_q, close_q in [('「', '」'), ('『', '』'), ('«', '»'), ('„', '"')]:
        text = text.replace(open_q, '"').replace(close_q, '"')
    return text


def _clean_level_up_block(block: str) -> str:
    """Drop no-op / scaffold Level up bullets; omit the section if nothing real
    survives.

    The model is prone to filling the Level up slot even when there's nothing to
    upgrade — suggesting a phrase be replaced with itself, or leaking the raw
    prompt scaffold ("[their phrase]", a bare "(why)"). None of that should ever
    reach the learner.
    """
    block = _normalize_quotes(block)
    lines = block.split('\n')
    header, body = lines[0], lines[1:]
    kept = []
    for line in body:
        s = line.strip()
        if not s:
            continue
        # Unfilled template placeholders like [their phrase] — pure scaffold.
        if re.search(r'\[[^\]]*\]', s):
            continue
        # A bare "(why)"/"(reason)" tag is leaked scaffold, not a real reason.
        cleaned = re.sub(r'\s*\((?:why|reason)\)\s*$', '', line.rstrip(),
                         flags=re.IGNORECASE)
        quotes = re.findall(r'"([^"]*)"', cleaned)
        # Replacing a phrase with itself is a no-op suggestion — drop it.
        if len(quotes) >= 2 and _normalize_phrase(quotes[0]) == _normalize_phrase(quotes[1]):
            continue
        kept.append(cleaned)
    if not kept:
        return ""
    return "\n".join([header.strip()] + kept).strip()


def _tidy_whitespace(text: str) -> str:
    """Strip trailing spaces and collapse stray runs after the Feedback label."""
    lines = [re.sub(r'[ \t]+$', '', ln) for ln in text.split('\n')]
    text = '\n'.join(lines)
    text = re.sub(r'💡 Feedback:[ \t]+', '💡 Feedback: ', text)
    return text.strip()


def filter_coach_output(raw: str) -> str:
    """Split, normalise, parse, drop no-ops, dedupe, stitch. No I/O."""
    level_up_header_patterns = [
        r'⬆️\s*Level up:',
        r'⬆️ Level up:',
        r'Level up:',
    ]

    feedback_block = raw
    level_up_block = ""

    for pattern in level_up_header_patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            idx = match.start()
            feedback_block = raw[:idx].strip()
            level_up_block = raw[idx:].strip()
            break

    feedback_block = _normalize_quotes(feedback_block)

    lines = feedback_block.split('\n')
    corrections = []
    kept_lines = []

    for line in lines:
        match = re.search(r'❌\s*"(.*?)"\s*→\s*✅\s*"(.*?)"', line)
        if match:
            said_norm = _normalize_phrase(match.group(1))
            better_norm = _normalize_phrase(match.group(2))
            if said_norm == better_norm:
                continue  # no-op "correction"
            if any(c == said_norm for c in corrections):
                continue  # duplicate
            corrections.append(said_norm)
            kept_lines.append(line)
        elif '→' in line or re.search(r'✅\s*"', line):
            # A correction-shaped bullet that ISN'T a clean ❌ ... → ✅ ... — most
            # often the model's "✅ ... → ✅ ..." on input it actually judged
            # correct. It's noise, not a real fix; drop it rather than leak it.
            continue
        else:
            kept_lines.append(line)  # header, prose, "Perfectly natural!"

    if corrections:
        final_feedback = "\n".join(kept_lines).strip()
    else:
        remaining = "\n".join(kept_lines)
        body = re.sub(r'💡\s*Feedback:?', '', remaining).strip()
        if not body or 'perfectly natural' in remaining.lower():
            final_feedback = "💡 Feedback: Perfectly natural!"
        else:
            final_feedback = remaining.strip()

    if level_up_block:
        level_up_block = _clean_level_up_block(level_up_block)
    if level_up_block:
        return _tidy_whitespace(f"{final_feedback}\n\n{level_up_block}")
    return _tidy_whitespace(final_feedback)

def call_coach(user_input: str, language: str) -> str:
    """Get language feedback on the learner's message."""
    system = COACH_SYS.format(language=language)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_input},
    ]
    response = _llm_chat(messages=messages, options=COACH_OPTS)
    raw = response['message']['content']
    raw = strip_think_tags(raw).strip()
    return filter_coach_output(raw)


# ---------------------------------------------------------------------------
# Task Evaluation (hybrid: deterministic + LLM)
# ---------------------------------------------------------------------------

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
    match = re.search(r"Learner used the word '(\w+)'", done_when)
    if match:
        word = match.group(1)
        if re.search(rf'\b{re.escape(word)}\b', user_input, re.IGNORECASE):
            return True, None
        return False, f"You haven't used the word '{word}' yet."
    return None


def judge_llm(conversation: list, done_when: str, language: str = "English") -> tuple:
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
    # Trim any trailing NPC turn: at judge time the conversation ends with the
    # actor's reply to the learner, and that reply routinely tacks on a NEW
    # follow-up offer/question ("we're out of oat milk, want a regular latte
    # instead?"). Left in context it contaminates the verdict — the judge starts
    # requiring the learner to have answered it. The goal only ever concerns the
    # learner's own message, so cut everything after their last turn; the PRIOR
    # actor turn (which may have established a premise the goal reacts to) stays.
    last_user_idx = next(
        (i for i in range(len(conversation) - 1, -1, -1)
         if conversation[i]['role'] == 'user'),
        len(conversation) - 1
    )
    context = conversation[:last_user_idx + 1][-4:]
    context_str = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in context
    )
    learner_msg = next(
        (m['content'] for m in reversed(context) if m['role'] == 'user'), ""
    )
    prompt = (
        f"Conversation so far (background context only):\n{context_str}\n\n"
        f"The LEARNER's most recent message was:\n\"{learner_msg}\"\n\n"
        f"GOAL: {done_when}\n\n"
        f"Decide whether the LEARNER's OWN words satisfy this goal. Rules:\n"
        f"- Judge ONLY what the learner said. The goal describes the learner's "
        f"contribution, never the NPC's.\n"
        f"- Judge by MEANING, not keywords. A message that merely mentions a "
        f"related topic, or happens to share a word with the goal, does NOT "
        f"count — the learner must actually DO what the goal describes. (E.g. "
        f"idly comparing two products does not satisfy 'point out a discrepancy "
        f"on the label and ask for clarification'.)\n"
        f"- The learner need not use the goal's exact words; a clear paraphrase "
        f"or equivalent expression counts (e.g. 'somewhere quiet' satisfies "
        f"'asked for a quiet room', and asking 'how much should I take each "
        f"time' satisfies a goal about dosage even without the word 'dose').\n"
        f"- The NPC's turns may raise new questions, offers, or options. Do NOT "
        f"require the learner to have addressed any of those — they are NOT part "
        f"of the goal unless the goal text literally names them.\n"
        f"- If the goal has multiple clauses joined by AND, EVERY clause must be "
        f"clearly met by the learner's words; if any one is missing, answer NO. "
        f"Ignore anything the goal does not mention.\n"
        f"- Be strict about the SUBSTANCE (is it on-topic, are all clauses "
        f"present?) but generous about WORDING: a clear paraphrase, synonym, or "
        f"equivalent phrasing fully counts (e.g. 'how often each day' satisfies "
        f"'how many times a day'). Reject off-topic or partial answers, not "
        f"answers that merely use different words than the goal.\n"
        f"If the learner's own words already meet the goal, answer YES.\n"
        f"Otherwise answer 'NO: <one short sentence, written in {language}, "
        f"naming the specific part of the goal the learner has not yet "
        f"expressed>'. /no_think"
    )
    response = _llm_chat(
        messages=[{"role": "user", "content": prompt}],
        options=JUDGE_OPTS
    )
    text = response['message']['content'].strip()
    text = strip_think_tags(text).strip()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    verdict = next(
        (l for l in lines if l.upper().startswith(('YES', 'NO'))),
        lines[-1] if lines else ''
    )
    if verdict.upper().startswith('YES'):
        return True, None
    reason = re.sub(r'^\s*NO\b[\s:.,\-]*', '', verdict, flags=re.IGNORECASE)
    return False, (reason.strip() or None)


def evaluate_task(user_input: str, done_when: str, conversation: list,
                  language: str) -> tuple:
    """Evaluate task: deterministic first, LLM fallback.

    Returns (done, hint) — hint explains what's missing on a miss, else None.
    """
    result = judge_deterministic(user_input, done_when, language)
    if result is not None:
        return result
    return judge_llm(conversation, done_when, language)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def select_scenario():
    valid_scenarios = [s for s in SCENARIOS if len(s.tasks) > 0]
    if not valid_scenarios:
        print("Error: No scenarios with tasks found!")
        sys.exit(1)

    random_scenario = random.choice(valid_scenarios)
    print(f"\nRandomly selected scenario: {random_scenario.name}")

    choice = input("Do you want to play this scenario? (y/n): ").strip().lower()
    if choice == 'y' or choice == '':
        return random_scenario

    print("\nAvailable Scenarios:")
    for i, s in enumerate(valid_scenarios):
        print(f"{i + 1}. {s.name} ({len(s.tasks)} tasks available)")

    while True:
        try:
            sel = input("\nEnter the number of the scenario you want "
                       "(or 'quit'): ").strip()
            if sel.lower() in ('quit', 'exit'):
                print("Exiting...")
                sys.exit(0)
            idx = int(sel) - 1
            if 0 <= idx < len(valid_scenarios):
                return valid_scenarios[idx]
            else:
                print("Invalid number. Try again.")
        except ValueError:
            print("Please enter a valid number.")


def main():
    print("========================================")
    print("   Language Conversation Coach CLI")
    print("========================================")

    try:
        _client.show(BASE_MODEL)
    except ollama.ResponseError as e:
        if e.status_code == 404:
            print(f"Error: Model '{BASE_MODEL}' not found.")
            print(f"Please run: ollama pull {BASE_MODEL}")
        else:
            print(f"Ollama error: {e}")
        sys.exit(1)
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        print(f"Error: {describe_ollama_error(e)}")
        sys.exit(1)

    language = input(
        "Which language do you want to practice? (e.g., English, Japanese): "
    ).strip()
    if not language:
        language = "English"

    scenario = select_scenario()
    tasks = scenario.get_session_tasks(num_tasks=10)
    speaker = scenario.speaker

    # Translate task hints to the target language in one batch call.
    print("[Preparing session...]")
    hint_translations = translate_hints(tasks, language)

    # Session-level flavour, fixed for this whole playthrough: one random NPC
    # mood, plus one random complication if the scenario defines any. These
    # only shape the actor prompt — the task judge never sees them.
    mood = random.choice(NPC_MOODS)
    complication = (random.choice(scenario.complications)
                    if scenario.complications else None)
    # The mid-conversation actor turns and the opening greeting need DIFFERENT
    # complication instructions: by the greeting the learner has said nothing,
    # so the actor must not pre-claim a request that hasn't happened; mid-
    # conversation, the risk is instead re-raising an already-established
    # obstacle on unrelated turns. Hence two separate blocks.
    actor_complication_block = (
        f"\nTODAY'S COMPLICATION (applies to this whole conversation, FIRM): "
        f"{complication}. The FIRST time the learner asks for something this "
        f"obstacle actually affects, you MUST raise it before agreeing and make "
        f"them adapt or choose an alternative — do not quietly fulfil that "
        f"request as if the obstacle weren't there. But this complication is to "
        f"be ESTABLISHED ONCE and then re-mentioned ONLY when the learner's "
        f"CURRENT message is actually about the affected item. Look at the "
        f"conversation so far: if you (or your greeting) have already "
        f"established it, do NOT state it again — not verbatim, not reworded, "
        f"not even in passing — UNLESS the learner's latest message is directly "
        f"about the thing it affects. If the learner just asked for something "
        f"unrelated (napkins, the wifi password, a receipt, directions) while "
        f"the complication is about, say, oat milk, then say NOTHING about the "
        f"complication — just handle exactly what they asked. Above all, "
        f"actually RESPOND to what the learner just said: acknowledge their "
        f"specific point first (if they say they already have a booking, "
        f"confirm you see it) and build on it, rather than ignoring it to "
        f"repeat this complication. Beyond this and whatever the learner's "
        f"current goal calls for, do not pile on extra unrelated obstacles."
        if complication else ""
    )
    greeting_complication_block = (
        f"\nTODAY'S COMPLICATION (background for the whole conversation): "
        f"{complication}. IMPORTANT: this is your FIRST line and the customer "
        f"has NOT said anything yet. You must NOT claim they already asked for, "
        f"wanted, or complained about any specific item, and you must NOT say a "
        f"specific item is unavailable relative to a request they haven't made "
        f"— no request exists yet, so phrases like \"the X you were asking "
        f"about\" or \"the X you wanted\" are forbidden here. Let the "
        f"complication colour only the ambiance or your manner (you might seem "
        f"a little apologetic, harried, or frazzled). Save actually raising the "
        f"obstacle for later, once the learner asks for something it affects."
        if complication else ""
    )

    print(f"\nStarting Scenario: {scenario.name}")
    print(f"Place: {scenario.place}")
    print(f"Role of AI: {scenario.role}")
    print("========================================\n")

    # The actor prompt is rebuilt per task inside the loop so it always carries
    # the CURRENT task's setup instruction; the greeting carries the first
    # task's, since the opening line is the only actor turn before the learner
    # first speaks on task 1.
    greeting_system = GREETING_SYS.format(
        place=scenario.place, role=scenario.role, language=language,
        mood=mood, complication=greeting_complication_block,
        task_setup=build_task_setup_block(tasks[0])
    )

    # Initial greeting — the seed "Hello." triggers the actor but is NOT
    # persisted in the conversation history.  Only the greeting itself is kept.
    print(f"[{speaker} is getting ready...]")
    try:
        seed = [{"role": "user", "content": "Hello."}]
        greeting = call_actor(seed, greeting_system, speaker=speaker,
                             max_sentences=4)
    except OLLAMA_ERRORS as e:
        print(f"Failed to communicate with Ollama: {describe_ollama_error(e)}")
        sys.exit(1)

    messages = [{"role": "assistant", "content": greeting}]
    print(f"\n[{speaker}]: {greeting}")

    current_task_idx = 0
    total_tasks = len(tasks)
    attempts = 0
    # Index into `messages` where the CURRENT task's turns begin. The judge is
    # given only messages from here on, so a hint can never reference a previous
    # task's unresolved thread once we've advanced. Reset each time the active
    # task changes (below), capturing the length before the learner's first
    # turn on that task.
    prev_task_idx = -1
    task_start_idx = len(messages)

    while current_task_idx < total_tasks:
        if current_task_idx != prev_task_idx:
            task_start_idx = len(messages)
            prev_task_idx = current_task_idx
        current_task = tasks[current_task_idx]
        actor_system = ACTOR_SYS.format(
            place=scenario.place, role=scenario.role, language=language,
            mood=mood, complication=actor_complication_block,
            task_setup=build_task_setup_block(current_task)
        )
        print(f"\n--- Task {current_task_idx + 1}/{total_tasks} ---")
        translated_hint = hint_translations.get(current_task.hint, current_task.hint)
        print(f"🎯 Objective: {translated_hint} (type 'skip' to move on)")

        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            print("Exiting...")
            break
        if user_input.lower() == 'skip':
            print(f"\n⏭️  Skipped: {current_task.goal}")
            current_task_idx += 1
            attempts = 0
            continue
        if not user_input.strip():
            print("[You didn't type anything — say something to the "
                 f"{speaker.lower()}, or type 'skip'/'quit'.]")
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            # 1. Actor response (aware of the current task's setup, not grading)
            print(f"\n[{speaker} is thinking...]")
            actor_reply = call_actor(messages, actor_system, speaker=speaker)
            messages.append({"role": "assistant", "content": actor_reply})
            print(f"\n[{speaker}]: {actor_reply}")

            # 2. Coach feedback (separate call, never enters conversation history)
            coach_feedback = call_coach(user_input, language)
            print(f"\n{coach_feedback}")

            # 3. Task evaluation — only the current task's turns, so a hint
            # can't drift back to a previous task's thread.
            is_done, hint = evaluate_task(user_input, current_task.done_when,
                                          messages[task_start_idx:], language)
        except OLLAMA_ERRORS as e:
            print(f"\n[⚠️  {describe_ollama_error(e)}]")
            print("[Your last message wasn't processed — please try again.]")
            if messages and messages[-1]['content'] == user_input:
                messages.pop()  # drop the unanswered turn, retry cleanly
            continue
        if is_done:
            print(f"\n✅ TASK COMPLETED! Moving to next...")
            current_task_idx += 1
            attempts = 0
        else:
            attempts += 1
            if attempts >= MAX_TASK_ATTEMPTS:
                print(f"\n➡️  Moving on after {attempts} tries. "
                     f"Goal was: {current_task.goal}")
                current_task_idx += 1
                attempts = 0
            else:
                print(f"\n❌ Task not yet completed. Keep trying! "
                     f"({attempts}/{MAX_TASK_ATTEMPTS} attempts)")
                if hint:
                    print(f"💡 Hint: {hint}")

    if current_task_idx == total_tasks:
        print("\n========================================")
        print("🎉 CONGRATULATIONS! You completed all tasks! 🎉")
        print("========================================")


if __name__ == "__main__":
    main()
