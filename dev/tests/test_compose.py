"""Composed scenes (app/scenarios/compose.py): the default composition is the
legacy scenario, a seed reproduces its scene and tasks, every draw keeps the
part constraints, and a spec survives a round trip and a vanished part."""
import hashlib
import random

import pytest

from app.scenarios.builtins import scenarios_by_archetype
from app.scenarios.compose import (PARTS, SceneSpec, compose, compose_from_spec,
                                   default_spec)
from app.scenarios.parts import fits

LEGACY = scenarios_by_archetype()


@pytest.mark.parametrize('aid', sorted(LEGACY))
def test_default_composition_is_the_legacy_scenario(aid):
    scenario, spec = compose_from_spec(default_spec(aid))
    assert scenario == LEGACY[aid]
    assert [t.goal for t in scenario.tasks] == [t.goal for t in LEGACY[aid].tasks]
    assert scenario.speaker_translations == {}
    assert spec == default_spec(aid)


def _draw(aid, seed):
    scenario, spec = compose(aid, random.Random(seed))
    random.seed(seed)
    return scenario, spec, [t.goal for t in scenario.get_session_tasks()]


def test_same_seed_same_scene_and_tasks():
    for i, aid in enumerate(sorted(LEGACY)):
        assert _draw(aid, i) == _draw(aid, i)


def test_seeds_vary_the_scene():
    specs = {compose('scenario_01', random.Random(s))[1].signature() for s in range(50)}
    assert len(specs) > 5


def test_constraints_hold_over_10k_seeds():
    rng = random.Random(20261101)
    ids = sorted(LEGACY)
    for _ in range(10_000):
        aid = rng.choice(ids)
        scenario, spec = compose(aid, rng)
        a = PARTS.archetypes[aid]
        place = PARTS.places[spec.place]
        assert fits(a.requires_place_tags, place.tags)
        assert aid in PARTS.characters[spec.character].archetypes
        for eid in spec.events:
            e = PARTS.events[eid]
            assert fits(e.requires_place_tags, place.tags)
            assert not e.archetypes or aid in e.archetypes
        assert sum(not PARTS.events[e].archetypes for e in spec.events) <= 1
        assert all(PARTS.goal_fits(aid, t.goal, place.id) for t in scenario.tasks)
        assert scenario.place == place.text


def test_session_tasks_never_draw_an_unfit_goal():
    # scenario_02's "express bus to the airport" goal is kept away from the airport.
    unfit = {(aid, pid) for aid, a in PARTS.archetypes.items() if a.goal_requires_place_tags
             for pid in (p.id for p in PARTS.eligible_places(aid))
             if any(not PARTS.goal_fits(aid, g, pid) for g in a.goal_requires_place_tags)}
    assert unfit
    for aid, pid in sorted(unfit):
        spec = SceneSpec(archetype=aid, place=pid, character=PARTS.archetypes[aid].default_character,
                         events=())
        scenario, _ = compose_from_spec(spec)
        for seed in range(20):
            random.seed(seed)
            assert all(PARTS.goal_fits(aid, t.goal, pid) for t in scenario.get_session_tasks())


def test_spec_round_trip():
    for seed in range(200):
        scenario, spec = compose(f'scenario_{seed % 80 + 1:02d}', random.Random(seed))
        again = SceneSpec.from_dict(spec.as_dict())
        assert again == spec
        assert compose_from_spec(again) == (scenario, spec)


def test_missing_parts_fall_back_to_defaults():
    aid = 'scenario_01'
    a = PARTS.archetypes[aid]
    scenario, spec = compose_from_spec(SceneSpec(
        archetype=aid, place='gone_place', character='gone_character',
        events=('gone_event', 's01_long_kitchen_wait'), seed=7))
    assert (spec.place, spec.character) == (a.default_place, a.default_character)
    assert spec.events == ('s01_long_kitchen_wait',)
    assert spec.seed == 7
    assert scenario.place == LEGACY[aid].place and scenario.role == LEGACY[aid].role


def test_a_place_or_character_off_the_archetype_falls_back():
    aid = 'scenario_01'
    a = PARTS.archetypes[aid]
    other = PARTS.archetypes['scenario_02']
    _, spec = compose_from_spec(SceneSpec(archetype=aid, place=other.default_place,
                                          character=other.default_character,
                                          events=('amb_sudden_rain',)))
    assert (spec.place, spec.character) == (a.default_place, a.default_character)
    assert spec.events == ()                        # the indoor default place has no rain


def test_signature_ignores_the_seed_and_is_stable():
    spec = SceneSpec(archetype='scenario_01', place='fine_dining_restaurant',
                     character='waiter_01', events=('s01_long_kitchen_wait',), seed=1)
    assert spec.signature() == SceneSpec.from_dict({**spec.as_dict(), 'seed': 99}).signature()
    canon = ('{"archetype":"scenario_01","character":"waiter_01","dropin":null,'
             '"events":["s01_long_kitchen_wait"],"place":"fine_dining_restaurant","v":1}')
    assert spec.signature() == hashlib.sha1(canon.encode()).hexdigest()[:10] == '852ee06a99'
    assert spec.signature() != SceneSpec(archetype='scenario_01', place='fine_dining_restaurant',
                                         character='waiter_01', events=()).signature()


def test_a_persona_names_the_npc_in_role_and_labels():
    c = PARTS.characters['henri_dubois_01']
    a = PARTS.archetypes['scenario_01']
    scenario, _ = compose_from_spec(SceneSpec(archetype='scenario_01', place=a.default_place,
                                              character=c.id, events=()))
    assert scenario.speaker == 'Henri Dubois (Waiter)'
    assert scenario.speaker_translations == {'Japanese': 'アンリ・デュボワ（ウェイター）'}
    assert scenario.role.startswith(LEGACY['scenario_01'].role)
    assert 'Henri Dubois' in scenario.role and c.persona.trait in scenario.role
    assert scenario.name == LEGACY['scenario_01'].name   # the default place keeps the name


def test_a_label_that_already_names_the_persona_is_kept():
    scenario, _ = compose_from_spec(SceneSpec(
        archetype='scenario_75', place=PARTS.archetypes['scenario_75'].default_place,
        character='ryuji_kato_75', events=()))
    assert scenario.speaker == 'Officer Kato'
    assert scenario.speaker_translations == {'Japanese': '加藤巡査'}


def test_a_drawn_place_names_the_scene():
    aid = 'scenario_01'
    scenario, _ = compose_from_spec(SceneSpec(
        archetype=aid, place='rooftop_restaurant_with_view_over_city',
        character='waiter_01', events=()))
    place = PARTS.places['rooftop_restaurant_with_view_over_city']
    assert scenario.name == f"{LEGACY[aid].name} · {place.text}"
    assert scenario.name_translations['Japanese'] == (
        f"{LEGACY[aid].name_translations['Japanese']} · {place.translations['Japanese']}")
    assert scenario.place_translations == place.translations
