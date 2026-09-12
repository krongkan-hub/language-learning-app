from .llm import _llm_chat, strip_think_tags, find_wrong_script
from typing import Optional
import re

COACH_OPTS = {'temperature': 0.2, 'max_tokens': 250}
COACH_SYS = 'You are a language coach. The learner is practicing {language}.\n\nAnalyze ONLY the learner\'s most recent message. Everything you write — quotes,\ncorrections, suggestions, and reasons — must be in {language}, with the sole\nexception of the two fixed section labels below, which stay in English.\n\nYOUR STRONGEST BIAS IS TOWARD "Perfectly natural!". Most learner messages are\nalready correct. Your job is NOT to find something to fix in every message — it\nis to catch genuine mistakes and otherwise get out of the way. A correction you\nare not sure about does more harm than good.\n\nAlways begin with the Feedback section:\n\n💡 Feedback:\n- ❌ "[exact quote]" → ✅ "[correction]" (short reason in {language})\n\nRules for Feedback:\n- This section is ONLY for a CLEAR, UNAMBIGUOUS error a teacher would mark\n  wrong: broken grammar (including missing verb inflections, wrong participle\n  forms such as a bare verb after "is/are" e.g. "is prohibit" → "is prohibited",\n  wrong verb form after "to", number/plural agreement e.g. after a number or quantifier a countable noun must be plural "two bottle" → "two bottles", or attaching "だ" to an i-adjective e.g. "欲しいだ" → "欲しいです"; an i-adjective takes "です" for politeness, never "だ"), a real spelling mistake, or a genuinely wrong word —\n  a word a native speaker simply would not use for that meaning in that context\n  (in Japanese, e.g. たくさん states an AMOUNT, so using it for a DEGREE is\n  wrong and should be とても). That rule runs in ONE direction only: とても\n  cannot state an amount, and たくさん in front of a noun being counted is\n  correct — so never "fix" a たくさん that is counting things, and never\n  replace とても with たくさん.\n- The following are NOT errors — never "correct" them: a correct sentence, a\n  valid synonym or equally-natural phrasing (in Japanese, e.g. 何時 vs いつ are\n  both fine — do not swap one for the other; ～から vs ～まで have DIFFERENT\n  meanings, so never switch them; ～で in "ブラックで" is valid manner specification, do not change to ～の), a politeness level that also\n  fits the learner\'s situation, or a stylistic preference.\n- Adding or removing a SENTENCE-FINAL particle (よ, ね, か at the very end)\n  is NEVER a correction: it changes tone, or turns a statement into a\n  question, and neither of those is a grammar mistake. This covers those\n  sentence-final particles ONLY. A wrong CASE particle inside the sentence\n  — が for の, を for に, に for で — is a real grammar error and MUST be\n  corrected.\n- When a Japanese て-form is built wrongly, the fix is the correct て-form\n  (the 音便 form), NOT a different tense: 「飲みて」 is 「飲んで」, never\n  「飲んだ」 — changing the tense breaks the clause that follows.\n- The reason in brackets must describe the change you ACTUALLY made. Never\n  call a form the "base form" or "base verb" unless the ✅ word IS the\n  dictionary form: "costs" and "lives" are a third-person "-s", "bought" is\n  a past tense, "going" is an -ing form. And when the fix ADDS a word, the\n  reason must name the word that was missing, not restate the phrase the\n  addition creates.\n- Never change the MEANING of what the learner said. If your "correction" says\n  something different from their sentence, it is wrong — discard it.\n- When you are not certain something is a real error, treat the message as\n  correct.\n- If the grammar, spelling, and word choice are all fine, write EXACTLY this\n  and nothing more (no Feedback bullets, no Level up):\n  💡 Feedback: Perfectly natural!\n- Maximum 2 corrections. Quote their exact words. Keep their pronouns. Every\n  Feedback bullet MUST use the "❌ ... → ✅ ..." shape; if you would write\n  "✅ ... → ✅ ...", the message was correct, so write "Perfectly natural!"\n  instead.\n\nEXAMPLES (copy this behaviour exactly):\nLearner: "ブラックコーヒーをください。"\n💡 Feedback: Perfectly natural!\nLearner: "朝ごはんは何時からですか"\n💡 Feedback: Perfectly natural!\nLearner: "Is it prohibit here?"\n💡 Feedback:\n- ❌ "Is it prohibit" → ✅ "Is it prohibited" (after "is", use the past participle "prohibited")\nLearner: "Can I get two bottle of water, please?"\n💡 Feedback:\n- ❌ "two bottle" → ✅ "two bottles" (after a number, use the plural)\nLearner: "わたし、猫が好きだ、たくさん。"\n💡 Feedback:\n- ❌ "たくさん" → ✅ "とても" ("とても"が程度を表す自然な語です)\nLearner: "公園にたくさんの人がいます。"\n💡 Feedback: Perfectly natural!\nLearner: "コーヒーを一つ欲しいだ、ブラックで。"\n💡 Feedback:\n- ❌ "欲しいだ" → ✅ "欲しいです" (い形容詞に「だ」は付きません)\nLearner: "I want to finding a book."\n💡 Feedback:\n- ❌ "I want to finding" → ✅ "I want to find" (after "to" the verb takes no ending: "find")\nLearner: "My friend live in Osaka."\n💡 Feedback:\n- ❌ "My friend live" → ✅ "My friend lives" (a third-person singular subject takes "-s")\nLearner: "I need buy a ticket."\n💡 Feedback:\n- ❌ "I need buy" → ✅ "I need to buy" ("need" takes "to" before the verb — the missing word is "to")\n\nAfter Feedback you MAY add a Level up section — but ONLY when the message is\nalready correct AND you have a genuinely better, more natural phrasing a native\nspeaker would clearly prefer:\n\n⬆️ Level up:\n- "[their phrase]" → "[better phrase]" (short reason in {language})\n\nRules for Level up:\n- OMIT this section entirely — write nothing at all after Feedback — when there\n  is no real improvement to offer. Most correct messages need no Level up. Do\n  NOT fill it in just to have something, and NEVER suggest replacing a phrase\n  with the same phrase.\n- NEVER write "Perfectly natural!" and then offer a grammatical fix in Level up.\n  If a correction fixes grammar, spelling, or word form, it is a Feedback bullet.\n  Level up is only for a genuinely better phrasing of an already-grammatical sentence.\n- The suggested phrase must be meaningfully different from and better than the\n  learner\'s own.\n- A phrase may appear in Feedback OR Level up, never in both.\n\nKeep the labels "💡 Feedback:" and "⬆️ Level up:" exactly as written, in\nEnglish. If the learner used a non-{language} word, show the {language}\nequivalent.'

