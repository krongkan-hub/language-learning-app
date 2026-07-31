from .llm import _llm_chat, strip_think_tags
import re
BASE_MODEL = 'qwen3:8b'
COACH_OPTS = {'temperature': 0.2, 'max_tokens': 250}
COACH_SYS = 'You are a language coach. The learner is practicing {language}.\n\nAnalyze ONLY the learner\'s most recent message. Everything you write — quotes,\ncorrections, suggestions, and reasons — must be in {language}, with the sole\nexception of the two fixed section labels below, which stay in English.\n\nYOUR STRONGEST BIAS IS TOWARD "Perfectly natural!". Most learner messages are\nalready correct. Your job is NOT to find something to fix in every message — it\nis to catch genuine mistakes and otherwise get out of the way. A correction you\nare not sure about does more harm than good.\n\nAlways begin with the Feedback section:\n\n💡 Feedback:\n- ❌ "[exact quote]" → ✅ "[correction]" (short reason in {language})\n\nRules for Feedback:\n- This section is ONLY for a CLEAR, UNAMBIGUOUS error a teacher would mark\n  wrong: broken grammar, a real spelling mistake, or a genuinely wrong word —\n  a word a native speaker simply would not use for that meaning in that context\n  (in Japanese, e.g. たくさん to mean "very much" should be とても).\n- The following are NOT errors — never "correct" them: a correct sentence, a\n  valid synonym or equally-natural phrasing (in Japanese, e.g. 何時 vs いつ are\n  both fine — do not swap one for the other; ～から vs ～まで have DIFFERENT\n  meanings, so never switch them), a different-but-also-natural politeness\n  level, or a stylistic preference.\n- Never change the MEANING of what the learner said. If your "correction" says\n  something different from their sentence, it is wrong — discard it.\n- When you are not certain something is a real error, treat the message as\n  correct.\n- If the grammar, spelling, and word choice are all fine, write EXACTLY this\n  and nothing more (no Feedback bullets, no Level up):\n  💡 Feedback: Perfectly natural!\n- Maximum 2 corrections. Quote their exact words. Keep their pronouns. Every\n  Feedback bullet MUST use the "❌ ... → ✅ ..." shape; if you would write\n  "✅ ... → ✅ ...", the message was correct, so write "Perfectly natural!"\n  instead.\n\nEXAMPLES (copy this behaviour exactly):\nLearner: "ブラックコーヒーをください。"\n💡 Feedback: Perfectly natural!\nLearner: "朝ごはんは何時からですか"\n💡 Feedback: Perfectly natural!\nLearner: "わたし、猫が好きだ、たくさん。"\n💡 Feedback:\n- ❌ "たくさん" → ✅ "とても" ("とても"が程度を表す自然な語です)\nLearner: "I want to finding a book."\n💡 Feedback:\n- ❌ "I want to finding" → ✅ "I want to find" (after "to", use the base verb)\n\nAfter Feedback you MAY add a Level up section — but ONLY when the message is\nalready correct AND you have a genuinely better, more natural phrasing a native\nspeaker would clearly prefer:\n\n⬆️ Level up:\n- "[their phrase]" → "[better phrase]" (short reason in {language})\n\nRules for Level up:\n- OMIT this section entirely — write nothing at all after Feedback — when there\n  is no real improvement to offer. Most correct messages need no Level up. Do\n  NOT fill it in just to have something, and NEVER suggest replacing a phrase\n  with the same phrase.\n- The suggested phrase must be meaningfully different from and better than the\n  learner\'s own.\n- A phrase may appear in Feedback OR Level up, never in both.\n\nKeep the labels "💡 Feedback:" and "⬆️ Level up:" exactly as written, in\nEnglish. If the learner used a non-{language} word, show the {language}\nequivalent.'

def _normalize_phrase(s: str) -> str:
    s = s.strip()
    s = re.sub('[.!?]+$', '', s).strip()
    s = re.sub('\\s+', ' ', s)
    return s

def _normalize_quotes(text: str) -> str:
    text = text.replace('->', '→').replace('=>', '→')
    text = text.replace('“', '"').replace('”', '"')
    for (open_q, close_q) in [('「', '」'), ('『', '』'), ('«', '»'), ('„', '"')]:
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
    (header, body) = (lines[0], lines[1:])
    kept = []
    for line in body:
        s = line.strip()
        if not s:
            continue
        if re.search('\\[[^\\]]*\\]', s):
            continue
        cleaned = re.sub('\\s*\\((?:why|reason)\\)\\s*$', '', line.rstrip(), flags=re.IGNORECASE)
        quotes = re.findall('"([^"]*)"', cleaned)
        if len(quotes) >= 2 and _normalize_phrase(quotes[0]) == _normalize_phrase(quotes[1]):
            continue
        kept.append(cleaned)
    if not kept:
        return ''
    return '\n'.join([header.strip()] + kept).strip()

def _tidy_whitespace(text: str) -> str:
    """Strip trailing spaces and collapse stray runs after the Feedback label."""
    lines = [re.sub('[ \\t]+$', '', ln) for ln in text.split('\n')]
    text = '\n'.join(lines)
    text = re.sub('💡 Feedback:[ \\t]+', '💡 Feedback: ', text)
    return text.strip()

def filter_coach_output(raw: str) -> str:
    """Split, normalise, parse, drop no-ops, dedupe, stitch. No I/O."""
    level_up_header_patterns = ['⬆️\\s*Level up:', '⬆️ Level up:', 'Level up:']
    feedback_block = raw
    level_up_block = ''
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
        match = re.search('❌\\s*"(.*?)"\\s*→\\s*✅\\s*"(.*?)"', line)
        if match:
            said_norm = _normalize_phrase(match.group(1))
            better_norm = _normalize_phrase(match.group(2))
            if said_norm == better_norm:
                continue
            if any((c == said_norm for c in corrections)):
                continue
            corrections.append(said_norm)
            kept_lines.append(line)
        elif '→' in line or re.search('✅\\s*"', line):
            continue
        else:
            kept_lines.append(line)
    if corrections:
        # Suppress any "Perfectly natural!" lines if real corrections exist
        clean_kept = [l for l in kept_lines if 'perfectly natural' not in l.lower()]
        final_feedback = '\n'.join(clean_kept).strip()
        if not final_feedback.startswith('💡 Feedback:'):
            final_feedback = f'💡 Feedback:\n{final_feedback}'
    else:
        remaining = '\n'.join(kept_lines)
        body = re.sub('💡\\s*Feedback:?', '', remaining).strip()
        if not body or 'perfectly natural' in remaining.lower():
            final_feedback = '💡 Feedback: Perfectly natural!'
        else:
            final_feedback = remaining.strip()
    if level_up_block:
        level_up_block = _clean_level_up_block(level_up_block)
    if level_up_block:
        return _tidy_whitespace(f'{final_feedback}\n\n{level_up_block}')
    return _tidy_whitespace(final_feedback)

def call_coach(user_input: str, language: str) -> str:
    """Get language feedback on the learner's message."""
    system = COACH_SYS.format(language=language)
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user_input}]
    response = _llm_chat(messages=messages, options=COACH_OPTS)
    raw = response['message']['content']
    raw = strip_think_tags(raw).strip()
    return filter_coach_output(raw)