from .llm import _llm_chat, strip_think_tags
import re

COACH_OPTS = {'temperature': 0.2, 'max_tokens': 250}
COACH_SYS = 'You are a language coach. The learner is practicing {language}.\n\nAnalyze ONLY the learner\'s most recent message. Everything you write — quotes,\ncorrections, suggestions, and reasons — must be in {language}, with the sole\nexception of the two fixed section labels below, which stay in English.\n\nYOUR STRONGEST BIAS IS TOWARD "Perfectly natural!". Most learner messages are\nalready correct. Your job is NOT to find something to fix in every message — it\nis to catch genuine mistakes and otherwise get out of the way. A correction you\nare not sure about does more harm than good.\n\nAlways begin with the Feedback section:\n\n💡 Feedback:\n- ❌ "[exact quote]" → ✅ "[correction]" (short reason in {language})\n\nRules for Feedback:\n- This section is ONLY for a CLEAR, UNAMBIGUOUS error a teacher would mark\n  wrong: broken grammar (including missing verb inflections, wrong participle\n  forms such as a bare verb after "is/are" e.g. "is prohibit" → "is prohibited",\n  wrong verb form after "to", number/plural agreement e.g. after a number or quantifier a countable noun must be plural "two bottle" → "two bottles", or attaching "だ" to an i-adjective e.g. "欲しいだ" → "欲しいです"; an i-adjective takes "です" for politeness, never "だ"), a real spelling mistake, or a genuinely wrong word —\n  a word a native speaker simply would not use for that meaning in that context\n  (in Japanese, e.g. たくさん to mean "very much" should be とても).\n- The following are NOT errors — never "correct" them: a correct sentence, a\n  valid synonym or equally-natural phrasing (in Japanese, e.g. 何時 vs いつ are\n  both fine — do not swap one for the other; ～から vs ～まで have DIFFERENT\n  meanings, so never switch them; ～で in "ブラックで" is valid manner specification, do not change to ～の), a different-but-also-natural politeness\n  level, or a stylistic preference.\n- Never change the MEANING of what the learner said. If your "correction" says\n  something different from their sentence, it is wrong — discard it.\n- When you are not certain something is a real error, treat the message as\n  correct.\n- If the grammar, spelling, and word choice are all fine, write EXACTLY this\n  and nothing more (no Feedback bullets, no Level up):\n  💡 Feedback: Perfectly natural!\n- Maximum 2 corrections. Quote their exact words. Keep their pronouns. Every\n  Feedback bullet MUST use the "❌ ... → ✅ ..." shape; if you would write\n  "✅ ... → ✅ ...", the message was correct, so write "Perfectly natural!"\n  instead.\n\nEXAMPLES (copy this behaviour exactly):\nLearner: "ブラックコーヒーをください。"\n💡 Feedback: Perfectly natural!\nLearner: "朝ごはんは何時からですか"\n💡 Feedback: Perfectly natural!\nLearner: "Is it prohibit here?"\n💡 Feedback:\n- ❌ "Is it prohibit" → ✅ "Is it prohibited" (after "is", use the past participle "prohibited")\nLearner: "Can I get two bottle of water, please?"\n💡 Feedback:\n- ❌ "two bottle" → ✅ "two bottles" (after a number, use the plural)\nLearner: "わたし、猫が好きだ、たくさん。"\n💡 Feedback:\n- ❌ "たくさん" → ✅ "とても" ("とても"が程度を表す自然な語です)\nLearner: "コーヒーを一つ欲しいだ、ブラックで。"\n💡 Feedback:\n- ❌ "欲しいだ" → ✅ "欲しいです" (い形容詞に「だ」は付きません)\nLearner: "I want to finding a book."\n💡 Feedback:\n- ❌ "I want to finding" → ✅ "I want to find" (after "to", use the base verb)\n\nAfter Feedback you MAY add a Level up section — but ONLY when the message is\nalready correct AND you have a genuinely better, more natural phrasing a native\nspeaker would clearly prefer:\n\n⬆️ Level up:\n- "[their phrase]" → "[better phrase]" (short reason in {language})\n\nRules for Level up:\n- OMIT this section entirely — write nothing at all after Feedback — when there\n  is no real improvement to offer. Most correct messages need no Level up. Do\n  NOT fill it in just to have something, and NEVER suggest replacing a phrase\n  with the same phrase.\n- NEVER write "Perfectly natural!" and then offer a grammatical fix in Level up.\n  If a correction fixes grammar, spelling, or word form, it is a Feedback bullet.\n  Level up is only for a genuinely better phrasing of an already-grammatical sentence.\n- The suggested phrase must be meaningfully different from and better than the\n  learner\'s own.\n- A phrase may appear in Feedback OR Level up, never in both.\n\nKeep the labels "💡 Feedback:" and "⬆️ Level up:" exactly as written, in\nEnglish. If the learner used a non-{language} word, show the {language}\nequivalent.'

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