# Appended to COACH_SYS only when the caller can say where the learner is and
# who they are talking to. A coach that is told nothing about the setting cannot
# judge fit and would have to invent one, so with no situation the prompt stays
# byte-for-byte what it was and appropriateness judging is simply off.
#
# The scope is exactly three classes because those are the ones a learner can
# act on. "Wrong topic for the venue" is deliberately absent: the actor prompt
# already pushes back on a request that does not belong at its counter, and a
# coach that also flagged it would be marking the learner's grammar wrong for a
# content choice.
#
# Everything after the three rules is brake, not accelerator. Over-correction is
# the failure this project treats as worst, and telling a learner their entirely
# appropriate sentence is rude is the sharpest form of it.
COACH_SITUATION = '''

THE SITUATION: {situation}

On top of the rules above, a Feedback bullet MAY also flag a sentence that is
grammatically fine but does not fit THIS situation, in these three cases only:
- Register mismatch: plain or casual forms where this situation clearly calls
  for polite ones, or stiff formal language aimed at someone this situation
  makes a friend or an equal.
- Too blunt for the culture: a bare command where asking a stranger or a
  service worker for something needs a softener or a request form.
- A missing social move this situation requires: no greeting at all before a
  first request to a stranger, no thanks for something just received, no
  apology when the learner says they are late or have caused trouble.

Judge NOTHING else against the situation. The TOPIC in particular is never your
business: if the learner asks for something this place does not provide, that is
for the other person to answer and is not a language error.

The bias toward "Perfectly natural!" applies here at FULL strength — these three
rules are the easiest in this prompt to over-apply:
- Two politeness levels often both fit one situation. Only a level that CLASHES
  with this situation is an error; a different but still fitting one is a
  stylistic preference and must be left alone.
- A polite request form is already polite enough for any service situation.
  Never ask for humbler or more honorific language on top of one.
- A greeting, a thank-you or an apology is missing only when this situation
  actually demands it. A single sentence in the middle of a conversation, and
  any answer to a question the other person asked, demands none of them.
- If you are weighing whether something is rude, it is not. Say
  "Perfectly natural!".

An appropriateness bullet takes the same "❌ ... → ✅ ..." shape as any other,
quoting their words and giving the wording that fits, reason in {language}.'''


def describe_situation(place: Optional[str] = None, role: Optional[str] = None,
                       speaker: Optional[str] = None) -> str:
    """One line naming where the learner is and who they are speaking to.

    `role` is written as an instruction to the actor ("You are a busy
    barista."), so it is re-pointed at the listener rather than quoted at the
    coach, which would otherwise read as an instruction to become one.
    """
    listener = re.sub('^\\s*You are\\s+', '', (role or '').strip()).strip().rstrip('.')
    if not listener:
        listener = (speaker or '').strip().rstrip('.')
    setting = (place or '').strip().rstrip('.')
    if setting:
        setting = setting[0].lower() + setting[1:]
    if listener and setting:
        return f'The learner is speaking to {listener}, at {setting}.'
    if listener:
        return f'The learner is speaking to {listener}.'
    if setting:
        return f'The learner is speaking to someone at {setting}.'
    return ''


def coach_system(language: str, situation: Optional[str] = None) -> str:
    """The coach's system prompt, with the appropriateness rules only when the
    caller supplied a situation for them to be judged against."""
    system = COACH_SYS.format(language=language)
    if situation:
        system += COACH_SITUATION.format(language=language, situation=situation)
    return system


# Sentence-final punctuation is presentation, not grammar, so a "correction"
# that only adds or drops a terminator is a no-op. The ASCII three were already
# treated that way; the CJK and full-width twins are the same three marks and
# are stripped identically. Measured on real coach output: when the model quotes
# a whole learner sentence it carries the terminator into the quote — 12 quotes
# ended in '.', 4 in 。 across 30 forced sentence-level corrections — which is
# exactly the shape that reached the learner as ❌X → ✅X in Japanese.
#
# 、 is deliberately NOT here. It is a comma, not a terminator: its ASCII twin
# ',' is not stripped either, no quote in the corpus ended in one, and dropping
# a spurious comma is a real correction a learner should see.
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


# A Feedback bullet must CORRECT what the learner wrote, not add to it. The
# model ignores that rule in a specific way: it completes the learner's thought.
# Reproduced from a real session — the learner had just ordered hot milk, having
# said they cannot drink coffee:
#
#     ❌ "warmed is okay"        → ✅ "warmed coffee is okay"
#     ❌ "can I get a discount?" → ✅ "can I get a discount with my loyalty card?"
#
# Neither is a grammar error, and the first is factually wrong about the
# learner's own order. COACH_SYS already says "Never change the MEANING of what
# the learner said"; nothing enforced it, and because promote_fit puts these in
# Feedback, run_correction_drill then made the learner type "warmed coffee is
# okay" with no way to skip.
#
# The test is deliberately narrow: a correction may INFLECT what is there
# ("two bottle" -> "two bottles", "is prohibit" -> "is prohibited") and may add
# function words, but it may not introduce a content word the learner never
# used. Stem-matching on a prefix handles the inflection cases without a
# morphology library.
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


