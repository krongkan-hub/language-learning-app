"""Composed scenes: an archetype's tasks at a drawn place, with a drawn
character and the complications that place can host.

`compose` draws a scene and returns it as an ordinary `Scenario`, so the
session, actor, coach and judge take it unchanged, together with the
`SceneSpec` that names its parts. `compose_from_spec` rebuilds the same scene
from a spec (resume, `--seed`), and `default_spec` names the composition that
is exactly the legacy scenario. Plan: docs/plans/dynamic-scenarios.md.

Not wired into the CLI yet (PR 4 of the plan).
"""
import hashlib
import json
import random
from dataclasses import asdict, dataclass, replace
from typing import Dict, Optional, Tuple

from .builtins import scenarios_by_archetype
from .models import Scenario
from .parts import Character, Parts, load_parts

SPEC_VERSION = 1

PARTS: Parts = load_parts()
ARCHETYPES: Dict[str, Scenario] = scenarios_by_archetype()


@dataclass(frozen=True)
class SceneSpec:
    archetype: str
    place: str
    character: str
    events: Tuple[str, ...]
    seed: Optional[int] = None
    # Drop-in characters arrive with PR 6 of the plan.
    dropin: None = None
    v: int = SPEC_VERSION

    def as_dict(self) -> dict:
        d = asdict(self)
        d['events'] = list(self.events)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'SceneSpec':
        return cls(archetype=d['archetype'], place=d['place'], character=d['character'],
                   events=tuple(d['events']), seed=d.get('seed'), dropin=None,
                   v=d.get('v', SPEC_VERSION))

    def signature(self) -> str:
        """Names the scene, not the draw: two seeds that land on the same
        parts share it."""
        d = self.as_dict()
        del d['seed']
        canon = json.dumps(d, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        return hashlib.sha1(canon.encode('utf-8')).hexdigest()[:10]


def default_spec(archetype: str) -> SceneSpec:
    """The composition that equals the legacy scenario: its own place,
    role and complications."""
    a = PARTS.archetypes[archetype]
    return SceneSpec(archetype=archetype, place=a.default_place, character=a.default_character,
                     events=tuple(e.id for e in PARTS.events_for(archetype, a.default_place)
                                  if e.archetypes))


def compose(archetype: str, rng: random.Random) -> Tuple[Scenario, SceneSpec]:
    """Draw a scene for `archetype`. The draw comes from a seed taken from
    `rng`, and the spec records it."""
    seed = rng.randrange(2 ** 31)
    r = random.Random(seed)
    place = r.choice(PARTS.eligible_places(archetype))
    character = r.choice(PARTS.characters_for(archetype))
    fitting = PARTS.events_for(archetype, place.id)
    events = [e.id for e in fitting if e.archetypes]
    ambient = [e.id for e in fitting if not e.archetypes]
    if ambient:
        events.append(r.choice(ambient))
    spec = SceneSpec(archetype=archetype, place=place.id, character=character.id,
                     events=tuple(events), seed=seed)
    return compose_from_spec(spec)


def compose_from_spec(spec: SceneSpec) -> Tuple[Scenario, SceneSpec]:
    """Rebuild a scene. A part id that no longer exists, or no longer fits,
    falls back to the archetype's default (or is dropped, for an event); the
    returned spec says what was actually used."""
    a = PARTS.archetypes[spec.archetype]
    legacy = ARCHETYPES[spec.archetype]
    eligible = {p.id for p in PARTS.eligible_places(spec.archetype)}
    place = PARTS.places[spec.place if spec.place in eligible else a.default_place]
    character = PARTS.characters.get(spec.character)
    if character is None or spec.archetype not in character.archetypes:
        character = PARTS.characters[a.default_character]
    fitting = {e.id for e in PARTS.events_for(spec.archetype, place.id)}
    events = tuple(eid for eid in spec.events if eid in fitting)
    spec = replace(spec, place=place.id, character=character.id, events=events)

    if place.id == a.default_place:
        name, name_translations = legacy.name, dict(legacy.name_translations)
    else:
        name = f'{legacy.name} · {place.text}'
        name_translations = {lang: f'{n} · {place.translations.get(lang, place.text)}'
                             for lang, n in legacy.name_translations.items()}
    role, speaker, speaker_translations = _cast(character)
    scenario = Scenario(
        name=name,
        place=place.text,
        role=role,
        speaker=speaker,
        tasks=[t for t in legacy.tasks if PARTS.goal_fits(spec.archetype, t.goal, place.id)],
        complications=[PARTS.events[eid].text for eid in events],
        name_translations=name_translations,
        place_translations=dict(place.translations),
        threads=dict(legacy.threads),
        speaker_translations=speaker_translations,
    )
    return scenario, spec


def _cast(c: Character) -> Tuple[str, str, Dict[str, str]]:
    """Role, speaker and speaker translations for a character. A persona's
    name goes into the label unless the label already carries it
    ('Officer Kato', '加藤巡査')."""
    if c.persona is None:
        return c.role, c.speaker, {}
    p = c.persona
    role = (f'{c.role} Your name is {p.name_en} ({p.name_ja} in Japanese), {p.trait}. '
            f'When speaking Japanese, use {p.ja_register}.')
    en_names = p.name_en.split()
    speaker = c.speaker if set(en_names) & set(c.speaker.split()) else f'{p.name_en} ({c.speaker})'
    ja_names = p.name_ja.replace('・', ' ').split()
    labels = {lang: (label if any(n in label for n in ja_names) else f'{p.name_ja}（{label}）')
              for lang, label in c.speaker_translations.items()}
    return role, speaker, labels