def _clean_level_up_block(block: str, feedback_quotes: set = None) -> str:
    """Drop no-op / scaffold Level up bullets; omit the section if nothing real
    survives. Also suppress duplicate quotes that appeared in Feedback.
    """
    if feedback_quotes is None:
        feedback_quotes = set()
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
        if len(quotes) >= 2:
            q0 = _normalize_phrase(quotes[0])
            q1 = _normalize_phrase(quotes[1])
            if q0 == q1:
                continue
            if q0 in feedback_quotes or q1 in feedback_quotes:
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
    feedback_quotes = set()

    for line in lines:
        match = re.search('❌\\s*"(.*?)"\\s*→\\s*✅\\s*"(.*?)"', line)
        if match:
            said_norm = _normalize_phrase(match.group(1))
            better_norm = _normalize_phrase(match.group(2))
            if said_norm == better_norm:
                continue
            if any((c == said_norm for c in corrections)):
                continue
            if len(corrections) >= 2:  # Enforce max 2 corrections
                continue
            corrections.append(said_norm)
            feedback_quotes.add(said_norm)
            feedback_quotes.add(better_norm)
            kept_lines.append(line)
        elif '→' in line or re.search('✅\\s*"', line):
            continue
        else:
            kept_lines.append(line)

    # BUG-001 / BL-12: Check if Level up contains explicit error corrections (❌ -> ✅ or correction phrasing)
    # If Feedback says "Perfectly natural!", promote these corrections into Feedback
    promoted_corrections = []
    if level_up_block:
        level_up_lines = level_up_block.split('\n')
        remaining_level_up = [level_up_lines[0]] if level_up_lines else []
        for line in level_up_lines[1:]:
            match_err = re.search('❌\\s*"(.*?)"\\s*→\\s*✅\\s*"(.*?)"', line)
            if match_err and len(corrections) + len(promoted_corrections) < 2:
                said_norm = _normalize_phrase(match_err.group(1))
                better_norm = _normalize_phrase(match_err.group(2))
                if said_norm != better_norm and said_norm not in corrections:
                    promoted_corrections.append(line)
                    feedback_quotes.add(said_norm)
                    feedback_quotes.add(better_norm)
                    continue
            remaining_level_up.append(line)
        level_up_block = '\n'.join(remaining_level_up)

    if corrections or promoted_corrections:
        # Suppress any "Perfectly natural!" lines if real corrections exist
        clean_kept = [l for l in kept_lines if 'perfectly natural' not in l.lower()]
        if promoted_corrections:
            clean_kept.extend(promoted_corrections)
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
        level_up_block = _clean_level_up_block(level_up_block, feedback_quotes=feedback_quotes)
    if level_up_block:
        return _tidy_whitespace(f'{final_feedback}\n\n{level_up_block}')
    return _tidy_whitespace(final_feedback)

# Verbs that mark their partner or destination with に/と, so a を sitting
# directly in front of one is a learner error. Qwen2.5-7B calls
# 「友達を会いました」 fully correct even when asked outright with no leniency
# bias, so no wording of COACH_SYS can reach this class — prompt rules and a
# near-verbatim worked example both left it at 0/5 (OPEN-07). Handled in code
# for that reason, and only ever to overturn a clean verdict: a real correction
# from the model always wins.
_NI_TARGET_VERBS = {
    '会': '「会う」の相手は「に」か「と」で示します',
    '乗': '「乗る」の行き先は「に」で示します',
}
# The noun class excludes particles so 「久しぶりに友達を会う」 quotes 友達, not
# 久しぶりに友達. Requiring を to touch the verb keeps causatives, where を is
# correct, out: 「友達を医者に会わせた」 has a noun after を, and the わ stems of
# 会わせる/乗せる are outside the stem classes.
#
# 乗 is spelled out as whole inflections of plain 乗る rather than as a stem
# class, because 乗り/乗っ also open every compound built on 乗る, and those
# compounds take を: 電車を乗り換える, 駅を乗り過ごす, 飛行機を乗っ取る,
# 困難を乗り越える. Matching a stem class flagged all of those as errors. An
# inflection list also survives kana spelling — 「電車を乗りかえます」 is left
# alone, where a "no kanji after the stem" rule would still fire on it. The
# cost is missing を on inflections nobody listed here; a miss is recoverable,
# telling a learner that correct Japanese is wrong is not.
_NI_PARTICLE_ERROR = re.compile(
    '(?P<noun>[^\\s、。「」『』！？!?・をはがにでともへや]{1,12})を'
    '(?P<stem>会[いうっえお]'
    '|乗(?:る|った|って|ります|りました|りません|りましょう|りたい|らない|れば|ろう))'
)


def apply_particle_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict when を sits on a に/と-taking verb's target."""
    if language != 'Japanese' or 'perfectly natural' not in feedback.lower():
        return feedback
    match = _NI_PARTICLE_ERROR.search(user_input)
    if not match:
        return feedback
    noun = match.group('noun')
    reason = _NI_TARGET_VERBS[match.group('stem')[0]]
    return f'💡 Feedback:\n- ❌ "{noun}を" → ✅ "{noun}に" ({reason})'


def coach_feedback(raw: str, user_input: str, language: str) -> str:
    """The exact text the learner sees: filter the model, then net what it missed."""
    return apply_particle_net(filter_coach_output(raw), user_input, language)


def call_coach(user_input: str, language: str) -> str:
    """Get language feedback on the learner's message."""
    system = COACH_SYS.format(language=language)
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user_input}]
    response = _llm_chat(messages=messages, options=COACH_OPTS, cache_key='coach')
    raw = response['message']['content']
    raw = strip_think_tags(raw).strip()
    return coach_feedback(raw, user_input, language)