# Transitive/intransitive pairs, the largest net-able slice of OPEN-10: the
# coach scores 0/3 on them, answering "Perfectly natural!" to 電気をつきました,
# 会議が始めました and 窓が閉めました. The pairs are a closed, enumerable set,
# which is what makes a deterministic net possible here where it is not for
# particle choice or register.
#
# Stems are listed as the ren'youkei (ます-stem) plus the dictionary form,
# because those two cover every inflection the learner is likely to write and
# an inflection list is what kept the 乗る net out of trouble.
_TI_PAIRS = (
    # (intransitive stems, transitive stems, intransitive citation, transitive citation)
    (('つき', 'つく'), ('つけ', 'つける'), 'つきます', 'つけます'),
    (('閉まり', '閉まる'), ('閉め', '閉める'), '閉まります', '閉めます'),
    (('始まり', '始まる'), ('始め', '始める'), '始まります', '始めます'),
    (('開き', '開く'), ('開け', '開ける'), '開きます', '開けます'),
    (('消え', '消える'), ('消し', '消す'), '消えます', '消します'),
    (('入り', '入る'), ('入れ', '入れる'), '入ります', '入れます'),
    (('止まり', '止まる'), ('止め', '止める'), '止まります', '止めます'),
    (('変わり', '変わる'), ('変え', '変える'), '変わります', '変えます'),
    (('決まり', '決まる'), ('決め', '決める'), '決まります', '決めます'),
    (('壊れ', '壊れる'), ('壊し', '壊す'), '壊れます', '壊します'),
    (('届き', '届く'), ('届け', '届ける'), '届きます', '届けます'),
    (('落ち', '落ちる'), ('落とし', '落とす'), '落ちます', '落とします'),
)

# が + a transitive verb is NOT an error in general — が marks the agent, so
# 「私が閉めました」 is correct. It is only wrong when the noun is the thing
# being acted on, which needs semantics we do not have. So rule B fires only
# for an enumerated set of inanimate patients. Anything not listed, including
# every person, is left to the model.
_TI_PATIENTS = (
    '窓', 'ドア', '扉', '電気', '明かり', '照明', '電源', 'テレビ', 'エアコン',
    '会議', '授業', '試合', '店', '番組', '映画', 'パーティー', '荷物', '予約',
    '火', 'お湯', 'music', '音楽', 'ドアベル', 'カーテン',
)

# られ/れ mark passive and potential, where the transitive stem is correct:
# 「窓が閉められました」 is good Japanese. Never fire in front of them.
_TI_SUFFIX_BLOCK = ('られ', 'れる', 'れま', 'れた')


def _ti_lookup(text: str, stems, offset: int):
    """Match a stem sitting IMMEDIATELY at `offset`, never merely later in the
    sentence. Searching ahead produced false positives on correct multi-clause
    Japanese — 「電気をつけて、窓が閉まりました。」 matched the intransitive 閉まり
    from the second clause against the を of the first and "corrected" it. The
    error shape this net targets is adjacent by construction (電気を+つきました),
    so adjacency costs nothing and removes the whole class."""
    for stem in stems:
        if text.startswith(stem, offset):
            after = text[offset + len(stem): offset + len(stem) + 2]
            if not any(after.startswith(b) for b in _TI_SUFFIX_BLOCK):
                return stem
    return None


# Counters, the other net-able slice of OPEN-10 (currently 1/3). Japanese
# picks a counter from the SHAPE of the thing counted, so noun->counter is a
# closed mapping a rule can check where particle choice and register cannot be.
#
# Deliberately a DENY list, not an allow list. つ and 個 are near-universal
# fallbacks and many nouns take several counters legitimately (水 is 本 by the
# bottle and 杯 by the glass), so enumerating what is allowed would over-fire
# on correct Japanese. Only pairings that are unambiguously wrong are listed,
# and everything unlisted is left to the model.
_COUNTER_RULES = (
    # (nouns, counters that are wrong for them, suggested counters, reason)
    (('水', 'お茶', 'コーヒー', 'ジュース', 'ビール', 'ワイン', '牛乳'),
     ('枚', '冊', '匹', '台', '本人'),
     ('本', '杯'), '液体は瓶なら「本」、グラスなら「杯」で数えます'),
    (('切符', 'チケット', '写真', '紙', 'カード', '切手', 'シャツ', 'お皿'),
     ('本', '冊', '匹', '台', '杯'),
     ('枚',), '薄くて平らなものは「枚」で数えます'),
    (('りんご', 'みかん', '卵', 'たまご', 'ボール', '石鹸'),
     ('本', '枚', '冊', '匹', '台', '杯'),
     ('つ', '個'), '丸くて小さいものは「つ」か「個」で数えます'),
    (('雑誌', 'ノート', '辞書', '教科書'),
     ('本', '枚', '匹', '台', '杯'),
     ('冊',), '本や雑誌は「冊」で数えます'),
)
# Numerals that can precede a counter, kanji and arabic.
_COUNT_NUM = '[0-9０-９一二三四五六七八九十百千]+'


