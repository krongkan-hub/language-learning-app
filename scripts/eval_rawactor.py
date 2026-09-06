#!/usr/bin/env python3
"""Score the actor's FIRST generation, with no repair of any kind — OPEN-14.

Why this exists. `scripts/eval_actor.py` and `scripts/eval_moods.py` both call
`call_actor`, which retries up to 3x, then salvages, then falls back to a canned
line. `validate()` at that layer only ever sees what survived all of it, so
those suites measure the repair pipeline and score 85-100%. They cannot see the
actor itself regress until repair stops covering for it — and the repair
pipeline is the part that keeps getting changed.

This harness generates ONE turn and scores it. No retry, no salvage, no
fallback line. The number it prints is the actor's own compliance rate, and the
REASON DISTRIBUTION beneath it is the real product: it says which rule the model
trips, which a repaired score can never tell you. A rule tightened upstream
(the Japanese script check, the closed-question fix) shows up here and nowhere
else.

Method, and how it relates to the earlier probe. The 16.7-33.3% figures in
BACKLOG.md and eval_baselines.json came from `scratch/measure_greeting.py`: 12
seeded scenarios, one raw `_llm_chat` per scenario, scored with `validate`.
That shape is sound and is kept. Three things about it are not, and are fixed
here, so the numbers are NOT directly comparable to the old ones:

  * it scored greetings against max_sentences=3, but greetings are allowed
    GREETING_MAX_SENTENCES=4, so some "failures" were compliant turns;
  * it passed no `language`, so `find_wrong_script` never ran and every
    Japanese script leak scored as a pass;
  * it sampled only greetings and only mood='neutral', which is not one of the
    six real NPC_MOODS, so it measured a prompt the app never sends.

Scoring goes through `validate`, which dispatches the per-sentence rules to
`sentence_rejection_reason` — the single place those rules live. Nothing here
reimplements a rule, so this harness cannot drift from the shipped ones.

Generation uses cache_key=None: every sample is independent, where the suites
share one rolling prompt cache. A raw measurement should not have earlier
samples in its context.

Usage:
    python3 scripts/eval_rawactor.py [--scenarios N] [--seed S] [--json OUT]
"""
import argparse
import json
import os
import random
import sys
import time

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm import ACTOR_OPTS, NPC_MOODS, _llm_chat, sanitize, validate
from app.scenarios.builtins import SCENARIOS
from app.session import (ACTOR_MAX_SENTENCES, GREETING_MAX_SENTENCES,
                         build_actor_system_prompt, build_greeting_system_prompt)

DEFAULT_LANGUAGES = ['English', 'Japanese']
DEFAULT_SCENARIOS = 12

OPENER = {'English': 'Hello!', 'Japanese': 'こんにちは。'}

# A fixed NPC line and learner reply, so the mid-conversation prompt carries a
# real history without a second generation compounding into the measurement.
# Deliberately bland, and the Japanese is free of simplified-Chinese forms so it
# cannot itself prime the script drift being measured.
PRIOR_NPC = {
    'English': "Of course, let me take a look at that for you.",
    'Japanese': "かしこまりました。少々お待ちください。",
}
LEARNER_REPLY = {
    'English': "Thanks. What are my options from here?",
    'Japanese': "ありがとうございます。どんな選択肢がありますか。",
}


def build_samples(scenarios, languages, moods=NPC_MOODS):
    """The (scenario, language, kind, mood) grid this run will generate.

    Pure: no model, no I/O. Kept separate so the sampling is unit-testable and
    so a run is fully reproducible from its seed.
    """
    plan = []
    for idx, scenario in enumerate(scenarios):
        mood = moods[idx % len(moods)]
        for language in languages:
            for kind in ('greeting', 'mid'):
                plan.append({'scenario': scenario, 'language': language,
                             'kind': kind, 'mood': mood})
    return plan


