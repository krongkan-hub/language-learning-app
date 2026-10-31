"""Scene parts (app/scenarios/parts): the loader, the invariants
dev/checks/check_parts.py holds them to, and the extractor that seeds them.

Each invariant test breaks one thing in an otherwise clean copy of the real
pools and asserts check_parts names it — a check that cannot fail is the
failure dev/checks/check_rule_vacuity.py exists to catch elsewhere.
"""
import dataclasses
import json

import pytest

from app.scenarios.models import Task
from app.scenarios.parts import (PARTS_DIR, Archetype, Character, Event, Persona, Place,
                                 load_parts)
from dev.checks.check_parts import (flag_place_bound, problems, scenarios_by_archetype,
                                    venue_terms)
from dev.tools.extract_parts import extract, slug


@pytest.fixture(scope='module')
def parts():
    return load_parts()


@pytest.fixture(scope='module')
def scenarios():
    return scenarios_by_archetype()


def _raw():
    return {name: json.loads((PARTS_DIR / f'{name}.json').read_text(encoding='utf-8'))
            for name in ('archetypes', 'places', 'characters', 'events')}


def _with(parts, **pools):
    return dataclasses.replace(parts, **pools)


def test_the_committed_pools_are_clean(parts, scenarios):
    assert problems(parts, scenarios, _raw()) == []


def test_loader_builds_typed_pools(parts):
    assert len(parts.archetypes) == 80
    a = parts.archetypes['scenario_01']
    assert isinstance(a, Archetype)
    assert isinstance(parts.places[a.default_place], Place)
    default = parts.characters[a.default_character]
    assert isinstance(default, Character) and default.persona is None
    personas = [c for c in parts.characters_for('scenario_01') if c.persona]
    assert personas and all(isinstance(c.persona, Persona) for c in personas)
    assert all(isinstance(e, Event) for e in parts.events.values())


def test_default_parts_restate_their_scenario(parts, scenarios):
    for aid, s in scenarios.items():
        a = parts.archetypes[aid]
        assert parts.places[a.default_place].text == s.place
        char = parts.characters[a.default_character]
        assert (char.role, char.speaker) == (s.role, s.speaker)


def test_eligible_places_cover_the_required_tags(parts):
    for aid, a in parts.archetypes.items():
        eligible = parts.eligible_places(aid)
        assert parts.places[a.default_place] in eligible
        assert all(set(a.requires_place_tags) <= set(p.tags) for p in eligible)


def test_events_for_respects_archetype_and_place_tags(parts):
    indoor = parts.archetypes['scenario_01'].default_place
    got = {e.id for e in parts.events_for('scenario_01', indoor)}
    assert 's01_menu_item_out_of_stock' in got
    assert 's02_flight_delayed' not in got            # another archetype's
    assert 'amb_air_conditioning' in got              # ambient, needs indoor
    assert 'amb_sudden_rain' not in got               # ambient, needs outdoor
    rooftop = 'rooftop_restaurant_with_view_over_city'
    assert 'amb_sudden_rain' in {e.id for e in parts.events_for('scenario_01', rooftop)}


def test_duplicate_ids_are_reported(parts, scenarios):
    raw = _raw()
    raw['places'].append(dict(raw['places'][0]))
    assert any('appears 2 times' in p for p in problems(parts, scenarios, raw))


def test_a_tag_outside_the_vocabulary_is_reported(parts, scenarios):
    pid = parts.archetypes['scenario_03'].default_place
    places = dict(parts.places)
    places[pid] = dataclasses.replace(places[pid], tags=places[pid].tags + ('cafe_typo',))
    found = problems(_with(parts, places=places), scenarios)
    assert any(pid in p and 'cafe_typo' in p for p in found)


def test_too_few_eligible_places_is_reported(parts, scenarios):
    keep = parts.archetypes['scenario_03'].default_place
    places = {pid: p for pid, p in parts.places.items()
              if 'cafe' not in p.tags or pid == keep}
    found = problems(_with(parts, places=places), scenarios)
    assert any('scenario_03: 1 eligible places' in p for p in found)


def test_too_few_personas_is_reported(parts, scenarios):
    chars = {cid: c for cid, c in parts.characters.items()
             if not ('scenario_05' in c.archetypes and c.persona)}
    found = problems(_with(parts, characters=chars), scenarios)
    assert any('scenario_05: 0 personas' in p for p in found)


def test_missing_japanese_is_reported_on_every_kind_of_part(parts, scenarios):
    pid = next(iter(parts.places))
    cid = next(c for c in parts.characters if parts.characters[c].persona)
    eid = next(iter(parts.events))
    places = dict(parts.places)
    places[pid] = dataclasses.replace(places[pid], translations={})
    chars = dict(parts.characters)
    chars[cid] = dataclasses.replace(chars[cid], speaker_translations={'Japanese': ' '})
    events = dict(parts.events)
    events[eid] = dataclasses.replace(events[eid], translations={})
    found = problems(_with(parts, places=places, characters=chars, events=events), scenarios)
    for part_id in (pid, cid, eid):
        assert any(part_id in p and 'Japanese' in p for p in found), part_id


