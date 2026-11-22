"""The greeting (GREETING_SYS through call_actor, repair included) on the
fixture cases, 5 iterations each.

    python3 dev/evals/eval_actor.py                          # the gated fixture
    python3 dev/evals/eval_actor.py --composed N --seed S    # N composed scenes, EN + JA
    python3 dev/evals/eval_actor.py --composed N --seed S --default   # their legacy scenarios

--composed builds a case per scene and language from the scene's own place
and role in that language (persona included, as app/session.py words them)
and speaker; --default runs the same archetypes as
the legacy scenarios, so the two are a matched comparison
(dev/evals/composed.py).
"""
import argparse
import json
import os
import sys

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)          # find the project root by
sys.path.insert(0, _here)                   # marker, not by counting depth

from app.i18n import scenario_place, scenario_role
from app.llm import call_actor, GREETING_SYS, validate
from app.vocab_card import extract_and_format_vocab
from dev.evals.composed import composed_scenes

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fixtures', 'actor_cases.json')

def evaluate_case(case):
    system = GREETING_SYS.format(
        place=case['place'],
        role=case['role'],
        language=case['language'],
        mood=case.get('mood', "chatty and friendly"),
        complication="",
        task_setup=""
    )
    seed = [{'role': 'user', 'content': 'Hello!'}]
    raw_actor = call_actor(seed, system, speaker=case['speaker'], max_sentences=4, language=case['language'])
    ok, reason = validate(raw_actor, max_sentences=4, language=case['language'])
    clean_text, vocab_box = extract_and_format_vocab(raw_actor)
    has_vocab = len(vocab_box.strip()) > 0
    return (ok and has_vocab), raw_actor, reason, has_vocab, ok

def scene_cases(n, seed, default=False):
    return [{'name': f'{spec.archetype}:{spec.place}:{spec.character}',
             'place': scenario_place(sc, language), 'role': scenario_role(sc, language),
             'speaker': sc.speaker, 'language': language}
            for sc, spec in composed_scenes(n, seed, default)
            for language in ('English', 'Japanese')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--composed', type=int, default=None, metavar='N')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--default', action='store_true',
                    help="with --composed: each archetype's default composition (legacy)")
    args = ap.parse_args()

    if args.composed:
        cases = scene_cases(args.composed, args.seed, args.default)
    else:
        if not os.path.exists(FIXTURE_PATH):
            print(f"Fixture not found: {FIXTURE_PATH}")
            sys.exit(1)
        with open(FIXTURE_PATH, 'r') as f:
            cases = json.load(f)

    print(f"Running Actor Eval on {len(cases)} cases across 5 iterations...")
    total_runs = len(cases) * 5
    passed_runs = 0

    print("=" * 80)
    for i, case in enumerate(cases):
        print(f"Case {i+1}: {case['name']} — {case['speaker']} at {case['place']} [{case['language']}]")
        case_passes = 0
        for it in range(5):
            passed, raw, reason, has_vocab, ok = evaluate_case(case)
            if passed:
                case_passes += 1
            else:
                print(f"  Iter {it+1} FAIL: valid={ok}, reason='{reason}', has_vocab={has_vocab}")
                print(f"    raw: {raw!r}")
        passed_runs += case_passes
        print(f"  Result: {case_passes}/5 passed")
        print("-" * 80)

    score = (passed_runs / total_runs) * 100
    print(f"\nFinal Actor Score: {score:.1f}% ({passed_runs}/{total_runs})")

if __name__ == "__main__":
    main()
