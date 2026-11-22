"""Composed scenes: an archetype's tasks at a drawn place, with a drawn
character and the complications that place can host.

`compose` draws a scene and returns it as an ordinary `Scenario`, so the
session, actor, coach and judge take it unchanged, together with the
`SceneSpec` that names its parts. `compose_from_spec` rebuilds the same scene
from a spec (resume, `--seed`), and `default_spec` names the composition that
is exactly the legacy scenario. Plan: docs/plans/dynamic-scenarios.md.

The CLI's random offer serves one when LANGUAGE_COACH_COMPOSE=1, or with
`--seed N` (app/cli/state.py composed_scene).
"""
import hashlib
import json
import random
import re
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

    # `name` stays the archetype's: sessions, task logs, mistakes and mastery
    # are keyed by it. A drawn place shows only through the translations,
    # English included, which is what i18n.scenario_name displays.
    if place.id == a.default_place:
        name_translations = dict(legacy.name_translations)
    else:
        shown = {'English': legacy.name, **legacy.name_translations}
        name_translations = {lang: f'{n} · {place.translations.get(lang, place.text)}'
                             for lang, n in shown.items()}
    role, role_translations, speaker, speaker_translations, listener = _cast(character)
    scenario = Scenario(
        name=legacy.name,
        place=place.text,
        role=role,
        speaker=speaker,
        tasks=[t for t in legacy.tasks if PARTS.goal_fits(spec.archetype, t.goal, place.id)],
        complications=[PARTS.events[eid].text for eid in events],
        name_translations=name_translations,
        place_translations=dict(place.translations),
        threads=dict(legacy.threads),
        speaker_translations=speaker_translations,
        listener=listener,
        role_translations=role_translations,
    )
    return scenario, spec


def _cast(c: Character) -> Tuple[str, Dict[str, str], str, Dict[str, str], str]:
    """Role, role translations, speaker, speaker translations and listener for
    a character. A persona's label is always `Name (Role)` / `名前（役割）`; its
    character carries the role alone ('Officer', '巡査'), never a name
    ('Officer Kato').

    Each language's role names the persona in that language only. One role
    for both carried "(林 恵子 in Japanese)" and a Japanese register into
    English prompts, which then taught Japanese words in English turns, and
    the romanised name into Japanese turns ('sarah Mitchellといいます'). The
    trait colours manner, not agenda: a persona that "loves putting outfits
    together" steered the learner off their objective (playtest seed 2)."""
    if c.persona is None:
        return c.role, {}, c.speaker, {}, ''
    p = c.persona
    lead = ("Let that show in how you talk, but follow the learner's lead: "
            "answer what they ask before suggesting anything of your own.")
    role = f'{c.role} Your name is {p.name_en}, {p.trait}. {lead}'
    roles = {'English': role,
             'Japanese': (f'{c.role} Your name is {p.name_ja}; say it only in Japanese '
                          f'script, never romanised. You are {p.trait}. {lead} '
                          f'Speak {p.ja_register}.')}
    labels = {lang: f'{p.name_ja}（{label}）' for lang, label in c.speaker_translations.items()}
    who = re.split(r'(?<=[.!?])\s', c.role.strip(), maxsplit=1)[0]
    who = re.sub(r'^You are\s+', '', who).rstrip('.')
    return role, roles, f'{p.name_en} ({c.speaker})', labels, f'{p.name_en}, {who}'
