"""Hold the scene-part pools (app/scenarios/parts/) to their invariants.

    python3 dev/checks/check_parts.py

A composed scene draws a place, a character and complications for one of the
80 archetypes (docs/plans/dynamic-scenarios.md). Every draw has to make
sense, so this fails on:

- ids: duplicate or dangling (default place/character, alt roles, events'
  archetypes), and an archetype per scenario file, no more, no fewer;
- the seeded defaults drifting from their scenario (place, role, speaker,
  complications), which would make a default composition differ from the
  scenario it stands for;
- a tag outside the closed vocabulary in parts.PLACE_TAGS;
- an archetype with fewer than MIN_PLACES eligible places, or fewer than
  MIN_PERSONAS named characters, or a default place it does not itself fit;
- an event that no eligible place of its archetypes could host;
- a part missing its English or Japanese text;
- a goal the place lexicon flags (below) that is not in the archetype's
  place_bound_goals, or a place-bound goal that is not one of its tasks.
"""
import json
import os
import re
import sys
from collections import Counter

_here = os.path.abspath(__file__)
while not os.path.exists(os.path.join(_here, 'pyproject.toml')):
    _here = os.path.dirname(_here)          # find the project root by
sys.path.insert(0, _here)                   # marker, not by counting depth

from app.scenarios.parts import (EVENT_KINDS, PARTS_DIR, PLACE_TAGS,  # noqa: E402
                                 VENUE_TAGS, load_parts)

MIN_PLACES = 3
MIN_PERSONAS = 2
# A session draws ten tasks, seven advanced; place-bound goals leave the pool
# away from the default place, so this many must stay behind.
MIN_PLACE_FREE_TASKS = 40

# Words that name a kind of venue or a feature of one. A task whose goal, hint
# or done_when uses one of these, when the archetype's default place does too
# and some other eligible place does not, presupposes the default place
# ("Ask what time the vineyard closes" at an urban winery bar) — so it is
# place-bound. Activities ('check-in') and subjects ('marketing', 'ski') are
# left out on purpose: they belong to the archetype, not the place. A tuple is
# one term spelt several ways: a beachside kiosk's tasks say "beach", "ocean"
# and "coastal trail".
PLACE_LEXICON = (
    'restaurant', 'airport', 'counter', 'hotel', 'desk', 'front desk',
    'reception', 'lobby', 'checkpoint', 'station', 'clinic', 'hospital',
    'branch', 'office', 'apartment', 'shop', 'store', 'boutique', 'showroom',
    'salon', 'studio', 'center', 'market', 'stall', 'kiosk', 'booth', 'window',
    'terminal', ('harbor', 'harbour', 'port', 'dock', 'pier'),
    ('beach', 'beachside', 'seaside', 'coastal', 'coast', 'ocean', 'boardwalk'),
    'mountain', 'resort', 'park', 'campground', 'gallery', 'museum',
    'library', 'university', 'campus', 'school', 'kitchen', 'classroom',
    'garage', 'workshop', ('vineyard', 'winery'), 'stadium', 'arena', 'venue',
    'lounge', 'hallway', 'highway', 'road', 'street', 'downtown', 'suburban',
    'outdoor', 'indoor', 'night', 'rooftop', 'mall', 'room', 'home', 'house',
    'vehicle', 'drive-thru', 'parlor', 'alley', 'elevator',
)
# Phrases that contain a venue word without naming the venue: a tourist desk
# at the station still hands out a city-center map, and a hardware store's
# "home" is the learner's.
_NOT_A_VENUE = re.compile(r'\b(?:city cent(?:er|re)|home improvement)\b', re.I)


def _term_re(spellings) -> re.Pattern:
    words = '|'.join(re.escape(w) for w in spellings)
    return re.compile(r'\b(?:' + words + r')(?:s|es)?\b', re.I)


_TERMS = {(t if isinstance(t, str) else t[0]): _term_re((t,) if isinstance(t, str) else t)
          for t in PLACE_LEXICON}


def venue_terms(text: str) -> set:
    """The lexicon terms a piece of text uses, by each term's first spelling."""
    text = _NOT_A_VENUE.sub(' ', text)
    return {term for term, rx in _TERMS.items() if rx.search(text)}


def flag_place_bound(tasks, default_place: str, other_places) -> list:
    """Goals naming a venue term the default place has and some other
    eligible place lacks, in task order."""
    at_default = venue_terms(default_place)
    missing = set()
    for text in other_places:
        missing |= at_default - venue_terms(text)
    out = []
    for t in tasks:
        if venue_terms(f'{t.goal} {t.hint} {t.done_when}') & missing:
            out.append(t.goal)
    return out


def _ja(translations) -> str:
    return (translations or {}).get('Japanese', '').strip()


