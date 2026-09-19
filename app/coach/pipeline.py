"""Assembling one coach turn: filter, then every net, then the guards."""
import re
from typing import Optional

from ..llm import _llm_chat, strip_think_tags, find_wrong_script
from .filters import filter_coach_output
from .nets import (apply_apology_net, apply_collocation_net,
                   apply_conjugation_net, apply_counter_net,
                   apply_existence_net, apply_particle_net,
                   apply_register_net, apply_transitivity_net,
                   apply_verbform_net, apply_word_order_net)
from .prompt import coach_system, COACH_OPTS
from .verdict import (is_clean_verdict, localize_clean_verdict,
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


def _coach_pass(user_input: str, language: str, situation: Optional[str]) -> str:
    """One model call and the whole filter/net/guard chain over its output."""
    system = coach_system(language, situation)
    messages = [{'role': 'system', 'content': system},
                {'role': 'user', 'content': user_input}]
    response = _llm_chat(messages=messages, options=COACH_OPTS, cache_key='coach')
    raw = strip_think_tags(response['message']['content']).strip()
    return coach_feedback(raw, user_input, language, promote_fit=bool(situation))


def _merge_passes(grammar: str, fit: str, language: str) -> str:
    """One feedback block from two passes, bullets in grammar-first order.

    Both passes run the nets, so the same deterministic correction can come
    back twice; bullets are deduplicated on the ❌/✅ pair rather than on the
    whole line, since the two passes word their reasons differently.
    """
    bullets, seen = [], set()
    for block in (grammar, fit):
        if is_clean_verdict(block, language):
            continue
        for line in re.split(r'⬆️\s*Level up:', block)[0].split('\n'):
            line = line.rstrip()
            if not line.startswith('-'):
                continue
            pair = _CORRECTION_BULLET.search(line)
            key = pair.groups() if pair else line.strip()
            if key in seen:
                continue
            seen.add(key)
            bullets.append(line)
    if not bullets:
        return localize_clean_verdict('💡 Feedback: Perfectly natural!', language)
    return '💡 Feedback:\n' + '\n'.join(bullets)


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
    if not situation:
        return _coach_pass(user_input, language, None)
    grammar = _coach_pass(user_input, language, None)
    fit = _coach_pass(user_input, language, situation)
    return _merge_passes(grammar, fit, language)
