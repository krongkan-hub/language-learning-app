"""What survives between the model's reply and the learner's screen.

Dedupe, no-op collapse, scaffold removal, and the two guards that drop a
correction the learner cannot use: one for a quote they never wrote, one
for a fix that introduces a word they never said. See BACKLOG OPEN-38.
"""
import re


_SENTENCE_END = re.compile('[.!?。．！？]+$')


def _normalize_phrase(s: str) -> str:
    s = s.strip()
    s = _SENTENCE_END.sub('', s).strip()
    s = re.sub('\\s+', ' ', s)
    return s

def _normalize_quotes(text: str) -> str:
    text = text.replace('->', '→').replace('=>', '→')
    text = text.replace('“', '"').replace('”', '"')
    for (open_q, close_q) in [('「', '」'), ('『', '』'), ('«', '»'), ('„', '"')]:
        text = text.replace(open_q, '"').replace(close_q, '"')
    return text

# The placeholder words COACH_SYS actually uses. A bracket around anything
# else is the model quoting real text with the template's punctuation still
# attached, and the brackets are simply stripped.
_SCAFFOLD_BRACKET = re.compile(
    r'\[\s*(their phrase|better phrase|exact quote|correction|short reason'
    r'|reason in \w+|word|explanation)[^\]]*\]', re.IGNORECASE)
_BRACKETS_AROUND_CONTENT = re.compile(r'\[([^\]]+)\]')


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
        # Only the prompt's literal placeholders are scaffold. This used to
        # drop ANY bullet containing brackets, and COACH_SYS's own Level up
        # template is `- "[their phrase]" → "[better phrase]"` — so whenever the
        # model copied the brackets around REAL content, the bullet was deleted
        # silently. Measured at 2 of 10 Japanese cases, and one of them threw
        # away the best correction in the run:
        #     - "[電車に乗るのため]" → "[電車に乗るために]"
        if _SCAFFOLD_BRACKET.search(s):
            continue
        s = _BRACKETS_AROUND_CONTENT.sub(r'\1', s)
        line = _BRACKETS_AROUND_CONTENT.sub(r'\1', line)
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

# Reasons that mark a Level up bullet as a SITUATIONAL FIT problem rather than
# ordinary polish. Measured on real output: told "Give me a large coffee." at a
# café, the model files the fix under Level up with "more polite and natural in
# a service context", leaving Feedback saying "Perfectly natural!". The eval
# scores Feedback and the repeat drill only drills Feedback, so those fixes
# reached neither. Promoting them is what makes the situational feature bite —
# it caught roughly a third of violations without this.
#
# The list is deliberately about POLITENESS AND REGISTER, not "more natural":
# the latter is ordinary style polish, which is what Level up is for and which
# the learner should not be made to retype.
_FIT_MARKERS = (
    'polite', 'politeness', 'courteous', 'respectful', 'formal', 'rude',
    'blunt', 'demanding', 'softer', 'service context',
    '丁寧', '敬語', '失礼', 'ぶっきらぼう', '柔らか', '目上', '接客',
)


# Politeness already present in the learner's own sentence. Japanese: the
# ます/です register and the request forms built on it. English: the modal and
# softener set that makes a request rather than a command.
_POLITE_ALREADY = (
    'ます', 'です', 'ください', 'いただけ', 'もらえ', 'でしょうか', 'ますか',
    'please', 'could you', 'could i', 'would you', 'would like', 'may i',
    'can i have', 'excuse me', "i'd like",
)


def _promote_fit_bullet(line: str):
    """Turn a plain Level up bullet into a Feedback correction when its reason
    is about politeness or register. Returns (said, better, bullet) or None.

    Only the plain `"X" → "Y" (reason)` shape is considered — a bullet already
    carrying ❌/✅ is handled by the loop above.
    """
    match = re.search('"(.*?)"\\s*→\\s*"(.*?)"', line)
    if not match:
        return None
    reason = line[match.end():]
    if not any(marker in reason.lower() for marker in _FIT_MARKERS):
        return None
    said, better = match.group(1), match.group(2)
    # A reason saying "more polite" covers two different things the model does
    # not distinguish: fixing a rude sentence, and offering a politer variant
    # of an already-polite one. Measured: 「領収書をもらえますか。」 — correct and
    # polite at a café — was promoted 5/5 on 「より丁寧な表現です」, which under a
    # no-skip drill forces the learner to retype a sentence that was fine.
    #
    # The learner's own sentence settles it: you cannot be rude in a sentence
    # that already uses a polite form, so an upgrade to one is polish and stays
    # in Level up. This is why the check is on `said` and not on the reason.
    # Case-folded: the English markers are lowercase and a learner writes
    # "Could I get a receipt?" with a capital. Japanese is unaffected by fold.
    if any(marker in said.lower() for marker in _POLITE_ALREADY):
        return None
    said_norm, better_norm = _normalize_phrase(said), _normalize_phrase(better)
    if said_norm == better_norm:
        return None
    tail = reason.strip()
    bullet = f'- ❌ "{said}" → ✅ "{better}" {tail}'.rstrip()
    return said_norm, better_norm, bullet