def test_dangling_references_are_reported(parts, scenarios):
    archetypes = dict(parts.archetypes)
    archetypes['scenario_02'] = dataclasses.replace(
        archetypes['scenario_02'], default_place='nowhere', default_character='nobody')
    found = problems(_with(parts, archetypes=archetypes), scenarios)
    assert any("unknown default place 'nowhere'" in p for p in found)
    assert any("unknown default character 'nobody'" in p for p in found)


def test_an_event_no_place_can_host_is_reported(parts, scenarios):
    events = dict(parts.events)
    events['amb_test'] = Event(id='amb_test', kind='complication', text='x',
                               translations={'Japanese': 'x'},
                               requires_place_tags=('outdoor', 'table_service', 'airport'),
                               archetypes=())
    found = problems(_with(parts, events=events), scenarios)
    assert any('amb_test: no eligible place' in p for p in found)


def test_a_dropin_event_is_not_accepted_yet(parts, scenarios):
    eid = next(iter(parts.events))
    events = dict(parts.events)
    events[eid] = dataclasses.replace(events[eid], kind='dropin')
    assert any("kind 'dropin'" in p for p in problems(_with(parts, events=events), scenarios))


def test_a_drifted_default_is_reported(parts, scenarios):
    pid = parts.archetypes['scenario_04'].default_place
    places = dict(parts.places)
    places[pid] = dataclasses.replace(places[pid], text='A pharmacy on the moon')
    found = problems(_with(parts, places=places), scenarios)
    assert any('scenario_04: default place' in p and 'extract_parts' in p for p in found)


def test_an_unflagged_place_bound_goal_is_reported(parts, scenarios):
    archetypes = dict(parts.archetypes)
    a = archetypes['scenario_75']
    assert a.place_bound_goals
    archetypes['scenario_75'] = dataclasses.replace(a, place_bound_goals=())
    found = problems(_with(parts, archetypes=archetypes), scenarios)
    assert any('scenario_75: lexicon flags' in p for p in found)


def test_a_place_bound_goal_must_be_a_task(parts, scenarios):
    archetypes = dict(parts.archetypes)
    archetypes['scenario_01'] = dataclasses.replace(
        archetypes['scenario_01'], place_bound_goals=('Order a unicorn',))
    found = problems(_with(parts, archetypes=archetypes), scenarios)
    assert any("not its tasks ['Order a unicorn']" in p for p in found)


def _task(goal, hint='', done_when=''):
    return Task(goal=goal, hint=hint, done_when=done_when)


def test_lexicon_flags_a_venue_the_other_place_lacks():
    tasks = [_task('Ask what time the vineyard closes'),
             _task('Order a glass of red', hint='Ask the sommelier')]
    assert flag_place_bound(tasks, 'A vineyard tasting room',
                            ['An urban wine bar']) == ['Ask what time the vineyard closes']
    # Every other place keeps the venue word: nothing is place-bound.
    assert flag_place_bound(tasks, 'A vineyard tasting room',
                            ['A hilltop vineyard tasting room']) == []


def test_lexicon_spellings_and_non_venue_phrases():
    assert 'beach' in venue_terms('a scenic coastal trail')
    assert 'beach' in venue_terms('A beachside bicycle rental kiosk')
    assert 'harbor' in venue_terms('the ferry docks')
    assert 'center' not in venue_terms('a city center walking map')
    assert 'home' not in venue_terms('A home improvement hardware store')


def test_extractor_reproduces_the_committed_pools(scenarios):
    """Re-running extract_parts over the committed files changes nothing:
    the seeded fields agree with the scenarios and every curated field
    survives the merge."""
    raw = _raw()
    assert extract(scenarios, json.loads(json.dumps(raw))) == raw


def test_extractor_seeds_from_nothing(scenarios):
    out = extract(scenarios, {n: [] for n in ('archetypes', 'places', 'characters', 'events')})
    assert len(out['archetypes']) == len(out['places']) == len(out['characters']) == 80
    assert sum(len(s.complications) for s in scenarios.values()) == len(out['events'])
    first = out['archetypes'][0]
    assert first['default_place'] == slug(scenarios['scenario_01'].place)
    assert first['place_bound_goals'] == []           # no tags yet, no other places


def test_extractor_drops_a_complication_the_scenario_dropped(scenarios):
    raw = _raw()
    raw['events'].append({'id': 's01_gone', 'kind': 'complication', 'text': 'gone',
                          'translations': {'Japanese': 'なし'},
                          'requires_place_tags': [], 'archetypes': ['scenario_01']})
    out = extract(scenarios, raw)
    assert 's01_gone' not in {e['id'] for e in out['events']}