def apply_counter_net(feedback: str, user_input: str, language: str) -> str:
    """Catch a counter that does not match the shape of the noun counted.
    Only ever overturns a clean verdict."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    for nouns, wrong_counters, suggested, reason in _COUNTER_RULES:
        for noun in nouns:
            for wrong in wrong_counters:
                # The noun and its count sit adjacent in the error shape
                # (水を三枚), the same adjacency that kept the transitivity net
                # from reaching across clauses.
                pattern = re.escape(noun) + r'を(' + _COUNT_NUM + r')' + re.escape(wrong)
                match = re.search(pattern, user_input)
                if not match:
                    continue
                number = match.group(1)
                fixes = '」か「'.join(f'{number}{s}' for s in suggested)
                return (f'💡 Feedback:\n- ❌ "{number}{wrong}" → ✅ '
                        f'"{number}{suggested[0]}" '
                        f'({reason}。「{fixes}」と言います)')
    return feedback


def _ti_inflect(text: str, offset: int, hit: str, target_stems, wrong_cite: str,
                right_cite: str):
    """Quote the learner's own inflection back, not a dictionary form.

    The learner writes 「電気をつきました」; quoting 「をつきます → をつけます」 at
    them is a citation form they did not use and cannot copy. Splicing the
    correct stem onto their own ending gives 「をつきました → をつけました」, which
    is the sentence they meant and — since the repeat drill asks them to retype
    the ✅ text — the thing they should be practising.

    Falls back to the citation pair when the ending cannot be read, so a shape
    this does not understand degrades to the old behaviour rather than
    producing something wrong.
    """
    ending = ''
    for stop in ('。', '、', '！', '？', '\n'):
        cut = text.find(stop, offset + len(hit))
        if cut != -1:
            ending = text[offset + len(hit):cut]
            break
    else:
        ending = text[offset + len(hit):]
    if not ending or len(ending) > 8:
        return wrong_cite, right_cite
    # The ren'youkei stem is listed first in each tuple and is the one an
    # ending attaches to; the dictionary form takes no ending.
    replacement = target_stems[0]
    return f'{hit}{ending}', f'{replacement}{ending}'


def apply_transitivity_net(feedback: str, user_input: str, language: str) -> str:
    """Catch を+intransitive and inanimate-が+transitive, the two shapes the
    model calls natural. Only ever overturns a clean verdict."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    for intrans, trans, intrans_cite, trans_cite in _TI_PAIRS:
        # Rule A: を + intransitive. Unambiguous — an intransitive verb takes no
        # object. (Motion verbs take を for a path, but none are in this table.)
        idx = user_input.find('を')
        if idx != -1:
            hit = _ti_lookup(user_input, intrans, idx + 1)
            if hit:
                wrong, right = _ti_inflect(user_input, idx + 1, hit, trans,
                                           intrans_cite, trans_cite)
                return (f'💡 Feedback:\n- ❌ "を{wrong}" → ✅ "を{right}" '
                        f'(「を」を使うときは他動詞の「{right}」になります)')

        # Rule B: inanimate patient + が + transitive.
        for patient in _TI_PATIENTS:
            marker = patient + 'が'
            pos = user_input.find(marker)
            if pos == -1:
                continue
            hit = _ti_lookup(user_input, trans, pos + len(marker))
            if hit:
                wrong, right = _ti_inflect(user_input, pos + len(marker), hit,
                                           intrans, trans_cite, intrans_cite)
                return (f'💡 Feedback:\n- ❌ "{patient}が{wrong}" → ✅ '
                        f'"{patient}が{right}" '
                        f'(「{patient}」が主語のときは自動詞の「{right}」を使います)')
    return feedback


# People. Enumerated for the same reason _TI_PATIENTS enumerates inanimate
# patients: the rules below turn on whether the noun is the verb's HUMAN
# partner, and nothing in the text tells us that. 「意味を質問しました」 is
# correct Japanese — を marks the content questioned — so a rule keyed on the
# verb alone would flag it. Keyed on a person, 「先生を質問しました」 is
# unambiguous. Anything not listed is left to the model.
_JA_PERSON_NOUNS = (
    '先生', '友達', '友だち', '母', '父', 'お母さん', 'お父さん', '兄', '姉',
    '弟', '妹', '両親', '家族', '彼', '彼女', '上司', '部長', '課長', '社長',
    '同僚', '先輩', '後輩', '店員', '医者', '看護師', 'お客さん', 'お客様',
    '担当者', '日本人', '外国人', '子供', '子ども', '息子', '娘', '奥さん',
    'ご主人', '主人', '妻', '夫', '友人', '知り合い', '警察官', '運転手',
)

# Suru-verbs whose human partner is marked に, never を.
_NI_PARTNER_SURU = {
    '質問': '「質問する」相手は「に」で示します',
    '電話': '「電話する」相手は「に」で示します',
    '連絡': '「連絡する」相手は「に」で示します',
    '相談': '「相談する」相手は「に」で示します',
    '挨拶': '「挨拶する」相手は「に」で示します',
    'あいさつ': '「あいさつする」相手は「に」で示します',
    '返事': '「返事する」相手は「に」で示します',
    '報告': '「報告する」相手は「に」で示します',
}

# Suru-verbs whose human partner is marked と, never に — a reciprocal action
# needs a co-participant, not a target.
_TO_PARTNER_SURU = {
    '結婚': '「結婚する」相手は「と」で示します',
    '離婚': '「離婚する」相手は「と」で示します',
    '喧嘩': '「喧嘩する」相手は「と」で示します',
    'けんか': '「けんかする」相手は「と」で示します',
    '約束': '「約束する」相手は「と」で示します',
}

# The suru ending is REQUIRED, not optional: it is what keeps the noun reading
# of these words out. 「彼女に結婚を申し込みました」 puts 結婚 straight after に
# and is correct; demanding し/する behind it leaves that sentence alone.
_SURU_TAIL = ('(?:し(?:ました|ませんでした|ましょう|まして|ません|ます|たい|たら|'
              'なかった|ない|よう|た|て)?|する|すれば|される)')

_NI_PARTNER_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_JA_PERSON_NOUNS) + ')を'
    '(?P<verb>' + '|'.join(_NI_PARTNER_SURU) + ')(?P<tail>' + _SURU_TAIL + ')')

_TO_PARTNER_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_JA_PERSON_NOUNS) + ')に'
    '(?P<verb>' + '|'.join(_TO_PARTNER_SURU) + ')(?P<tail>' + _SURU_TAIL + ')')

# 住む and 勤める locate a person rather than an action, so they take に. 「東京
# で住んでいます」 is wrong whatever the place is, which is why this rule needs
# no place list — unlike the で rule below, where the verb decides nothing.
# 住 must be followed by its own okurigana so 住宅/住所 do not match.
# The noun is a run of kanji/katakana/latin rather than "anything but a
# particle": a hiragana-tolerant class swallowed 「三年前から東京」 whole and
# quoted the adverbial back at the learner along with the fix.
_NI_RESIDENCE_ERROR = re.compile(
    '(?P<noun>[一-龥ァ-ヶーA-Za-z]{1,12})で'
    '(?P<stem>住(?:んでいます|んでいる|んでます|んでいた|んだ|んで|みます|みました|む|み)'
    '|勤め(?:ています|ている|ます|ました|て|る))')