# A correction may INFLECT what the learner wrote ("two bottle" -> "two
# bottles", "is prohibit" -> "is prohibited") and may add function words, but it
# may not introduce a CONTENT word they never used. Stem-matching on a prefix
# handles the inflection cases without a morphology library.
#
# Why it exists — the coach completing the learner's thought, and the no-skip
# drill then making them type it: BACKLOG OPEN-38.
_FUNCTION_WORDS = set(
    "a an the this that these those my your his her its our their "
    "i you he she it we they me him us them "
    "is am are was were be been being do does did have has had "
    "will would shall should can could may might must "
    "to of in on at by for with from into onto about over under "
    "and or but so if then than as not no yes please thank thanks "
    "there here it's i'd i'll i'm we'd we'll let lets".split())

_LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z']*")
# Runs of kanji or katakana — the units a Japanese correction would smuggle in.
_JA_CONTENT = re.compile(r'[一-鿿]{2,}|[ァ-ヴー]{2,}')


def _introduces_new_content(correction: str, quoted: str, user_input: str) -> bool:
    """True when the ✅ side uses a content word the learner never wrote.

    Applied to Feedback bullets only, NOT to promoted Level up bullets. A
    politeness promotion necessarily rewrites — "Give me a large coffee" ->
    "Could I get a large coffee, please?" introduces "get" — and that is the
    feature working, because the learner's subject matter survives. What this
    catches is a changed referent: the learner ordered hot milk and was told to
    say "warmed coffee is okay". Extending it to promotions broke the register
    feature outright, so the scope is deliberate rather than an oversight.
    """
    haystack = f'{quoted} {user_input}'.lower()
    known = [t.lower() for t in _LATIN_TOKEN.findall(haystack)]
    for token in _LATIN_TOKEN.findall(correction):
        low = token.lower()
        if low in _FUNCTION_WORDS:
            continue
        # Same word, or an inflection of one the learner used.
        if any(k.startswith(low[:4]) or low.startswith(k[:4]) for k in known if len(k) >= 3):
            continue
        if low in haystack:
            continue
        return True
    for run in _JA_CONTENT.findall(correction):
        if run not in haystack:
            return True
    return False


# The ❌ side must be something the learner actually wrote. COACH_SYS asks for
# "[exact quote]" and "Quote their exact words", and the model does not always
# comply: from a real session, the learner typed
#
#     "Hello, I want to know what tasting flight you have and how much it cost?"
#
# and was told ❌ "Can I ask" → ✅ "May I ask". They never wrote "Can I ask". The
# drill then made them retype a correction to a sentence they had not produced.
#
# The test is content-word overlap, not an exact substring: a legitimate quote
# differs in punctuation, case and spacing, and `_normalize_phrase` does not
# cover every shape. A fabricated quote shares no content word at all —
# "Can I ask" against that sentence has none, while "how much it cost" has
# three. Function words are ignored because "I" alone means nothing.
def _quote_is_the_learners(quoted: str, user_input: str) -> bool:
    """True when the ❌ side plausibly comes from the learner's own message."""
    if not quoted or not user_input:
        return True                      # nothing to check against
    said = user_input.lower()
    latin = [w for w in _LATIN_TOKEN.findall(quoted.lower())
             if w not in _FUNCTION_WORDS and len(w) >= 3]
    ja = _JA_CONTENT.findall(quoted)
    if not latin and not ja:
        return True                      # only function words; nothing to judge
    return (any(w in said for w in latin)
            or any(run in user_input for run in ja))


def filter_coach_output(raw: str, promote_fit: bool = False,
                        user_input: str = '') -> str:
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
    # Both blocks must be normalized here, not just Feedback: the promotion loop
    # below matches ❌ "..." → ✅ "..." on the Level up text, and it used to run
    # before _clean_level_up_block did the normalizing. A correction quoted with
    # 「」 (or curly quotes in English) was therefore never promoted, leaving the
    # learner a clean verdict sitting directly above a grammar fix — BUG-001.
    level_up_block = _normalize_quotes(level_up_block)
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
            # A correction that introduces a content word the learner never
            # wrote is a rewrite, not a correction — and because promote_fit
            # puts these in Feedback, the drill would force the learner to type
            # it. See _introduces_new_content.
            if user_input and not _quote_is_the_learners(match.group(1), user_input):
                continue
            if user_input and _introduces_new_content(match.group(2),
                                                      match.group(1), user_input):
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
            if promote_fit and len(corrections) + len(promoted_corrections) < 2:
                promoted = _promote_fit_bullet(line)
                if promoted:
                    said_norm, better_norm, bullet = promoted
                    if said_norm != better_norm and said_norm not in corrections:
                        promoted_corrections.append(bullet)
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
