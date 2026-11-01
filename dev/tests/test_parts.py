"""Scene parts (app/scenarios/parts): the loader, the invariants
dev/checks/check_parts.py holds them to, and the extractor that seeds them.

Each invariant test breaks one thing in an otherwise clean copy of the real
pools and asserts check_parts names it — a check that cannot fail is the
failure dev/checks/check_rule_vacuity.py exists to catch elsewhere.
"""
import dataclasses
import json

import pytest

from app.i18n import speaker_label
from app.scenarios.models import Task
from app.scenarios.parts import (PARTS_DIR, Archetype, Character, Event, Persona, Place,
                                 fits, load_parts)
from dev.checks.check_parts import (MIN_PLACE_FREE_TASKS, feature_terms, place_gaps, problems,
                                    scenarios_by_archetype, venue_terms)
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
        assert all(fits(a.requires_place_tags, p.tags) for p in eligible)


def test_an_archetype_can_exclude_a_venue(parts):
    # An engineering interview is not held in the marketing department.
    assert 'corporate_marketing_office' in {p.id for p in parts.eligible_places('scenario_18')}
    assert 'corporate_marketing_office' not in {p.id for p in parts.eligible_places('scenario_17')}


def test_events_for_respects_archetype_and_place_tags(parts):
    indoor = parts.archetypes['scenario_01'].default_place
    got = {e.id for e in parts.events_for('scenario_01', indoor)}
    assert 's01_menu_item_out_of_stock' in got
    assert 's02_flight_delayed' not in got            # another archetype's
    assert 'amb_air_conditioning' in got              # ambient, needs indoor
    assert 'amb_sudden_rain' not in got               # ambient, needs outdoor
    rooftop = 'rooftop_restaurant_with_view_over_city'
    assert 'amb_sudden_rain' in {e.id for e in parts.events_for('scenario_01', rooftop)}


def test_an_event_can_exclude_a_place_with_a_negated_tag(parts):
    # The arrivals customs hall shows no departure boards.
    assert 'amb_departure_boards' in {e.id for e in parts.events_for('scenario_02', 'airport_check_in_counter')}
    for pid in ('customs_checkpoint', 'customs_checkpoint_in_airport_arrivals_hall'):
        assert 'amb_departure_boards' not in {e.id for e in parts.events_for('scenario_06', pid)}


def test_an_event_negating_every_host_is_reported(parts, scenarios):
    events = dict(parts.events)
    events['amb_test'] = Event(id='amb_test', kind='complication', text='x',
                               translations={'Japanese': 'x'},
                               requires_place_tags=('customs', '!airport_typo'),
                               archetypes=('scenario_06',))
    found = problems(_with(parts, events=events), scenarios)
    assert any('amb_test' in p and "outside the vocabulary ['airport_typo']" in p for p in found)
    events['amb_test'] = dataclasses.replace(events['amb_test'], requires_place_tags=('customs', '!customs'))
    found = problems(_with(parts, events=events), scenarios)
    assert any('amb_test: no eligible place' in p for p in found)


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


def test_a_persona_that_drops_the_named_npc_is_reported(parts, scenarios):
    # scenario_70's tasks say "Greet your neighbor Alex".
    chars = dict(parts.characters)
    c = chars['alex_kim_70']
    chars[c.id] = dataclasses.replace(c, persona=dataclasses.replace(c.persona, name_en='Yumi Takagi'))
    found = problems(_with(parts, characters=chars), scenarios)
    assert any("scenario_70: tasks name the NPC 'Alex' but persona alex_kim_70" in p for p in found)
    chars[c.id] = dataclasses.replace(c, role=c.role.replace(', named Alex', ''))
    found = problems(_with(parts, characters=chars), scenarios)
    assert any('persona alex_kim_70' in p for p in found)


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


def _requires(parts, aid, **fields):
    archetypes = dict(parts.archetypes)
    archetypes[aid] = dataclasses.replace(archetypes[aid], **fields)
    return _with(parts, archetypes=archetypes)


def test_a_goal_drawn_where_the_place_lacks_what_it_names_is_reported(parts, scenarios):
    a = parts.archetypes['scenario_44']
    assert a.goal_requires_place_tags
    found = problems(_requires(parts, 'scenario_44', goal_requires_place_tags={}), scenarios)
    assert any("scenario_44: goal 'Inquire about canoe and kayak" in p
               and "names 'lake'" in p and 'forest_campground_office' in p for p in found)


def test_a_feature_the_default_place_lacks_is_reported_too(parts, scenarios):
    # The ocean-view room needs the sea; without it the default place would
    # either be asked about an ocean it lacks or lose a legacy task.
    a = parts.archetypes['scenario_05']
    goal = 'Ask for a room with an ocean view'
    assert a.goal_requires_place_tags[goal] == ('seaside',)
    places = dict(parts.places)
    d = places[a.default_place]
    places[d.id] = dataclasses.replace(d, tags=tuple(t for t in d.tags if t != 'seaside'))
    found = problems(_with(parts, places=places), scenarios)
    assert any(goal in p and 'not drawn at the default place' in p for p in found)
    needs = {g: t for g, t in a.goal_requires_place_tags.items() if g != goal}
    found = problems(_requires(_with(parts, places=places), 'scenario_05',
                               goal_requires_place_tags=needs), scenarios)
    assert any(goal in p and "names 'seaside'" in p and a.default_place in p for p in found)


