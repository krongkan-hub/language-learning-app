"""Print composed scenes for eyeballing combinations of place, character and
complications.

    python3 dev/tools/sample_scenes.py --n 20 --seed 7 --lang Japanese
    python3 dev/tools/sample_scenes.py --archetype scenario_01 --n 5

Each scene shows what the learner would see (name, place, speaker) in the
chosen language, the persona note the actor gets, the complications, and the
first tasks a session would draw. Same --seed, same output.
"""
import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.i18n import scenario_name, scenario_place, speaker_label  # noqa: E402
from app.scenarios.compose import ARCHETYPES, PARTS, compose  # noqa: E402


def render(aid: str, rng: random.Random, lang: str, tasks: int) -> str:
    scenario, spec = compose(aid, rng)
    persona = PARTS.characters[spec.character].persona
    speaker = scenario.speaker_translations.get(lang) or speaker_label(scenario.speaker, lang)
    lines = [
        f'[{spec.signature()}] {aid}  seed={spec.seed}  place={spec.place}  character={spec.character}',
        f'  {scenario_name(scenario, lang)}',
        f'  place:    {scenario_place(scenario, lang)}',
        f'  speaker:  {speaker}',
    ]
    if persona:
        lines.append(f'  persona:  {persona.trait}')
    for eid in spec.events:
        e = PARTS.events[eid]
        tag = 'ambient' if not e.archetypes else 'own'
        lines.append(f'  event:    ({tag}) {e.translations.get(lang) or e.text}')
    random.seed(spec.seed)
    for t in scenario.get_session_tasks()[:tasks]:
        lines.append(f'  task:     {t.translations.get(lang, {}).get("goal") or t.goal}')
    return '\n'.join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--n', type=int, default=10)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--lang', default='English', choices=('English', 'Japanese'))
    ap.add_argument('--archetype', help='e.g. scenario_01; default: any')
    ap.add_argument('--tasks', type=int, default=3, help='session tasks to show per scene')
    args = ap.parse_args()
    rng = random.Random(args.seed)
    ids = sorted(ARCHETYPES)
    for _ in range(args.n):
        print(render(args.archetype or rng.choice(ids), rng, args.lang, args.tasks))
        print()


if __name__ == '__main__':
    main()
