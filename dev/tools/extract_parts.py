"""Seed and refresh the scene-part pools from the 80 scenario files.

    python3 dev/tools/extract_parts.py

Writes app/scenarios/parts/{archetypes,places,characters,events}.json. For
each scenario it (re)derives what the scenario itself states: an archetype,
its default place (place + place_translations), its default character (role,
speaker, and the speaker's label from i18n.SPEAKER_LABELS) and one
complication event per authored complication.

Everything else is curated by hand and kept: place tags, required tags, extra
places and personas, event translations and tags, alt roles, per-goal place
requirements and lexicon waivers (dev/checks/check_parts.py says which goals
need one). Re-running is safe and idempotent; only the
scenario-derived fields are overwritten.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.i18n import SPEAKER_LABELS  # noqa: E402
from app.scenarios.parts import PARTS_DIR  # noqa: E402
from dev.checks.check_parts import scenarios_by_archetype  # noqa: E402

FILES = ('archetypes', 'places', 'characters', 'events')
_SEEDED_EVENT = re.compile(r'^s\d{2}_')


def slug(text: str, words: int = 6) -> str:
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    tokens = [t for t in tokens if t not in ('a', 'an', 'the')]
    return '_'.join(tokens[:words])


def _by_id(rows: list) -> dict:
    return {r['id']: r for r in rows}


def extract(scenarios: dict, existing: dict) -> dict:
    """The four pools after merging what the scenarios state into
    `existing` (file name -> list of rows, empty lists on first run)."""
    archetypes = _by_id(existing['archetypes'])
    places = _by_id(existing['places'])
    characters = _by_id(existing['characters'])
    events = _by_id(existing['events'])

    seeded_events = set()
    for aid, s in scenarios.items():
        num = aid.split('_')[-1]
        a = archetypes.setdefault(aid, {'id': aid})
        place_id = a.get('default_place') or slug(s.place)
        place = places.setdefault(place_id, {'id': place_id, 'tags': []})
        place['text'] = s.place
        place['translations'] = {'Japanese': s.place_translations.get('Japanese', '')}

        char_id = a.get('default_character') or f'{slug(s.speaker)}_{num}'
        char = characters.setdefault(char_id, {'id': char_id})
        char.update({
            'archetypes': char.get('archetypes') or [aid],
            'role': s.role,
            'speaker': s.speaker,
            'speaker_translations': {'Japanese': SPEAKER_LABELS.get(s.speaker, '')},
            'persona': None,
        })

        for text in s.complications:
            eid = f's{num}_{slug(text)}'
            seeded_events.add(eid)
            ev = events.setdefault(eid, {'id': eid, 'kind': 'complication',
                                         'translations': {'Japanese': ''},
                                         'requires_place_tags': []})
            ev['text'] = text
            ev['archetypes'] = [aid]

        a['requires_place_tags'] = a.get('requires_place_tags', [])
        a['default_place'] = place_id
        a['default_character'] = char_id
        a['goal_requires_place_tags'] = a.get('goal_requires_place_tags', {})
        a['lexicon_waivers'] = a.get('lexicon_waivers', {})
        a['alt_roles'] = a.get('alt_roles', [])

    for eid in [e for e in events if _SEEDED_EVENT.match(e) and e not in seeded_events]:
        del events[eid]                           # the scenario dropped it

    key_order = {
        'archetypes': ('id', 'requires_place_tags', 'default_place', 'default_character',
                       'goal_requires_place_tags', 'lexicon_waivers', 'alt_roles'),
        'places': ('id', 'text', 'translations', 'tags'),
        'characters': ('id', 'archetypes', 'role', 'speaker', 'speaker_translations', 'persona'),
        'events': ('id', 'kind', 'text', 'translations', 'requires_place_tags', 'archetypes'),
    }
    pools = {'archetypes': archetypes, 'places': places,
             'characters': characters, 'events': events}
    return {name: [{k: row[k] for k in key_order[name]} for row in pool.values()]
            for name, pool in pools.items()}


def main() -> None:
    existing = {}
    for name in FILES:
        path = PARTS_DIR / f'{name}.json'
        existing[name] = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    out = extract(scenarios_by_archetype(), existing)
    PARTS_DIR.mkdir(exist_ok=True)
    for name, rows in out.items():
        (PARTS_DIR / f'{name}.json').write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'{name}: {len(rows)}')


if __name__ == '__main__':
    main()
