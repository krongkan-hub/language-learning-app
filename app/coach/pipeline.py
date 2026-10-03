"""Assembling one coach turn: filter, then every net, then the guards."""
import re
from typing import Optional

from ..llm import _llm_chat, strip_think_tags, find_wrong_script
from .filters import _normalize_phrase, filter_coach_output
from .nets import (apply_apology_net, apply_article_net, apply_collocation_net,
                   apply_conjugation_net, apply_counter_net,
                   apply_existence_net, apply_particle_net, apply_plural_net,
                   apply_register_net, apply_spelling_net,
                   apply_transitivity_net,
                   apply_verbform_net, apply_word_order_net, apply_ditransitive_net)
from .prompt import coach_system, COACH_OPTS
from .reasons import explain_particle_changes
from .reorder import drop_stylistic_reorder
from .verdict import (LEVEL_UP_MARKER, is_clean_verdict, localize_clean_verdict,
                      _CORRECTION_BULLET, _drop_foreign_reasons)


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
    netted = apply_existence_net(netted, user_input, language)
    netted = apply_verbform_net(netted, user_input, language)
    netted = apply_plural_net(netted, user_input, language)
    netted = apply_article_net(netted, user_input, language)
    netted = apply_ditransitive_net(netted, user_input, language)
    netted = apply_spelling_net(netted, user_input, language)
    netted = apply_apology_net(netted, user_input, language, situational=promote_fit)
    netted = _add_what_the_model_missed(netted, user_input, language)
    # After the nets, because a net's own reorder (a stranded degree adverb
    # sits AFTER the predicate) is not predicate-final and survives this.
    netted = drop_stylistic_reorder(netted, language)
    netted = explain_particle_changes(netted, language)
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
        # All-or-nothing used to mean a CORRECT correction was thrown away for
        # the language of its footnote. Seen live:
        #
        #   ❌ "行きます東京へ" → ✅ "東京へ行きます" (方位词放在句末更自然)
        #
        # The fix is right and in Japanese; only the bracketed reason is
        # Chinese. Dropping the reason keeps what the learner needs — and the
        # drill, which retypes the ✅ side, never used the reason anyway.
        trimmed = _drop_foreign_reasons(netted, language)
        if trimmed and not find_wrong_script(trimmed, language):
            return trimmed
        return localize_clean_verdict('💡 Feedback: Perfectly natural!', language)
    return netted


# English nets precise enough to speak up even beside the model's own
# corrections. Every net only overturns a CLEAN verdict, so a sentence with
# three errors was corrected once: playtest 2026-09-29, "Yesterday I go to the
# shop and buyed two bottle of milk" came back with "I go" only — each of these
# three finds one of the other errors on its own.
_ADDITIVE_NETS = {
    'English': ('apply_verbform_net', 'apply_plural_net', 'apply_spelling_net'),
    # 窓が閉めました。りんごを三本買いました。 — transitivity and counter each
    # find one of the two; the particle net covers the を/に/で/が shapes.
    'Japanese': ('apply_particle_net', 'apply_transitivity_net', 'apply_counter_net'),
}


def _add_what_the_model_missed(feedback: str, user_input: str, language: str) -> str:
    """Append a net's correction the model's bullets do not already cover.

    Only on a feedback that already corrects something (a clean verdict went
    through the nets above, unchanged). A net bullet is skipped when its
    quoted span overlaps a quoted span already there, so a model rewrite of
    the whole clause is never doubled by a net's piece of it.
    """
    if language not in _ADDITIVE_NETS or is_clean_verdict(feedback, language):
        return feedback
    head, _, level_up = _split_level_up(feedback)
    quoted = [q.lower() for q, _ in _CORRECTION_BULLET.findall(head)]
    added = []
    for name in _ADDITIVE_NETS[language]:
        out = globals()[name](_CLEAN, user_input, language)
        for line in out.split('\n'):
            pair = _CORRECTION_BULLET.search(line)
            if not pair:
                continue
            q = pair.group(1).lower()
            if any(q in e or e in q for e in quoted):
                continue
            quoted.append(q)
            added.append(line.rstrip())
    if not added:
        return feedback
    merged = head.rstrip() + '\n' + '\n'.join(added)
    return merged + (f'\n\n⬆️ Level up:\n{level_up}' if level_up else '')


_CLEAN = '💡 Feedback: Perfectly natural!'


def _coach_pass(user_input: str, language: str, situation: Optional[str]) -> str:
    """One model call and the whole filter/net/guard chain over its output."""
    system = coach_system(language, situation)
    messages = [{'role': 'system', 'content': system},
                {'role': 'user', 'content': user_input}]
    # Its own cache per pass: the situation pass's prompt is the grammar
    # pass's plus ~440 tokens, and sharing one entry re-read those tokens on
    # every turn (measured: 442 tokens to process vs 17 with its own entry).
    response = _llm_chat(messages=messages, options=COACH_OPTS,
                         cache_key='coach_situation' if situation else 'coach')
    raw = strip_think_tags(response['message']['content']).strip()
    return coach_feedback(raw, user_input, language, promote_fit=bool(situation))


# Clause boundaries an English learner's sentence actually has. Deliberately
# coarse: a wider pattern that also cut at `that`, `which`, `as soon as` and
# `before` was measured and scored identically — 18/27 either way — while
# making more model calls and more subjectless fragments, so the extra reach
# bought nothing. Recorded in OPEN-48 rather than shipped.
_EN_CLAUSE_SPLIT = re.compile(
    r',?\s+(?=\b(?:and|but|so|because|then|although|though|while)\b)|,\s+',
    re.IGNORECASE)

# Below this, splitting has nothing to buy: short sentences score 27/27 whole.
_SPLIT_ABOVE_WORDS = 12

