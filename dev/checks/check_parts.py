"""Hold the scene-part pools (app/scenarios/parts/) to their invariants.

    python3 dev/checks/check_parts.py

A composed scene draws a place, a character and complications for one of the
80 archetypes (docs/plans/dynamic-scenarios.md). Every draw has to make
sense, so this fails on:

- ids: duplicate or dangling (default place/character, alt roles, events'
  archetypes), and an archetype per scenario file, no more, no fewer;
- a default composition (default place, default character, no persona)
  that differs from the legacy scenario it stands for: place, role, speaker
  and its Japanese label as the legacy UI shows it, complications, and every
  goal drawable at the default place;
- a tag outside the closed vocabulary in parts.PLACE_TAGS;
- an archetype with fewer than MIN_PLACES eligible places, or fewer than
  MIN_PERSONAS named characters, or a default place it does not itself fit;
- an event that no eligible place of its archetypes could host;
- a part missing its English or Japanese text;
- a persona that drops the NPC's name when the role names it and the tasks
  use it ("Greet your neighbor Alex");
- a goal that names something of the place (either lexicon below) and can be
  drawn at an eligible place that lacks it — unless its
  goal_requires_place_tags keep it away or lexicon_waivers says the word is
  not about the place; a requirement or waiver on a goal that is not a task,
  a requirement no eligible place meets or every eligible place meets (it
  excludes nothing), a waived term no eligible place would be flagged for;
- an eligible place left with fewer than MIN_PLACE_FREE_TASKS goals.
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

from app.i18n import speaker_label  # noqa: E402
from app.scenarios.builtins import scenarios_by_archetype  # noqa: E402
from app.scenarios.parts import (EVENT_KINDS, PARTS_DIR, PLACE_TAGS,  # noqa: E402
                                 VENUE_TAGS, fits, load_parts)

MIN_PLACES = 3
MIN_PERSONAS = 2
# A session draws ten tasks, seven advanced; goals a place does not meet
# leave the pool there, so this many must stay behind at every place.
MIN_PLACE_FREE_TASKS = 40

# Words that name a kind of venue or a feature of one, compared by text. A
# task whose goal, hint or done_when uses one of these, when the archetype's
# default place does too and some other eligible place does not, presupposes
# the default place ("Ask what time the vineyard closes" at an urban winery
# bar). Activities ('check-in') and subjects ('marketing', 'ski') are left out
# on purpose: they belong to the archetype, not the place. A tuple is one term
# spelt several ways.
PLACE_LEXICON = (
    'restaurant', 'counter', 'hotel', 'desk', 'front desk',
    'reception', 'checkpoint', 'station', 'clinic',
    'branch', 'office', 'apartment', 'shop', 'store', 'boutique', 'showroom',
    'salon', 'studio', 'center', 'market', 'stall', 'kiosk', 'booth', 'window',
    'terminal', ('harbor', 'harbour', 'port', 'dock', 'pier'),
    'mountain', 'resort', 'park', 'campground', 'gallery', 'museum',
    'library', 'university', 'campus', 'school', 'kitchen', 'classroom',
    'garage', 'workshop', ('vineyard', 'winery'), 'stadium', 'arena', 'venue',
    'lounge', 'hallway', 'road', 'street', 'downtown', 'suburban',
    'outdoor', 'indoor', 'night', 'rooftop', 'mall', 'room', 'home', 'house',
    'vehicle', 'drive-thru', 'parlor', 'alley',
)
# Words for something a place has or lacks whatever its text says, compared
# by tag: a task using one is drawn only at places carrying the feature tag
# it maps to, which reaches what the text never names (the flights at a
# generic customs checkpoint, the lake at a forest campground) and goals the
# default place itself cannot hold.
FEATURE_LEXICON = {
    'airport': ('airport', 'flight', 'baggage claim'),
    'bedroom': ('bedroom',),
    'basement': ('basement', 'cellar'),
    'elevator': ('elevator', 'escalator'),
    'lobby': ('lobby', 'lobbies'),
    'upstairs': ('upstairs', 'upper floor', 'second floor', 'top floor'),
    'parking': ('parking', 'car park', 'valet'),
    'terrace': ('terrace', 'patio', 'balcony', 'balconies'),
    'lake': ('lake', 'lakeside', 'canoe', 'kayak'),
    'seaside': ('beach', 'beachside', 'seaside', 'ocean', 'boardwalk', 'coastal', 'coast'),
    'highway': ('highway', 'motorway', 'freeway', 'expressway'),
    'swimming_pool': ('pool', 'lap lane'),
    'hospital': ('hospital', 'radiology', 'laboratory', 'laboratories', 'blood lab',
                 'blood draw', 'blood donor', 'blood drive', 'MRI'),
    'big_screen': ('IMAX', '3D', 'Dolby', 'blockbuster'),
    'arcade': ('arcade',),
    'culinary_school': ('culinary school', 'culinary academy', 'cooking school'),
    'cafe_seating': ('café', 'cafe'),
    # A big-format venue: a main concourse, a lumber counter, a park hopper.
    'large': ('concourse', 'lumber', 'tool rental', 'park hopper', 'water park'),
    'lumber_yard': ('lumber yard',),
}
# Phrases that contain a lexicon word without naming the place's own thing: a
# tourist desk at the station still hands out a city-center map, a hardware
# store's "home" is the learner's, a wine flight never leaves the ground.
_NOT_A_VENUE = re.compile(
    r'\b(?:city cent(?:er|re)|home improvement|(?:tasting|wine|ice cream) flights?'
    r'|beach read\w*|(?:billiard )?pool tables?|(?:option|bonus|talent|car|share|salary|equity) pools?'
    r'|3d print\w*|shopping arcades?)\b', re.I)


def _term_re(spellings) -> re.Pattern:
    words = '|'.join(re.escape(w) for w in spellings)
    return re.compile(r'\b(?:' + words + r')(?:s|es)?\b', re.I)


_TERMS = {(t if isinstance(t, str) else t[0]): _term_re((t,) if isinstance(t, str) else t)
          for t in PLACE_LEXICON}
_FEATURES = {tag: _term_re(spellings) for tag, spellings in FEATURE_LEXICON.items()}
LEXICON_TERMS = frozenset(_TERMS) | frozenset(_FEATURES)


def venue_terms(text: str) -> set:
    """The PLACE_LEXICON terms a piece of text uses, by each term's first spelling."""
    text = _NOT_A_VENUE.sub(' ', text)
    return {term for term, rx in _TERMS.items() if rx.search(text)}