# Places. Needed here because the verb cannot settle this one: 図書館に行く is
# correct and 図書館に勉強する is not, so the rule has to see both a place and
# an action performed there.
_JA_PLACE_NOUNS = (
    '図書館', '図書室', '学校', '大学', '教室', '会社', '事務所', '公園',
    'レストラン', 'カフェ', '喫茶店', '食堂', '空港', '病院', '銀行',
    '郵便局', '本屋', 'スーパー', 'コンビニ', 'ホテル', '台所', '教会',
    '工場', '会議室', '体育館', 'プール', '図書館前', '公民館', '自習室',
)

# Verbs naming an action PERFORMED at a place, which takes で. Existence
# (いる/ある/住む) and arrival (行く/来る/着く/入る) take に and are absent by
# construction. Finite and te- forms are listed rather than bare ren'youkei
# because a bare stem opens compounds that take に legitimately: 買い would
# match 「店に買い物に行きました」, where に is the destination of 行く.
_DE_ACTION_SURU = ('勉強', '練習', '仕事', '食事', '会議', '掃除')
_DE_ACTION_STEMS = (
    '働きました', '働きます', '働いて', '働き', '働く',
    '食べました', '食べます', '食べた', '食べて', '食べる',
    '飲みました', '飲みます', '飲んだ', '飲んで', '飲む',
    '読みました', '読みます', '読んだ', '読んで', '読む',
    '書きました', '書きます', '書いた', '書いて', '書く',
    '買いました', '買います', '買った', '買って', '買う',
    '待ちました', '待ちます', '待った', '待って', '待つ',
    '遊びました', '遊びます', '遊んだ', '遊んで', '遊ぶ',
)

_DE_ACTION_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_JA_PLACE_NOUNS) + ')に'
    '(?P<stem>(?:' + '|'.join(_DE_ACTION_SURU) + ')' + _SURU_TAIL
    + '|' + '|'.join(_DE_ACTION_STEMS) + ')')


def _quote_through(user_input: str, match, replacement: str) -> tuple:
    """Quote the learner's own words from the noun through the verb.

    Quoting the bare particle (「先生を」 → 「先生に」) names the fix but not the
    sentence: the repeat drill asks the learner to retype the ✅ text, and a
    two-character fragment is not something to retype. Spanning the verb gives
    them the clause they actually meant.
    """
    return user_input[match.start():match.end()], replacement


def apply_particle_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a particle the verb, not the meaning, fixes.

    Five shapes, all of them classes the model calls natural: を on a に-taking
    verb's target (会う/乗る, and the suru-verbs whose partner is a person),
    に where a reciprocal verb needs と, に where an action at a place needs で,
    and で where 住む/勤める need に.
    """
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    match = _NI_PARTICLE_ERROR.search(user_input)
    if match:
        noun = match.group('noun')
        reason = _NI_TARGET_VERBS[match.group('stem')[0]]
        return f'💡 Feedback:\n- ❌ "{noun}を" → ✅ "{noun}に" ({reason})'

    for pattern, table, wrong_particle, right_particle in (
        (_NI_PARTNER_ERROR, _NI_PARTNER_SURU, 'を', 'に'),
        (_TO_PARTNER_ERROR, _TO_PARTNER_SURU, 'に', 'と'),
    ):
        match = pattern.search(user_input)
        if not match:
            continue
        noun, verb, tail = match.group('noun'), match.group('verb'), match.group('tail')
        wrong, right = _quote_through(
            user_input, match, f'{noun}{right_particle}{verb}{tail}')
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'({table[verb]})')

    match = _DE_ACTION_ERROR.search(user_input)
    if match:
        noun, stem = match.group('noun'), match.group('stem')
        wrong, right = _quote_through(user_input, match, f'{noun}で{stem}')
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(動作を行う場所は「で」で示します)')

    match = _NI_RESIDENCE_ERROR.search(user_input)
    if match:
        noun, stem = match.group('noun'), match.group('stem')
        wrong, right = _quote_through(user_input, match, f'{noun}に{stem}')
        return (f'💡 Feedback:\n- ❌ "{wrong}" → ✅ "{right}" '
                f'(「住む」「勤める」の場所は「に」で示します)')

    return feedback


# Godan verbs whose te-form takes an euphonic change (音便). A learner who
# forms the te-form by analogy with ichidan verbs (食べ→食べて) writes 読みて for
# 読んで, and the model calls it natural.
#
# す-godan verbs are absent BY CONSTRUCTION, not by oversight: for those the
# ren'youkei + て IS the correct te-form (話し→話して, 出し→出して), so listing
# one would flag correct Japanese as an error.
# Values are the whole correct te-form, not a stem: む/ぶ/ぬ take んで and く
# takes いて, but ぐ takes い*で* — 泳ぎて is 泳いで, not 泳いて — so deriving the
# ending from the stem's last kana would get the ぐ verbs wrong.
_TE_ONBIN = {
    '読み': '読んで', '飲み': '飲んで', '休み': '休んで', '進み': '進んで',
    '住み': '住んで', '呼び': '呼んで', '遊び': '遊んで', '運び': '運んで',
    '選び': '選んで', '喜び': '喜んで', '死に': '死んで',
    '書き': '書いて', '聞き': '聞いて', '歩き': '歩いて', '働き': '働いて',
    '置き': '置いて',
    '泳ぎ': '泳いで', '急ぎ': '急いで', '脱ぎ': '脱いで',
    '買い': '買って', '会い': '会って', '使い': '使って', '払い': '払って',
    '習い': '習って',
    '待ち': '待って', '持ち': '持って', '立ち': '立って', '勝ち': '勝って',
    '取り': '取って', '作り': '作って', '売り': '売って', '帰り': '帰って',
    '走り': '走って', '座り': '座って', '送り': '送って', '降り': '降って',
    '曲がり': '曲がって', '行き': '行って',
}
_TE_ONBIN_ERROR = re.compile('(' + '|'.join(_TE_ONBIN) + ')て')

# たい is an i-adjective, so its past is たかった — not たいでした, which is the
# shape a learner produces by treating たい as a noun. ない behaves the same way.
# Both are safe without any word list: no na-adjective and no noun ends in
# たい or ない, so the ending alone settles it.
_I_ADJ_PAST_ERROR = re.compile('(?P<stem>[^\\s、。「」『』！？!?]{0,10}?)(?P<adj>たい|ない)でした')

# The wider i-adjective class DOES need a list, because な-adjectives ending in
# the same kana (きれいでした, 嫌いでした, 有名でした) are correct and are
# indistinguishable from the ending alone.
_I_ADJECTIVES = (
    '楽しい', '嬉しい', 'うれしい', '悲しい', '面白い', 'おもしろい', '忙しい',
    '寒い', '暑い', '熱い', '冷たい', '高い', '安い', '良い', 'よい', '悪い',
    '難しい', '易しい', '新しい', '古い', '大きい', '小さい', '近い', '遠い',
    '早い', '速い', '遅い', '強い', '弱い', '長い', '短い', '広い', '狭い',
    '多い', '少ない', '怖い', '痛い', 'かわいい', 'すごい', '欲しい', 'ほしい',
    'おいしい', '美味しい', '美しい', '優しい', '厳しい', '眠い',
)
_I_ADJ_LIST_ERROR = re.compile('(?P<adj>' + '|'.join(_I_ADJECTIVES) + ')でした')


def apply_conjugation_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a mis-formed te-form or i-adjective past.

    Both are regular morphology the model does not enforce: it accepted 読みて
    and 行きたいでした as natural. Only ever overturns a clean verdict.
    """
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    match = _TE_ONBIN_ERROR.search(user_input)
    if match:
        stem = match.group(1)
        return (f'💡 Feedback:\n- ❌ "{stem}て" → ✅ "{_TE_ONBIN[stem]}" '
                f'(五段動詞のテ形は音便の形になります)')

    match = _I_ADJ_PAST_ERROR.search(user_input)
    if match:
        stem, adj = match.group('stem'), match.group('adj')
        past = 'たかったです' if adj == 'たい' else 'なかったです'
        return (f'💡 Feedback:\n- ❌ "{stem}{adj}でした" → ✅ "{stem}{past}" '
                f'(「{adj}」はい形容詞なので、過去形は「{past}」になります)')

    match = _I_ADJ_LIST_ERROR.search(user_input)
    if match:
        adj = match.group('adj')
        past = adj[:-1] + 'かったです'
        return (f'💡 Feedback:\n- ❌ "{adj}でした" → ✅ "{past}" '
                f'(い形容詞の過去形は「かったです」になります)')

    return feedback


