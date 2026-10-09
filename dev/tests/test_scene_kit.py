"""The front end's scene kit against the catalogue.

frontend/src/art/scenes.ts keys a backdrop by scenario name. A scenario added
to app/scenarios/data without one would get a plain desk at best; a renamed
one would lose its backdrop silently. This makes either fail here.
"""
import glob
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent.parent


def test_every_scenario_has_a_backdrop_and_no_backdrop_is_orphaned():
    names = {json.load(open(f))['name']
             for f in glob.glob(str(ROOT / 'app' / 'scenarios' / 'data' / 'scenario_*.json'))}
    source = (ROOT / 'frontend' / 'src' / 'art' / 'scenes.ts').read_text()
    keyed = set(re.findall(r"^  '([^']+)': S\(", source, re.M))
    assert names - keyed == set(), 'scenarios with no backdrop in scenes.ts'
    assert keyed - names == set(), 'backdrops for scenarios that no longer exist'