def generate_once(item):
    """One raw generation. No retry, no salvage, no fallback."""
    scenario = item['scenario']
    task = scenario.tasks[0]
    complication = scenario.complications[0] if scenario.complications else None
    language, kind = item['language'], item['kind']

    if kind == 'greeting':
        system_prompt = build_greeting_system_prompt(
            scenario, task, language=language, mood=item['mood'],
            complication=complication)
        messages = [{'role': 'user', 'content': OPENER[language]}]
        max_sentences = GREETING_MAX_SENTENCES
    else:
        system_prompt = build_actor_system_prompt(
            scenario, task, language=language, mood=item['mood'],
            complication=complication)
        messages = [
            {'role': 'user', 'content': OPENER[language]},
            {'role': 'assistant', 'content': PRIOR_NPC[language]},
            {'role': 'user', 'content': LEARNER_REPLY[language]},
        ]
        max_sentences = ACTOR_MAX_SENTENCES

    response = _llm_chat(
        messages=[{'role': 'system', 'content': system_prompt}] + messages,
        options=ACTOR_OPTS, cache_key=None)
    raw = response['message']['content']
    # sanitize() runs on every shipped path before validate() does, so applying
    # it here measures the model rather than the speaker-prefix stripper.
    text = sanitize(raw, speaker=scenario.speaker)
    ok, reason = validate(text, max_sentences=max_sentences, language=language)
    return ok, reason, text, raw


def summarize(samples):
    """(passed, total, {reason: count}) for a list of scored samples."""
    passed = sum(1 for s in samples if s['ok'])
    reasons = {}
    for s in samples:
        if not s['ok']:
            # Collapse the sentence count so 4/5/6 aggregate into one class.
            key = s['reason']
            if key.startswith('Too many sentences'):
                key = 'Too many sentences'
            elif key.startswith('Wrong script'):
                key = 'Wrong script'
            reasons[key] = reasons.get(key, 0) + 1
    return passed, len(samples), reasons


def pct(passed, total):
    return (passed / total * 100) if total else 0.0


def print_group(label, samples):
    passed, total, reasons = summarize(samples)
    detail = ', '.join(f'{v}x {k}' for k, v in
                       sorted(reasons.items(), key=lambda kv: -kv[1])) or 'none'
    print(f'  {label:<26} {passed:>3}/{total:<3} = {pct(passed, total):5.1f}%   {detail}')


def main():
    parser = argparse.ArgumentParser(
        description='Score the actor first generation with no repair (OPEN-14).')
    parser.add_argument('--scenarios', type=int, default=DEFAULT_SCENARIOS)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--languages', nargs='+', default=DEFAULT_LANGUAGES)
    parser.add_argument('--json', dest='json_out', default=None)
    args = parser.parse_args()

    picks = random.Random(args.seed).sample(
        range(len(SCENARIOS)), min(args.scenarios, len(SCENARIOS)))
    scenarios = [SCENARIOS[i] for i in picks]
    plan = build_samples(scenarios, args.languages)

    print('=' * 78)
    print('RAW ACTOR COMPLIANCE — first generation only, no retry/salvage/fallback')
    print(f'{len(scenarios)} scenarios x {len(args.languages)} languages x 2 turn kinds '
          f'= {len(plan)} samples [seed={args.seed}]')
    print('=' * 78)

    samples = []
    t0 = time.time()
    for i, item in enumerate(plan, 1):
        ok, reason, text, raw = generate_once(item)
        samples.append({'scenario': item['scenario'].name, 'language': item['language'],
                        'kind': item['kind'], 'mood': item['mood'],
                        'ok': ok, 'reason': reason, 'text': text, 'raw': raw})
        print(f'  [{i:>3}/{len(plan)}] {item["language"][:2]} {item["kind"]:<8} '
              f'{"ok " if ok else "FAIL"} {reason[:52]}')

    print()
    print('By language:')
    for language in args.languages:
        print_group(language, [s for s in samples if s['language'] == language])
    print('By turn kind:')
    for kind in ('greeting', 'mid'):
        print_group(kind, [s for s in samples if s['kind'] == kind])
    print('By language x turn kind:')
    for language in args.languages:
        for kind in ('greeting', 'mid'):
            print_group(f'{language} {kind}',
                        [s for s in samples if s['language'] == language and s['kind'] == kind])

    passed, total, reasons = summarize(samples)
    print()
    print('Rejection reasons (all samples):')
    for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f'  {count:>3}x  {reason}')
    if not reasons:
        print('  none')

    print(f'\nElapsed {time.time() - t0:.0f}s')
    # This wording is what check_evals.sh greps ("Final ... Score:", tail -1).
    # The per-language lines above are deliberately NOT phrased that way, or one
    # of them would become the number the gate reads.
    print(f'\nFinal Raw Score: {pct(passed, total):.1f}% ({passed}/{total})')

    if args.json_out:
        with open(args.json_out, 'w', encoding='utf-8') as fh:
            json.dump(samples, fh, ensure_ascii=False, indent=2)
        print(f'Wrote {args.json_out}')


if __name__ == '__main__':
    main()