# Address terms that name someone senior to the learner. A sentence that opens
# by calling one of these and then drops into plain form is a register clash
# the learner can see and fix — and, unlike the situational rules, it needs no
# scenario: the learner named the listener themselves.
_JA_SUPERIOR_ADDRESS = (
    '先生', '部長', '課長', '社長', '店長', '館長', '主任', '先輩',
    'お客様', 'お客さん', '社長さん', '部長さん',
)
_SUPERIOR_VOCATIVE = re.compile(
    '^(?:' + '|'.join(_JA_SUPERIOR_ADDRESS) + ')[、,]')

# Pronouns a learner should not aim at someone senior.
_CASUAL_PRONOUNS = (('俺', '私'), ('おれ', '私'), ('お前', 'あなた'), ('おまえ', 'あなた'))

# Politeness anywhere in the sentence means the register is already chosen, so
# the plain-form rule below must not fire. Checked over the whole utterance
# rather than the ending, because 「先生、明日来ますか」 is polite at the end and
# 「先生、明日来るか、教えてください」 is polite only at the end.
_JA_POLITE_MARKERS = ('ます', 'です', 'ください', 'ましょう', 'でしょう', 'ございま')

# Plain sentence-final forms and their polite twins. Enumerated, because ichidan
# and godan take different endings and the irregulars (来る/する) take neither.
_PLAIN_TO_POLITE = {
    '来る': '来ます', 'くる': 'きます', 'する': 'します', 'ある': 'あります',
    'いる': 'います', '行く': '行きます', '見る': '見ます', '食べる': '食べます',
    '飲む': '飲みます', '書く': '書きます', '読む': '読みます', '買う': '買います',
    '待つ': '待ちます', '帰る': '帰ります', '言う': '言います', '聞く': '聞きます',
    '出る': '出ます', '入る': '入ります', '休む': '休みます', '使う': '使います',
    '持つ': '持ちます', '取る': '取ります', '作る': '作ります', '分かる': '分かります',
    '教える': '教えます', '始める': '始めます', '終わる': '終わります',
}
_PLAIN_ENDING = re.compile(
    '(?P<verb>' + '|'.join(_PLAIN_TO_POLITE) + ')(?P<q>か)?[。．.！？!?]?\\s*$')