def problems(parts, scenarios, raw=None) -> list:
    """Every broken invariant, as one line each. `scenarios` maps archetype
    id -> Scenario; `raw` maps file name -> its parsed list, for id
    duplicates that the id-keyed pools have already collapsed."""
    out = []
    for name, rows in (raw or {}).items():
        for rid, n in Counter(r['id'] for r in rows).items():
            if n > 1:
                out.append(f'{name}: id {rid!r} appears {n} times')

    if set(parts.archetypes) != set(scenarios):
        missing = sorted(set(scenarios) - set(parts.archetypes))
        extra = sorted(set(parts.archetypes) - set(scenarios))
        out.append(f'archetypes do not match the scenario files: missing {missing}, extra {extra}')

    for p in parts.places.values():
        bad = sorted(set(p.tags) - PLACE_TAGS)
        if bad:
            out.append(f'place {p.id}: tags outside the vocabulary {bad}')
        if not set(p.tags) & VENUE_TAGS:
            out.append(f'place {p.id}: no venue tag')
        if not p.text.strip() or not _ja(p.translations):
            out.append(f'place {p.id}: missing English or Japanese text')

    for c in parts.characters.values():
        for aid in c.archetypes:
            if aid not in parts.archetypes:
                out.append(f'character {c.id}: unknown archetype {aid!r}')
        if not c.speaker.strip() or not _ja(c.speaker_translations):
            out.append(f'character {c.id}: missing English or Japanese speaker')
        if c.persona is not None:
            pr = c.persona
            if not (pr.name_en.strip() and pr.name_ja.strip()
                    and pr.trait.strip() and pr.ja_register.strip()):
                out.append(f'character {c.id}: incomplete persona')

    for e in parts.events.values():
        if e.kind not in EVENT_KINDS:
            out.append(f'event {e.id}: kind {e.kind!r} not in {EVENT_KINDS}')
        bad = sorted(set(e.requires_place_tags) - PLACE_TAGS)
        if bad:
            out.append(f'event {e.id}: tags outside the vocabulary {bad}')
        if not e.text.strip() or not _ja(e.translations):
            out.append(f'event {e.id}: missing English or Japanese text')
        for aid in e.archetypes:
            if aid not in parts.archetypes:
                out.append(f'event {e.id}: unknown archetype {aid!r}')
        hosts = [aid for aid in (e.archetypes or parts.archetypes)
                 if aid in parts.archetypes
                 and any(set(e.requires_place_tags) <= set(p.tags)
                         for p in parts.eligible_places(aid))]
        if not hosts:
            out.append(f'event {e.id}: no eligible place can host it')

    for aid, a in parts.archetypes.items():
        bad = sorted(set(a.requires_place_tags) - PLACE_TAGS)
        if bad:
            out.append(f'{aid}: requires tags outside the vocabulary {bad}')
        if not set(a.requires_place_tags) & VENUE_TAGS:
            out.append(f'{aid}: requires no venue tag')
        eligible = parts.eligible_places(aid)
        if len(eligible) < MIN_PLACES:
            out.append(f'{aid}: {len(eligible)} eligible places (want ≥{MIN_PLACES})')
        place = parts.places.get(a.default_place)
        if place is None:
            out.append(f'{aid}: unknown default place {a.default_place!r}')
        elif place not in eligible:
            out.append(f'{aid}: default place {a.default_place} lacks its required tags')
        char = parts.characters.get(a.default_character)
        if char is None:
            out.append(f'{aid}: unknown default character {a.default_character!r}')
        elif aid not in char.archetypes:
            out.append(f'{aid}: default character {char.id} is not on this archetype')
        personas = [c for c in parts.characters_for(aid) if c.persona is not None]
        if len(personas) < MIN_PERSONAS:
            out.append(f'{aid}: {len(personas)} personas (want ≥{MIN_PERSONAS})')
        for r in a.alt_roles:
            if r.character_id not in parts.characters:
                out.append(f'{aid}: alt role {r.character_id!r} is not a character')

        s = scenarios.get(aid)
        if s is None:
            continue
        if place is not None and (place.text != s.place
                                  or _ja(place.translations) != _ja(s.place_translations)):
            out.append(f'{aid}: default place {place.id} differs from the scenario — re-run extract_parts')
        if char is not None and (char.role != s.role or char.speaker != s.speaker
                                 or char.persona is not None):
            out.append(f'{aid}: default character {char.id} differs from the scenario — re-run extract_parts')
        own = {e.text for e in parts.events.values() if aid in e.archetypes}
        lost = [c for c in s.complications if c not in own]
        if lost:
            out.append(f'{aid}: complications missing from events {lost} — re-run extract_parts')

        goals = {t.goal for t in s.tasks}
        stray = [g for g in a.place_bound_goals if g not in goals]
        if stray:
            out.append(f'{aid}: place-bound goals that are not its tasks {stray}')
        if place is not None:
            others = [p.text for p in eligible if p.id != place.id]
            unflagged = [g for g in flag_place_bound(s.tasks, place.text, others)
                         if g not in a.place_bound_goals]
            if unflagged:
                out.append(f'{aid}: lexicon flags goals missing from place_bound_goals {unflagged}')
        free = len(goals - set(a.place_bound_goals))
        if free < MIN_PLACE_FREE_TASKS:
            out.append(f'{aid}: {free} place-free tasks (want ≥{MIN_PLACE_FREE_TASKS})')
    return out


def scenarios_by_archetype() -> dict:
    """Archetype id -> Scenario, by file name (scenario_01.json -> scenario_01)."""
    from app.scenarios.builtins import DATA_DIR, SCENARIOS
    files = sorted(DATA_DIR.glob('scenario_*.json'), key=lambda p: p.name)
    return {f.stem: s for f, s in zip(files, SCENARIOS)}


def main() -> bool:
    raw = {}
    for name in ('archetypes', 'places', 'characters', 'events'):
        with open(PARTS_DIR / f'{name}.json', encoding='utf-8') as f:
            raw[name] = json.load(f)
    parts = load_parts()
    found = problems(parts, scenarios_by_archetype(), raw)
    if found:
        print(f'❌ SCENE PARTS: {len(found)} problem(s)')
        for line in found:
            print(f'   {line}')
        return False
    personas = sum(c.persona is not None for c in parts.characters.values())
    bound = sum(len(a.place_bound_goals) for a in parts.archetypes.values())
    print(f'✅ SCENE PARTS OK — {len(parts.archetypes)} archetypes, {len(parts.places)} places, '
          f'{personas} personas, {len(parts.events)} events, {bound} place-bound goals')
    return True


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