# Japanese has no spaces to count, so length is characters. The short arm of
# eval_jalength.py is at most 16 characters and scores 36/36 whole.
_JA_SPLIT_ABOVE_CHARS = 20


def _grammar_units(user_input: str, language: str) -> list:
    """The pieces the grammar pass should judge separately.

    The same error scores 27/27 alone in a short sentence and 12/27 unchanged
    inside a long one, with 15 of those misses called "Perfectly natural!"
    Cutting the long sentence at its clause boundaries and coaching each piece
    takes that to 18/27 with the clean arm untouched at 18/18 — the same lever
    that took OPEN-40's translations from 16% to 8% by asking one line at a
    time. See BACKLOG OPEN-48.

    Japanese is cut at 、 only. Measured by eval_jalength.py: the classes a
    net covers hold at full marks in a long sentence, since a net does not
    read length, but the one class left to the model alone — な-adjective +
    の — goes 6/6 short to 0/6 long, the English effect exactly.
    """
    if language == 'Japanese':
        if len(user_input) <= _JA_SPLIT_ABOVE_CHARS:
            return [user_input]
        # A short piece (「昨日」) is joined to the next rather than dropped:
        # every character of the turn must reach some pass.
        parts, carry = [], ''
        for piece in user_input.split('、'):
            piece = carry + piece.strip()
            if len(piece) < 5:
                carry = piece + '、'
                continue
            parts.append(piece)
            carry = ''
        if carry and parts:
            parts[-1] += '、' + carry.rstrip('、')
        return parts or [user_input]
    if language != 'English' or len(user_input.split()) <= _SPLIT_ABOVE_WORDS:
        return [user_input]
    parts = [p.strip(' ,') for p in _EN_CLAUSE_SPLIT.split(user_input)]
    parts = [p for p in parts if len(p.split()) >= 3]
    return parts or [user_input]


def _key(phrase: str) -> str:
    return _normalize_phrase(phrase).lower()


def _inside_a_fix(said: str, fixed: set) -> bool:
    # Three words or more: a quoted "a" or "the" sits inside most rewrites
    # and is still a real, separate correction.
    return any(said == f or (len(said.split()) >= 3 and said in f) for f in fixed)


def _merge_many(blocks: list, language: str) -> str:
    """One feedback block from several passes, bullets in pass order.

    Every pass runs the nets, so the same deterministic correction can come
    back more than once. Bullets are kept one per QUOTED span: the grammar
    pass and the situation pass both rewrite a short sentence whole, each in
    its own words, and a playtest turn came back with two near-identical
    rewrites of one sentence — then a third bullet "correcting" the coach's
    own rewrite, text the learner never typed. The drill made the learner
    retype all three. A bullet is dropped when its ❌ side was already quoted,
    or is (part of) an earlier bullet's ✅ side.

    The first pass's Level up section, if any, is kept at the end. Until
    2026-09-30 every Level up was cut here — a clean block was skipped whole
    and the rest were split at the marker — so no learner had seen one since
    the passes were split (OPEN-47, OPEN-54).
    """
    bullets, quoted, fixed = [], set(), set()
    level_up = ''
    for block in blocks:
        head, _, tail = _split_level_up(block)
        if tail and not level_up:
            level_up = tail
        if is_clean_verdict(block, language):
            continue
        for line in head.split('\n'):
            line = line.rstrip()
            if not line.startswith('-'):
                continue
            pair = _CORRECTION_BULLET.search(line)
            said, better = ((_key(pair.group(1)), _key(pair.group(2)))
                            if pair else (line.strip(), None))
            drop = said in quoted or _inside_a_fix(said, fixed)
            # a dropped rewrite still counts: a later bullet may quote it
            if better:
                fixed.add(better)
            if drop:
                continue
            quoted.add(said)
            bullets.append(line)
    suffix = f'\n\n⬆️ Level up:\n{level_up}' if level_up else ''
    if not bullets:
        return localize_clean_verdict('💡 Feedback: Perfectly natural!', language) + suffix
    return '💡 Feedback:\n' + '\n'.join(bullets) + suffix


def _split_level_up(block: str) -> tuple:
    """(the feedback part, '', the Level up body) — the marker with or
    without the emoji variation selector U+FE0F, which the model drops."""
    parts = LEVEL_UP_MARKER.split(block, maxsplit=1)
    return (parts[0], '', parts[1].strip()) if len(parts) == 2 else (block, '', '')


def call_coach(user_input: str, language: str, situation: Optional[str] = None) -> str:
    """Get language feedback on the learner's message.

    `situation` is optional: without it the coach judges language only, which is
    what every caller that has no scenario to hand should get.

    With one, the work is split across TWO calls rather than one prompt that
    does both jobs. Measured on twelve sentences at three iterations, the
    situation block costs the single-call coach a quarter of its grammar
    recall — 30/36 without it, 21/36 with it, replicated — while the clean arm
    does not move at all, so it is recall lost for nothing. Two rewordings of
    the block recovered 3 of the 9 and no more. Judging grammar in a context
    that never mentions the situation restores the full 30/36, and the
    situation pass still flags register at 6/6, so the feature promote_fit
    depends on is intact. See BACKLOG OPEN-47.
    """
    # At most six clause passes: a turn is a few sentences, and each pass is a
    # model call serialized behind the lock.
    units = _grammar_units(user_input, language)[:6]
    grammar = [_coach_pass(unit, language, None) for unit in units]
    if not situation:
        return _merge_many(grammar, language)
    # Appropriateness reads the whole sentence: a greeting, a thank-you or a
    # register that clashes is a property of the turn, not of a clause.
    grammar.append(_coach_pass(user_input, language, situation))
    return _merge_many(grammar, language)