def apply_register_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict when the learner addresses someone senior and
    then speaks to them in plain form or with a casual pronoun.

    Narrower than the situational rules on purpose: it fires only when the
    learner's own sentence names the listener, so it needs no scenario and
    cannot mistake an equal for a superior.
    """
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    if not _SUPERIOR_VOCATIVE.match(user_input.strip()):
        return feedback

    for casual, polite in _CASUAL_PRONOUNS:
        if casual in user_input:
            return (f'💡 Feedback:\n- ❌ "{casual}" → ✅ "{polite}" '
                    f'(目上の人には「{polite}」を使います)')

    if any(marker in user_input for marker in _JA_POLITE_MARKERS):
        return feedback
    match = _PLAIN_ENDING.search(user_input.strip())
    if match:
        verb, question = match.group('verb'), match.group('q') or ''
        polite = _PLAIN_TO_POLITE[verb]
        return (f'💡 Feedback:\n- ❌ "{verb}{question}" → ✅ "{polite}{question}" '
                f'(目上の人には「ます」の形で話します)')

    return feedback


# A degree adverb sitting AFTER the predicate is stranded — Japanese puts it in
# front. The predicate ending is what makes this safe to check: nothing correct
# follows です/ます with a bare degree adverb and no comma.
_DEGREE_ADVERBS = ('とても', 'すごく', '本当に', 'ほんとうに', 'かなり', '非常に',
                   'ちょっと', '少し', 'たくさん', 'よく')
# `pred` excludes the case particles as well as the sentence punctuation, so the
# quote starts at the predicate and not at the top of the clause: without that
# 「私はコーヒーが好きですとても」 was quoted back whole and "fixed" to
# 「とても私はコーヒーが好きです」, which moves the adverb to the wrong place.
_STRANDED_ADVERB = re.compile(
    '(?P<pred>[^\\s、。「」『』！？!?がはをにでともへの]{1,10})(?P<cop>でした|ました|です|ます)'
    '(?P<adv>' + '|'.join(_DEGREE_ADVERBS) + ')')

# たくさん modifying a noun needs の. Restricted to a が-marked subject, where
# the adverbial reading is not available: 「たくさん本を読む」 is ordinary spoken
# Japanese and must not be touched, but 「たくさん人がいます」 has たくさん sitting
# on a subject noun and wants 「たくさんの人」.
_TAKUSAN_NO = re.compile('たくさん(?P<noun>[一-龥ァ-ヶー]{1,6})(?=が)')


def apply_word_order_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict on a stranded degree adverb or a bare
    たくさん modifying a subject noun."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback

    match = _STRANDED_ADVERB.search(user_input)
    if match:
        pred, cop, adv = match.group('pred'), match.group('cop'), match.group('adv')
        return (f'💡 Feedback:\n- ❌ "{pred}{cop}{adv}" → ✅ "{adv}{pred}{cop}" '
                f'(程度を表す副詞は述語の前に置きます)')

    match = _TAKUSAN_NO.search(user_input)
    if match:
        noun = match.group('noun')
        return (f'💡 Feedback:\n- ❌ "たくさん{noun}" → ✅ "たくさんの{noun}" '
                f'(「たくさん」が名詞を修飾するときは「の」が必要です)')

    return feedback


# Things that are drunk, not eaten. A closed collocation the model does not
# enforce: it called 「薬を食べました」 natural. Kept to the cases where 飲む is
# the only option — スープ is deliberately absent, since 「スープを食べる」 is
# acceptable for a chunky soup and this net must never correct correct Japanese.
_DRINK_NOUNS = ('薬', '水', 'お茶', 'コーヒー', '紅茶', 'ジュース', 'ビール',
                'ワイン', '牛乳', 'ミルク', 'お酒', '日本酒')

# The learner's own inflection, spliced onto the right verb — the same choice
# _ti_inflect makes, and for the same reason: the repeat drill asks them to
# retype the ✅ text.
_EAT_TO_DRINK = {
    '食べました': '飲みました', '食べます': '飲みます', '食べた': '飲んだ',
    '食べる': '飲む', '食べて': '飲んで', '食べません': '飲みません',
    '食べたい': '飲みたい', '食べなかった': '飲まなかった', '食べよう': '飲もう',
}
_EAT_DRINK_ERROR = re.compile(
    '(?P<noun>' + '|'.join(_DRINK_NOUNS) + ')を'
    '(?P<verb>' + '|'.join(sorted(_EAT_TO_DRINK, key=len, reverse=True)) + ')')


def apply_collocation_net(feedback: str, user_input: str, language: str) -> str:
    """Overturn a clean verdict when a drink or a medicine is 食べる'd."""
    if language != 'Japanese' or not is_clean_verdict(feedback, language):
        return feedback
    match = _EAT_DRINK_ERROR.search(user_input)
    if not match:
        return feedback
    noun, verb = match.group('noun'), match.group('verb')
    right = _EAT_TO_DRINK[verb]
    return (f'💡 Feedback:\n- ❌ "{noun}を{verb}" → ✅ "{noun}を{right}" '
            f'(「{noun}」は「飲む」を使います)')


# Saying you are late and offering no apology is the one situational miss that
# does NOT need to know who the listener is: the apology is owed to anyone kept
# waiting. COACH_SITUATION already asks for it and the model does not produce
# it — 61 and 62 scored 0/5, in both languages, with the situation in the
# prompt. So it is netted, in both languages, and gated on `situational`
# because a sentence with no situation around it has nobody to apologise to.
_LATE_MARKERS = {
    'Japanese': re.compile('遅れ(?:ま|そう|る)|遅刻|遅くなり'),
    'English': re.compile(r"\b(?:i|we)(?:'m| am| will be|'ll be| are)\b[^.!?]{0,40}?\blate\b",
                          re.IGNORECASE),
}
_APOLOGY_MARKERS = {
    'Japanese': ('すみません', 'すいません', '申し訳', 'ごめん', '恐れ入り', '失礼'),
    'English': ('sorry', 'apolog', 'forgive'),
}
# The English marker is subject-anchored — it requires "I/we ... late" — but the
# Japanese one was not, so 「電車が遅れました。」 was read as the learner being
# late and the net told them to apologise for the train. That is the failure the
# whole net design exists to avoid: a net may only ever overturn a CLEAN verdict,
# and here it overturned one on correct Japanese. Worse, `promote_fit` is on in
# the CLI, so it landed as a Feedback bullet and `run_correction_drill` — a
# `while True` with no skip — made the learner retype an apology they did not
# owe, with Ctrl-D the only way out.
#
# Japanese marks the subject rather than fixing it by position, so the guard is
# to look for an explicit `Xが` / `Xは` inside the same clause as the late verb.
# A third-party subject there means the lateness is not the learner's. An absent
# subject means the speaker, which is the ordinary Japanese reading — 「予約の
# 時間に三十分遅れました」 (fixture 61) has no subject and must still fire.
_JA_FIRST_PERSON = ('私', 'わたし', 'わたくし', '僕', 'ぼく', '俺', 'おれ', '自分', 'うち')
_JA_SUBJECT = re.compile(r'([^\s、。！？]{1,12}?)[がは]')