def feature_terms(text: str) -> set:
    """The feature tags whose FEATURE_LEXICON words a piece of text uses."""
    text = _NOT_A_VENUE.sub(' ', text)
    return {tag for tag, rx in _FEATURES.items() if rx.search(text)}


def _task_text(t) -> str:
    return f'{t.goal} {t.hint} {t.done_when}'


def place_gaps(task, place, default_place, required=()) -> set:
    """The lexicon terms `task` uses that `place` lacks: venue words the
    default place's text has and this place's text does not, and feature
    tags the place does not carry (unless `required` negates them — the
    task then names something elsewhere on purpose)."""
    text = _task_text(task)
    words = venue_terms(text) & venue_terms(default_place.text) - venue_terms(place.text)
    feats = {f for f in feature_terms(text)
             if f not in place.tags and '!' + f not in required}
    return words | feats


_NAMED = re.compile(r'\bnamed ([A-Z][a-z]+)\b')


def _named_npc_problems(aid, scenario, personas) -> list:
    """A role that names its NPC ("named Alex") and tasks that use the
    name ("Ask if Alex picked up your package") hold every persona on the
    archetype to that first name, and to the role that states it — or the
    learner is sent to talk to Alex while Yumi answers."""
    m = _NAMED.search(scenario.role)
    if not m:
        return []
    name = m.group(1)
    rx = re.compile(r'\b' + name + r'\b')
    if not any(rx.search(_task_text(t)) for t in scenario.tasks):
        return []
    return [f'{aid}: tasks name the NPC {name!r} but persona {c.id} is {c.persona.name_en!r}'
            for c in personas
            if c.persona.name_en.split()[0] != name or c.role != scenario.role]


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
        bad = sorted({r.lstrip('!') for r in e.requires_place_tags} - PLACE_TAGS)
        if bad:
            out.append(f'event {e.id}: tags outside the vocabulary {bad}')
        if not e.text.strip() or not _ja(e.translations):
            out.append(f'event {e.id}: missing English or Japanese text')
        for aid in e.archetypes:
            if aid not in parts.archetypes:
                out.append(f'event {e.id}: unknown archetype {aid!r}')
        hosts = [aid for aid in (e.archetypes or parts.archetypes)
                 if aid in parts.archetypes
                 and any(fits(e.requires_place_tags, p.tags)
                         for p in parts.eligible_places(aid))]
        if not hosts:
            out.append(f'event {e.id}: no eligible place can host it')

    for aid, a in parts.archetypes.items():
        bad = sorted({r.lstrip('!') for r in a.requires_place_tags} - PLACE_TAGS)
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
                                 or char.persona is not None
                                 or _ja(char.speaker_translations) != speaker_label(s.speaker, 'Japanese')):
            out.append(f'{aid}: default character {char.id} differs from the scenario — re-run extract_parts')
        own = {e.text for e in parts.events.values() if aid in e.archetypes}
        lost = [c for c in s.complications if c not in own]
        if lost:
            out.append(f'{aid}: complications missing from events {lost} — re-run extract_parts')
        out += _named_npc_problems(aid, s, personas)

        goals = {t.goal for t in s.tasks}
        needs = a.goal_requires_place_tags
        for g, req in needs.items():
            if g not in goals:
                out.append(f'{aid}: place requirement for a goal that is not its task {g!r}')
            bad = sorted({r.lstrip('!') for r in req} - PLACE_TAGS)
            if bad:
                out.append(f'{aid}: goal {g!r} requires tags outside the vocabulary {bad}')
            elif not any(fits(req, p.tags) for p in eligible):
                out.append(f'{aid}: goal {g!r} fits no eligible place')
            elif all(fits(req, p.tags) for p in eligible):
                out.append(f'{aid}: goal {g!r} requires {list(req)}, which every eligible place meets')
            elif place is not None and not fits(req, place.tags):
                out.append(f'{aid}: goal {g!r} is not drawn at the default place '
                           f'{place.id}, so the default composition loses a legacy task')
        by_goal = {t.goal: t for t in s.tasks}
        for g, terms in a.lexicon_waivers.items():
            t = by_goal.get(g)
            if t is None:
                out.append(f'{aid}: lexicon waiver for a goal that is not its task {g!r}')
                continue
            used = venue_terms(_task_text(t)) | feature_terms(_task_text(t))
            idle = sorted(set(terms) - used)
            if idle:
                out.append(f'{aid}: goal {g!r} waives terms it does not use {idle}')
        if place is None:
            continue
        drawn = {p.id: 0 for p in eligible}
        for t in s.tasks:
            req = needs.get(t.goal, ())
            waived = set(a.lexicon_waivers.get(t.goal, ()))
            gaps = {}
            for p in eligible:
                if not fits(req, p.tags):
                    continue
                drawn[p.id] += 1
                for term in place_gaps(t, p, place, req):
                    gaps.setdefault(term, []).append(p.id)
            for term, pids in sorted(gaps.items()):
                if term not in waived:
                    out.append(f'{aid}: goal {t.goal!r} names {term!r} but is drawn at {pids}')
            used = venue_terms(_task_text(t)) | feature_terms(_task_text(t))
            unneeded = sorted(waived & used - set(gaps))
            if unneeded:
                out.append(f'{aid}: goal {t.goal!r} waives {unneeded}, which no place '
                           f'it is drawn at lacks')
        for pid, n in drawn.items():
            if n < MIN_PLACE_FREE_TASKS:
                out.append(f'{aid}: {n} goals drawn at {pid} (want ≥{MIN_PLACE_FREE_TASKS})')
    return out


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
    bound = sum(len(a.goal_requires_place_tags) for a in parts.archetypes.values())
    waived = sum(len(a.lexicon_waivers) for a in parts.archetypes.values())
    print(f'✅ SCENE PARTS OK — {len(parts.archetypes)} archetypes, {len(parts.places)} places, '
          f'{personas} personas, {len(parts.events)} events, {bound} goals with place '
          f'requirements, {waived} with lexicon waivers')
    return True


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
