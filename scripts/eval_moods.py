#!/usr/bin/env python3
import argparse
import json
import os
import random
import sys
import time

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.cli import extract_and_format_vocab
from app.llm import FALLBACK_ACTOR_LINE, NPC_MOODS, call_actor, validate
from app.scenarios.builtins import SCENARIOS
from app.session import build_actor_system_prompt, ACTOR_MAX_SENTENCES

DEFAULT_LANGUAGES = ['English', 'Japanese']

# Plausible learner replies used to grow the conversation between actor turns.
# Deliberately generic so the same script works for any venue in the catalog,
# and deliberately fixed rather than sampled so a run is reproducible. The
# Japanese lines are checked clean of simplified-Chinese forms, so they cannot
# themselves prime the script drift this suite is trying to measure.
LEARNER_FOLLOWUPS = {
    'English': [
        "I see. Could you tell me a bit more about that?",
        "Hmm, I'm not sure yet. What are my options?",
        "All right, let's go with that. How long will it take?",
        "Thanks. And what do I need to do next?",
        "Sorry, one more thing — how much does that come to?",
    ],
    'Japanese': [
        "なるほど。もう少し詳しく教えてください。",
        "うーん、まだ迷っています。どんな選択肢がありますか。",
        "では、それでお願いします。どのくらいかかりますか。",
        "ありがとうございます。次は何をすればいいですか。",
        "すみません、もう一つ。値段はいくらになりますか。",
    ],
}

OPENER = {
    'English': 'Hello!',
    'Japanese': 'こんにちは。',
}


def run_conversation(language: str, mood: str, scenario, turns: int):
    """Run one multi-turn conversation and validate every actor turn.

    Turn 1 answers the learner's greeting; later turns carry the real message
    history, so they measure mid-conversation behaviour rather than resampling
    the same opening.
    """
    task = scenario.tasks[0]
    complication = scenario.complications[0] if scenario.complications else None
    system_prompt = build_actor_system_prompt(
        scenario, task, language=language, mood=mood, complication=complication
    )
    followups = LEARNER_FOLLOWUPS[language]
    messages = [{'role': 'user', 'content': OPENER[language]}]

    samples = []
    for turn_idx in range(turns):
        t0 = time.time()
        reply = call_actor(
            messages,
            system_prompt,
            speaker=scenario.speaker,
            max_sentences=ACTOR_MAX_SENTENCES,
            cache_key=None,
            language=language,
        )
        elapsed = time.time() - t0
        ok, reason = validate(reply, max_sentences=ACTOR_MAX_SENTENCES, language=language)
        samples.append({
            'language': language,
            'mood': mood,
            'scenario': scenario.name,
            'turn': turn_idx + 1,
            'position': 'opening' if turn_idx == 0 else 'mid',
            'ok': ok,
            'reason': reason,
            # call_actor returns a canned line when three attempts and the
            # salvage path all fail. That line passes validate() in every
            # language, so it scores as a pass while the learner actually got
            # no NPC turn — counted separately rather than folded into the score.
            'fallback': reply.startswith(FALLBACK_ACTOR_LINE),
            'latency': elapsed,
            'reply': reply,
        })

        # app/cli.py appends the vocab-stripped spoken line to the history, not
        # the raw reply. Mirroring that matters here: replaying `explanation:`
        # lines back at the model would prime a drift this suite is measuring.
        spoken, _ = extract_and_format_vocab(reply, language, scenario)
        messages = messages + [
            {'role': 'assistant', 'content': spoken},
            {'role': 'user', 'content': followups[turn_idx % len(followups)]},
        ]

    return samples


def pct(passed: int, total: int) -> float:
    return (passed / total) * 100 if total else 0.0


def summarize(samples: list) -> tuple[int, int, dict]:
    passed = sum(1 for s in samples if s['ok'])
    reasons = {}
    for s in samples:
        if not s['ok']:
            reasons[s['reason']] = reasons.get(s['reason'], 0) + 1
    return passed, len(samples), reasons


def reasons_str(reasons: dict) -> str:
    return ", ".join(f"{k}: {v}" for k, v in sorted(reasons.items())) if reasons else "None"


