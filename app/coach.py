from .llm import _llm_chat, strip_think_tags
from typing import Optional
import re

COACH_OPTS = {'temperature': 0.2, 'max_tokens': 250}
COACH_SYS = 'You are a language coach. The learner is practicing {language}.\n\nAnalyze ONLY the learner\'s most recent message. Everything you write — quotes,\ncorrections, suggestions, and reasons — must be in {language}, with the sole\nexception of the two fixed section labels below, which stay in English.\n\nYOUR STRONGEST BIAS IS TOWARD "Perfectly natural!". Most learner messages are\nalready correct. Your job is NOT to find something to fix in every message — it\nis to catch genuine mistakes and otherwise get out of the way. A correction you\nare not sure about does more harm than good.\n\nAlways begin with the Feedback section:\n\n💡 Feedback:\n- ❌ "[exact quote]" → ✅ "[correction]" (short reason in {language})\n\nRules for Feedback:\n- This section is ONLY for a CLEAR, UNAMBIGUOUS error a teacher would mark\n  wrong: broken grammar (including missing verb inflections, wrong participle\n  forms such as a bare verb after "is/are" e.g. "is prohibit" → "is prohibited",\n  wrong verb form after "to", number/plural agreement e.g. after a number or quantifier a countable noun must be plural "two bottle" → "two bottles", or attaching "だ" to an i-adjective e.g. "欲しいだ" → "欲しいです"; an i-adjective takes "です" for politeness, never "だ"), a real spelling mistake, or a genuinely wrong word —\n  a word a native speaker simply would not use for that meaning in that context\n  (in Japanese, e.g. たくさん to mean "very much" should be とても).\n- The following are NOT errors — never "correct" them: a correct sentence, a\n  valid synonym or equally-natural phrasing (in Japanese, e.g. 何時 vs いつ are\n  both fine — do not swap one for the other; ～から vs ～まで have DIFFERENT\n  meanings, so never switch them; ～で in "ブラックで" is valid manner specification, do not change to ～の), a politeness level that also\n  fits the learner\'s situation, or a stylistic preference.\n- Never change the MEANING of what the learner said. If your "correction" says\n  something different from their sentence, it is wrong — discard it.\n- When you are not certain something is a real error, treat the message as\n  correct.\n- If the grammar, spelling, and word choice are all fine, write EXACTLY this\n  and nothing more (no Feedback bullets, no Level up):\n  💡 Feedback: Perfectly natural!\n- Maximum 2 corrections. Quote their exact words. Keep their pronouns. Every\n  Feedback bullet MUST use the "❌ ... → ✅ ..." shape; if you would write\n  "✅ ... → ✅ ...", the message was correct, so write "Perfectly natural!"\n  instead.\n\nEXAMPLES (copy this behaviour exactly):\nLearner: "ブラックコーヒーをください。"\n💡 Feedback: Perfectly natural!\nLearner: "朝ごはんは何時からですか"\n💡 Feedback: Perfectly natural!\nLearner: "Is it prohibit here?"\n💡 Feedback:\n- ❌ "Is it prohibit" → ✅ "Is it prohibited" (after "is", use the past participle "prohibited")\nLearner: "Can I get two bottle of water, please?"\n💡 Feedback:\n- ❌ "two bottle" → ✅ "two bottles" (after a number, use the plural)\nLearner: "わたし、猫が好きだ、たくさん。"\n💡 Feedback:\n- ❌ "たくさん" → ✅ "とても" ("とても"が程度を表す自然な語です)\nLearner: "コーヒーを一つ欲しいだ、ブラックで。"\n💡 Feedback:\n- ❌ "欲しいだ" → ✅ "欲しいです" (い形容詞に「だ」は付きません)\nLearner: "I want to finding a book."\n💡 Feedback:\n- ❌ "I want to finding" → ✅ "I want to find" (after "to", use the base verb)\n\nAfter Feedback you MAY add a Level up section — but ONLY when the message is\nalready correct AND you have a genuinely better, more natural phrasing a native\nspeaker would clearly prefer:\n\n⬆️ Level up:\n- "[their phrase]" → "[better phrase]" (short reason in {language})\n\nRules for Level up:\n- OMIT this section entirely — write nothing at all after Feedback — when there\n  is no real improvement to offer. Most correct messages need no Level up. Do\n  NOT fill it in just to have something, and NEVER suggest replacing a phrase\n  with the same phrase.\n- NEVER write "Perfectly natural!" and then offer a grammatical fix in Level up.\n  If a correction fixes grammar, spelling, or word form, it is a Feedback bullet.\n  Level up is only for a genuinely better phrasing of an already-grammatical sentence.\n- The suggested phrase must be meaningfully different from and better than the\n  learner\'s own.\n- A phrase may appear in Feedback OR Level up, never in both.\n\nKeep the labels "💡 Feedback:" and "⬆️ Level up:" exactly as written, in\nEnglish. If the learner used a non-{language} word, show the {language}\nequivalent.'

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


def filter_coach_output(raw: str, promote_fit: bool = False) -> str:
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
    netted = apply_particle_net(filter_coach_output(raw, promote_fit), user_input, language)
    netted = apply_transitivity_net(netted, user_input, language)
    netted = apply_counter_net(netted, user_input, language)
    return localize_clean_verdict(netted, language)


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