def _ja_subject_is_someone_else(clause: str, late) -> bool:
    """True when the clause names an explicit subject that is not the speaker."""
    hit = late.search(clause)
    if not hit:
        return False
    for m in _JA_SUBJECT.finditer(clause[:hit.start()]):
        subject = m.group(1)
        if not any(p in subject for p in _JA_FIRST_PERSON):
            return True
    return False


_APOLOGY_FIX = {
    'Japanese': ('すみません、', '遅れることを伝えるときは、まずお詫びの言葉を添えます'),
    'English': ("I'm sorry — ", 'when you tell someone you are late, lead with an apology'),
}
_SENTENCE_SPLIT = re.compile('(?<=[.!?。．！？])\\s*')


def apply_apology_net(feedback: str, user_input: str, language: str,
                      situational: bool = False) -> str:
    """Overturn a clean verdict when the learner reports being late and
    apologises for nothing. Both languages."""
    if not situational or not is_clean_verdict(feedback, language):
        return feedback
    late = _LATE_MARKERS.get(language)
    if late is None or not late.search(user_input):
        return feedback
    if any(marker in user_input.lower() for marker in _APOLOGY_MARKERS[language]):
        return feedback

    prefix, reason = _APOLOGY_FIX[language]
    said = next((s for s in _SENTENCE_SPLIT.split(user_input.strip())
                 if late.search(s)), user_input.strip())
    said = said.strip()
    if language == 'Japanese' and _ja_subject_is_someone_else(said, late):
        return feedback
    return (f'💡 Feedback:\n- ❌ "{said}" → ✅ "{prefix}{said}" ({reason})')


# "Perfectly natural!" is the canonical clean verdict everywhere inside the
# pipeline — COACH_SYS asks for it, filter_coach_output collapses to it, and
# apply_particle_net keys on it. Only the learner-facing text is localized, and
# only at the very end, so the prompt itself never changes: removing a single
# worked example from COACH_SYS moved four unrelated cases and cost 12
# iterations, so prompt edits are not a cheap lever here.
#
# The Japanese wording is deliberately weaker than the English. The coach misses
# roughly three quarters of real Japanese errors (OPEN-10), and answering
# 「完璧です」 to a sentence that is in fact wrong does not merely fail to help —
# it confirms the mistake and the learner practises it. Reporting what the
# checker actually did ("I did not find anything to fix") is honest at this
# accuracy; a verdict on the sentence would not be.
CLEAN_SENTINEL = 'Perfectly natural!'
CLEAN_MARKERS = {'Japanese': '特に直すところは見つかりませんでした。'}


def clean_marker(language: str) -> str:
    """The clean verdict as the learner should see it in their language."""
    return CLEAN_MARKERS.get(language, CLEAN_SENTINEL)


def is_clean_verdict(feedback: str, language: str) -> bool:
    """True for a clean verdict in either the internal or the localized form."""
    return (CLEAN_SENTINEL.lower() in feedback.lower()
            or clean_marker(language) in feedback)


def localize_clean_verdict(feedback: str, language: str) -> str:
    """Swap the internal sentinel for the learner's language. Must run last."""
    marker = clean_marker(language)
    if marker == CLEAN_SENTINEL:
        return feedback
    return feedback.replace(CLEAN_SENTINEL, marker)


_CORRECTION_BULLET = re.compile('❌\\s*"(.*?)"\\s*→\\s*✅\\s*"(.*?)"')


def correction_targets(feedback: str) -> list:
    """The ✅ forms the learner should retype, in bullet order.

    Feedback bullets only: a Level up suggestion is optional polish on an
    already-correct sentence, not something the learner got wrong.
    """
    feedback_block = re.split('⬆️\\s*Level up:', feedback)[0]
    targets = []
    for (_said, better) in _CORRECTION_BULLET.findall(feedback_block):
        better = better.strip()
        if better and better not in targets:
            targets.append(better)
    return targets


def coach_feedback(raw: str, user_input: str, language: str,
                   promote_fit: bool = False) -> str:
    """The exact text the learner sees: filter the model, net what it missed,
    then localize the clean verdict — in that order, since the net keys on the
    English sentinel.

    `promote_fit` moves a politeness/register suggestion out of Level up and
    into Feedback, so it counts as a correction and the repeat drill picks it
    up. It is on only when the coach was given a situation to judge against,
    since without one there is no situation for a register to mismatch.
    """
    netted = apply_particle_net(
        filter_coach_output(raw, promote_fit, user_input), user_input, language)
    netted = apply_transitivity_net(netted, user_input, language)
    netted = apply_counter_net(netted, user_input, language)
    netted = apply_conjugation_net(netted, user_input, language)
    netted = apply_register_net(netted, user_input, language)
    netted = apply_word_order_net(netted, user_input, language)
    netted = apply_collocation_net(netted, user_input, language)
    netted = apply_apology_net(netted, user_input, language, situational=promote_fit)
    netted = localize_clean_verdict(netted, language)
    # Every other Japanese-output surface in this project has leaked simplified
    # Chinese at some point — the actor at 23-30%, translated hints at 12 of 12
    # — and each was found late because find_wrong_script existed and simply was
    # not called on that path. Coach feedback measured clean over 14 Japanese
    # cases, so this is a guard against a recurrence rather than a live fix
    # (OPEN-22). Falling back to the clean verdict is the safe direction: a
    # learner shown nothing is better off than one shown a correction in a
    # language they are not studying, and the nets have already had their say.
    if find_wrong_script(netted, language):
        return localize_clean_verdict('💡 Feedback: Perfectly natural!', language)
    return netted


def call_coach(user_input: str, language: str, situation: Optional[str] = None) -> str:
    """Get language feedback on the learner's message.

    `situation` is optional: without it the coach judges language only, which is
    what every caller that has no scenario to hand should get.
    """
    system = coach_system(language, situation)
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user_input}]
    response = _llm_chat(messages=messages, options=COACH_OPTS, cache_key='coach')
    raw = response['message']['content']
    raw = strip_think_tags(raw).strip()
    return coach_feedback(raw, user_input, language, promote_fit=bool(situation))