def print_breakdown(title: str, groups: list):
    """groups: list of (label, samples)."""
    print("=" * 110)
    print(title)
    print("=" * 110)
    print(f"{'Group':<58} | {'Pass':<7} | {'Pass %':<8} | {'Fallback':<8} | {'Mean Lat':<9} | Failure Reasons")
    print("-" * 110)
    for label, group in groups:
        passed, total, reasons = summarize(group)
        fallbacks = sum(1 for s in group if s['fallback'])
        mean_lat = sum(s['latency'] for s in group) / len(group) if group else 0.0
        print(
            f"{label:<58} | {f'{passed}/{total}':<7} | {pct(passed, total):>6.1f}%  | "
            f"{fallbacks:<8} | {mean_lat:>7.2f}s  | {reasons_str(reasons)}"
        )
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate actor output validation pass rate across NPC_MOODS, languages and conversation depth."
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=4,
        help="Actor turns per conversation; turn 1 is the opening, the rest are mid-conversation (default: 4)",
    )
    parser.add_argument(
        "--conversations",
        type=int,
        default=2,
        help="Conversations per language/mood cell, each on its own scenario (default: 2)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for scenario selection (default: 42)",
    )
    parser.add_argument(
        "--languages",
        default=",".join(DEFAULT_LANGUAGES),
        help="Comma-separated target languages (default: English,Japanese)",
    )
    parser.add_argument(
        "--dump",
        default="",
        help="Optional path to write every sample as JSON for offline analysis",
    )

    args = parser.parse_args()
    languages = [lang.strip() for lang in args.languages.split(",") if lang.strip()]
    for lang in languages:
        if lang not in LEARNER_FOLLOWUPS:
            parser.error(f"No learner follow-up lines defined for language '{lang}'")

    # One unbiased seeded draw of venues, shared by every language and mood, so
    # English and Japanese are compared on identical scenarios and no venue is
    # hand-picked for being easy.
    needed = len(NPC_MOODS) * args.conversations
    picks = random.Random(args.seed).sample(range(len(SCENARIOS)), min(needed, len(SCENARIOS)))
    scenarios = [SCENARIOS[i] for i in picks]

    total_samples = len(languages) * needed * args.turns
    print(
        f"Evaluating {len(NPC_MOODS)} moods x {len(languages)} languages x {args.conversations} conversations "
        f"x {args.turns} turns = {total_samples} samples [seed={args.seed}]"
    )
    print(f"Scenarios drawn: {', '.join(s.name for s in scenarios)}")
    print("=" * 110)

    samples = []
    step = 0
    for language in languages:
        for mood_idx, mood in enumerate(NPC_MOODS):
            for conv_idx in range(args.conversations):
                scenario = scenarios[(mood_idx * args.conversations + conv_idx) % len(scenarios)]
                step += 1
                print(
                    f"[{step}/{len(languages) * needed}] {language} | {mood[:40]} | {scenario.name}"
                )
                convo = run_conversation(language, mood, scenario, args.turns)
                for s in convo:
                    if not s['ok']:
                        print(f"    turn {s['turn']} ({s['position']}) FAIL: {s['reason']}")
                        print(f"      reply: {s['reply']!r}")
                    elif s['fallback']:
                        print(f"    turn {s['turn']} ({s['position']}) FALLBACK (scored as pass)")
                samples.extend(convo)

    print()
    print_breakdown(
        "BY LANGUAGE",
        [(lang, [s for s in samples if s['language'] == lang]) for lang in languages],
    )
    print_breakdown(
        "BY LANGUAGE x MOOD",
        [
            (f"{lang} | {mood}"[:58], [s for s in samples if s['language'] == lang and s['mood'] == mood])
            for lang in languages
            for mood in NPC_MOODS
        ],
    )
    print_breakdown(
        "BY TURN POSITION (opening vs mid-conversation)",
        [
            (f"{lang} | {pos}", [s for s in samples if s['language'] == lang and s['position'] == pos])
            for lang in languages
            for pos in ('opening', 'mid')
        ]
        + [
            (f"ALL | turn {n}", [s for s in samples if s['turn'] == n])
            for n in range(1, args.turns + 1)
        ],
    )

    failures = [s for s in samples if not s['ok']]
    if failures:
        print("=" * 110)
        print("FAILURES IN FULL")
        print("=" * 110)
        for s in failures:
            print(f"- [{s['language']} | {s['mood'][:30]} | {s['scenario']} | turn {s['turn']} {s['position']}] {s['reason']}")
            print(f"  {s['reply']!r}")
        print()

    if args.dump:
        with open(args.dump, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(samples)} samples to {args.dump}")

    total_passed, total_turns, all_reasons = summarize(samples)
    fallbacks = sum(1 for s in samples if s['fallback'])
    print("=" * 110)
    print(f"Failure reasons: {reasons_str(all_reasons)}")
    print(f"Fallback lines returned (scored as passes): {fallbacks}/{total_turns} ({pct(fallbacks, total_turns):.1f}%)")

    # Single aggregate line so check_evals.sh has one number to gate on.
    score = pct(total_passed, total_turns)
    print(f"\nFinal Moods Score: {score:.1f}% ({total_passed}/{total_turns})")


if __name__ == "__main__":
    main()
