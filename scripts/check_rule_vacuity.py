#!/usr/bin/env python3
"""Fail if a validation rule is silently vacuous on Japanese.

Six separate bugs of one shape reached production, each passing code review
and a green suite: a rule written and tested in English that quietly does
nothing on the Japanese half of the catalog.

    is_closed_question   matched ASCII '?' and [a-z']+     — 0 of 50 real
                         Japanese questions flagged
    _IDENTIFIER_TOKEN    used \\b, which finds nothing in 予約番号はAB-1234
    has_question         '?' in s, so a Japanese question was dropped and an
                         English line appended on 100% of sampled turns
    judge_deterministic   English target substring-matched against Japanese —
                         401 catalog tasks unwinnable
    _words               [a-z']+, so the trivial-vocab guard never fired
    walk-back rescue     English phrase list, in a prompt that demands the
                         reason be written in the session language

Reviewing harder was not enough; this is the check instead.

Three assertions, in decreasing order of teeth:

1. PARITY — the same utterance in both languages must get the same verdict.
   Catches vacuity AND over-firing, and is what would have caught most of
   the six above.
2. NON-VACUITY — each predicate must return both True and False somewhere in
   the Japanese corpus. A tripwire for a newly added rule nobody wrote a
   twin for. Weaker than it looks: a rule can be non-vacuous here and still
   miss the phrasing the model actually produces, which is exactly how the
   何か hole survived. Treat it as a smoke alarm, not a guarantee.
3. TRANSLATION SCRIPT — the ~160 scenario translation strings are covered by
   NO other check. check_catalog_roundtrip hashes tasks only, so 15 of them
   sat in Chinese behind a fully green gate.

The corpus is drawn from output the model actually produced, recorded in the
commits that fixed each bug — not invented. That distinction matters: a
hand-written corpus is how the coach fixtures rotted into measuring nothing.

Deliberately NOT included: an ASCII-literal lint over app/ with an allowlist.
It would flag every legitimate English-only branch, and a stale justification
string is indistinguishable from a live one — the audit that proposed it
identified it as where the next bug would hide. Parity is the assertion that
carries weight; a linter here would mostly train people to append to an
allowlist.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coach import _normalize_phrase
from app.llm import find_wrong_script, is_closed_question, is_question, validate
from app.scenarios.builtins import SCENARIOS

# (english, japanese, expected) — each pair is the same utterance in both
# languages. Japanese lines are shapes the actor really emitted; the closed
# 何か greeting is the single most common Japanese service opening and was
# classified open for weeks.
CLOSED_QUESTION_PAIRS = [
    ('Is there anything I can help you with?', '何かお手伝いできることがありますか？', True),
    ('Do you need a train ticket?', '列車のチケットが必要ですか。', True),
    ('Shall I help you?', 'お手伝いしましょうか？', True),
    ('What are you looking for?', '何をお探しですか。', False),
    ('Which would you like?', 'どちらになさいますか？', False),
    ('How about a coffee?', 'コーヒーはいかがですか？', False),
    ('Take your time.', 'ごゆっくりどうぞ。', False),
]

IS_QUESTION_PAIRS = [
    ('What are you looking for?', '何をお探しですか。', True),
    ('Is that everything?', '以上でよろしいですか。', True),
    ('Enjoy your stay.', 'ごゆっくりどうぞ。', False),
    ('Here is your receipt.', 'レシートでございます。', False),
]

# Sentences the model produced on Japanese turns, used for the non-vacuity
# sweep. Mixed deliberately: questions and statements, polite and casual.
JA_CORPUS = [line for _, line, _ in CLOSED_QUESTION_PAIRS] + \
            [line for _, line, _ in IS_QUESTION_PAIRS] + [
    'こんにちは、本屋へようこそ。',
    '年度末の会議は来週の月曜日、東京駅前の本社で行います。',
    '船が沈没した場所を確認します。',
    '砂糖は入れる？',
    'まず何からいたしましょうか。',
    '4つ星のホテル欢迎您，请坐。',          # a real leaked turn
    '本日は新刊が入荷しました。',
]

PREDICATES = [
    ('is_closed_question', is_closed_question),
    ('is_question', is_question),
    ('find_wrong_script', lambda s: bool(find_wrong_script(s, 'Japanese'))),
    ('validate', lambda s: validate(s, max_sentences=4, language='Japanese')[0]),
]


def check_parity():
    failures = []
    for label, rule, pairs in (
        ('is_closed_question', is_closed_question, CLOSED_QUESTION_PAIRS),
        ('is_question', is_question, IS_QUESTION_PAIRS),
    ):
        for english, japanese, expected in pairs:
            got_en, got_ja = rule(english), rule(japanese)
            if got_en != expected or got_ja != expected:
                failures.append(
                    f'{label}: expected {expected} for both\n'
                    f'      EN {got_en!r:<6} {english}\n'
                    f'      JA {got_ja!r:<6} {japanese}')
    return failures


def check_non_vacuity():
    failures = []
    for name, predicate in PREDICATES:
        seen = {bool(predicate(line)) for line in JA_CORPUS}
        if len(seen) < 2:
            only = seen.pop() if seen else None
            failures.append(
                f'{name}: returns {only} for every one of the '
                f'{len(JA_CORPUS)} Japanese corpus lines — it is vacuous here')
    return failures


def check_normalize_is_script_aware():
    """_normalize_phrase must treat 。 as presentation, exactly as it does '.'
    — otherwise a no-op correction reaches a Japanese learner as a correction
    of a sentence that was already right."""
    failures = []
    for bare, terminated in (('I go there', 'I go there.'),
                             ('コーヒーをお願いします', 'コーヒーをお願いします。'),
                             ('よろしいですか', 'よろしいですか？')):
        if _normalize_phrase(bare) != _normalize_phrase(terminated):
            failures.append(
                f'_normalize_phrase: {bare!r} and {terminated!r} normalize differently')
    return failures


def check_translation_script():
    """Scenario translations are covered by no other check in the project."""
    failures = []
    for scenario in SCENARIOS:
        for field in ('name_translations', 'place_translations'):
            japanese = (getattr(scenario, field, {}) or {}).get('Japanese', '')
            if not japanese:
                continue
            leaked = find_wrong_script(japanese, 'Japanese')
            if leaked:
                failures.append(
                    f'{scenario.name}: {field}[Japanese] contains {leaked} — {japanese}')
    return failures


def main():
    print('=' * 78)
    print('RULE VACUITY CHECK')
    print('=' * 78)

    groups = [
        ('parity across languages', check_parity),
        ('non-vacuity on Japanese', check_non_vacuity),
        ('punctuation normalization', check_normalize_is_script_aware),
        ('scenario translation script', check_translation_script),
    ]

    all_failures = []
    for label, fn in groups:
        failures = fn()
        all_failures.extend(failures)
        if failures:
            print(f'\n❌ {label}')
            for failure in failures:
                print(f'   {failure}')
        else:
            print(f'✅ {label}')

    if all_failures:
        print()
        print(f'{len(all_failures)} vacuity failure(s). A rule that is silently')
        print('inert on Japanese looks identical to a rule that is working.')
        return 1

    print()
    print('=' * 78)
    print('✅ RULE VACUITY CHECK PASSED')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
