"""The front end's character kit against the catalogue and the actor prompt.

frontend/src/art draws every catalogue speaker and starts each NPC mood on a
face of its own. Both lists live in Python (app/scenarios/data, NPC_MOODS) and
are copied into TypeScript, so a new speaker or a reworded mood would silently
get a default outfit or a neutral face. These tests make that drift fail here.
"""
import glob
import json
import pathlib
import re

from app.llm.prompts import NPC_MOODS

ROOT = pathlib.Path(__file__).parent.parent.parent
ART = ROOT / 'frontend' / 'src' / 'art'


def test_every_catalogue_speaker_is_dressed():
    speakers = {json.load(open(f))['speaker']
                for f in glob.glob(str(ROOT / 'app' / 'scenarios' / 'data' / 'scenario_*.json'))}
    dressed = set(re.findall(r"'([^']+)': '[a-z]+'", (ART / 'characters.test.tsx').read_text()))
    assert speakers - dressed == set(), 'add these speakers to DRESSED in characters.test.tsx'


def test_every_npc_mood_starts_on_its_own_face():
    prefixes = re.findall(r"m\.startsWith\('([a-z]+)'\)", (ART / 'characters.ts').read_text())
    for mood in NPC_MOODS:
        assert any(mood.startswith(p) for p in prefixes), f'no face for mood: {mood!r}'