def test_the_default_composition_is_the_legacy_scenario(parts, scenarios):
    for aid, s in scenarios.items():
        a = parts.archetypes[aid]
        place = parts.places[a.default_place]
        assert all(parts.goal_fits(aid, t.goal, place.id) for t in s.tasks), aid
        char = parts.characters[a.default_character]
        assert char.speaker_translations['Japanese'] == speaker_label(s.speaker, 'Japanese'), aid


def test_a_default_speaker_label_unlike_the_legacy_ui_is_reported(parts, scenarios):
    cid = parts.archetypes['scenario_42'].default_character
    chars = dict(parts.characters)
    chars[cid] = dataclasses.replace(chars[cid], speaker_translations={'Japanese': 'スキーショップのスタッフ'})
    found = problems(_with(parts, characters=chars), scenarios)
    assert any(f'default character {cid} differs' in p for p in found)


def test_a_waiver_covers_a_lexicon_hit_and_must_be_used(parts, scenarios):
    a = parts.archetypes['scenario_47']
    found = problems(_requires(parts, 'scenario_47', lexicon_waivers={}), scenarios)
    assert any("names 'big_screen'" in p for p in found)
    goal = scenarios['scenario_47'].tasks[0].goal
    waivers = dict(a.lexicon_waivers, **{goal: ('lake',)})
    found = problems(_requires(parts, 'scenario_47', lexicon_waivers=waivers), scenarios)
    assert any(goal in p and "waives terms it does not use ['lake']" in p for p in found)


def test_requirements_name_tasks_known_tags_and_a_place(parts, scenarios):
    first, second = (t.goal for t in scenarios['scenario_01'].tasks[:2])
    needs = {'Order a unicorn': ('restaurant',), first: ('cafe_typo',), second: ('airport',)}
    found = problems(_requires(parts, 'scenario_01', goal_requires_place_tags=needs), scenarios)
    assert any("not its task 'Order a unicorn'" in p for p in found)
    assert any(first in p and 'outside the vocabulary' in p for p in found)
    assert any(second in p and 'fits no eligible place' in p for p in found)


def test_too_few_goals_left_at_a_place_is_reported(parts, scenarios):
    goals = [t.goal for t in scenarios['scenario_02'].tasks]
    needs = {g: ('swimming_pool',) for g in goals[MIN_PLACE_FREE_TASKS - 1:]}
    found = problems(_requires(parts, 'scenario_02', goal_requires_place_tags=needs), scenarios)
    assert any('scenario_02: ' in p and 'goals drawn at' in p for p in found)


def test_fits_reads_plain_and_negated_tags():
    assert fits((), ('indoor',))
    assert fits(('airport', 'indoor'), ('indoor', 'airport', 'busy'))
    assert not fits(('airport',), ('indoor',))
    assert fits(('!airport',), ('indoor',))
    assert not fits(('!airport',), ('airport',))


def _task(goal, hint='', done_when=''):
    return Task(goal=goal, hint=hint, done_when=done_when)


def _place(text, *tags):
    return Place(id='p', text=text, translations={}, tags=tags)


def test_place_gaps_compare_venue_words_by_text():
    task = _task('Ask what time the vineyard closes')
    default = _place('A vineyard tasting room')
    assert place_gaps(task, _place('An urban wine bar'), default) == {'vineyard'}
    assert place_gaps(task, _place('A hilltop vineyard tasting room'), default) == set()
    # A venue word the default place does not have is the archetype's, not the place's.
    assert place_gaps(_task('Ask the bar staff'), _place('An urban wine bar'), default) == set()


def test_place_gaps_compare_features_by_tag():
    task = _task('Confirm your flight details')
    default = _place('A customs checkpoint', 'airport')
    assert place_gaps(task, _place('A customs checkpoint at a ferry terminal'), default) == {'airport'}
    assert place_gaps(task, _place('A customs checkpoint', 'airport'), default) == set()
    # Negated on purpose: the airport is where the learner is going.
    assert place_gaps(task, _place('A tourist desk'), default, ('!airport',)) == set()


def test_lexicon_spellings_and_non_venue_phrases():
    assert 'seaside' in feature_terms('a scenic coastal trail')
    assert 'harbor' in venue_terms('the ferry docks')
    assert 'center' not in venue_terms('a city center walking map')
    assert 'home' not in venue_terms('A home improvement hardware store')
    assert 'airport' in feature_terms('Negotiate a delay for a connecting flight')
    assert 'airport' not in feature_terms('Inquire about wine tasting flight options')
    assert 'swimming_pool' in feature_terms('Ask if the pool is heated')
    assert 'swimming_pool' not in feature_terms('Propose a 10 percent stock option pool')
    assert 'lake' in feature_terms('Inquire about canoe rental')


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
    assert first['goal_requires_place_tags'] == {} and first['lexicon_waivers'] == {}


def test_extractor_drops_a_complication_the_scenario_dropped(scenarios):
    raw = _raw()
    raw['events'].append({'id': 's01_gone', 'kind': 'complication', 'text': 'gone',
                          'translations': {'Japanese': 'なし'},
                          'requires_place_tags': [], 'archetypes': ['scenario_01']})
    out = extract(scenarios, raw)
    assert 's01_gone' not in {e['id'] for e in out['events']}
