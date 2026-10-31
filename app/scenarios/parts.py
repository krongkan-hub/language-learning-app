"""Scene parts: the pools a composed scene is drawn from.

An archetype is one of the 80 authored scenarios — the gradeable unit, since
its tasks are bound to its role. Around it the parts let a session vary what
the tasks do not depend on: the place (any place whose tags cover the
archetype's `requires_place_tags`), the character on the archetype's role (a
named persona), and ambient complications whose `requires_place_tags` the
place has. Plan: docs/plans/dynamic-scenarios.md.

Seeded from the scenario files by dev/tools/extract_parts.py and curated by
hand; dev/checks/check_parts.py holds the invariants. Nothing at runtime reads
this yet.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PARTS_DIR = Path(__file__).resolve().parent / "parts"

# The closed tag vocabulary. A place's tags are what an archetype or an event
# can require, so a misspelt tag would silently make a place ineligible
# everywhere; check_parts rejects anything not listed here.
#
# Two kinds: a venue tag names what the place IS (an archetype requires one),
# and an attribute tag describes it (ambient complications require those).
VENUE_TAGS = frozenset({
    'restaurant', 'airline_counter', 'cafe', 'pharmacy', 'hotel_desk',
    'customs', 'car_rental', 'clothing_store', 'rail_ticketing', 'clinic_reception',
    'bank', 'rental_home', 'device_repair', 'bookstore', 'hair_salon',
    'gym', 'meeting_room', 'vehicle', 'museum', 'produce_market',
    'vet', 'bakery', 'post_office', 'bike_rental', 'cinema',
    'dry_cleaner', 'police_desk', 'tourist_info', 'souvenir_shop', 'phone_store',
    'furniture_store', 'hardware_store', 'spa', 'student_office', 'library',
    'music_store', 'florist', 'ice_cream', 'drive_thru', 'winery',
    'ski_rental', 'ticket_booth', 'campground', 'gallery', 'tailor',
    'electronics_store', 'insurance_office', 'house_for_sale', 'garage', 'dental',
    'optician', 'bus_info', 'ferry', 'bowling', 'escape_room',
    'karaoke', 'tattoo', 'antique_stall', 'food_stall', 'cooking_class',
    'yoga', 'concert_box_office', 'duty_free', 'shoe_repair', 'pool',
    'garden_center', 'airport_lounge', 'coworking', 'shared_hallway', 'emergency_room',
    'roadside', 'apartment_inspection', 'port_customs', 'review_office', 'loan_office',
    'event_planner', 'interview_room', 'airline_service',
})
ATTRIBUTE_TAGS = frozenset({
    'indoor', 'outdoor', 'busy', 'quiet', 'formal', 'casual',
    'counter', 'table_service', 'queue', 'transit', 'airport', 'waterfront',
})
PLACE_TAGS = VENUE_TAGS | ATTRIBUTE_TAGS

# Drop-in characters (kind 'dropin') arrive with PR 6 of the plan.
EVENT_KINDS = ('complication',)


@dataclass(frozen=True)
class Place:
    id: str
    text: str
    translations: Dict[str, str]
    tags: Tuple[str, ...]


@dataclass(frozen=True)
class Persona:
    name_en: str
    name_ja: str
    # Model-facing notes, in English like the rest of the actor prompt.
    trait: str
    ja_register: str


@dataclass(frozen=True)
class Character:
    id: str
    archetypes: Tuple[str, ...]
    role: str
    speaker: str
    speaker_translations: Dict[str, str]
    # None for an archetype's default character, which is the scenario's own
    # role verbatim — a default composition must equal the legacy scenario.
    persona: Optional[Persona]


@dataclass(frozen=True)
class Event:
    id: str
    kind: str
    text: str
    translations: Dict[str, str]
    requires_place_tags: Tuple[str, ...]
    # Empty means any archetype whose place carries the required tags.
    archetypes: Tuple[str, ...]


@dataclass(frozen=True)
class AltRole:
    character_id: str
    threads: Tuple[str, ...]


@dataclass(frozen=True)
class Archetype:
    id: str
    requires_place_tags: Tuple[str, ...]
    default_place: str
    default_character: str
    # Goals that name something only the default place has; drawn only there.
    place_bound_goals: Tuple[str, ...]
    alt_roles: Tuple[AltRole, ...]


@dataclass(frozen=True)
class Parts:
    archetypes: Dict[str, Archetype]
    places: Dict[str, Place]
    characters: Dict[str, Character]
    events: Dict[str, Event]

    def eligible_places(self, archetype_id: str) -> List[Place]:
        need = set(self.archetypes[archetype_id].requires_place_tags)
        return [p for p in self.places.values() if need <= set(p.tags)]

    def characters_for(self, archetype_id: str) -> List[Character]:
        return [c for c in self.characters.values() if archetype_id in c.archetypes]

    def events_for(self, archetype_id: str, place_id: str) -> List[Event]:
        tags = set(self.places[place_id].tags)
        return [e for e in self.events.values()
                if (not e.archetypes or archetype_id in e.archetypes)
                and set(e.requires_place_tags) <= tags]


def _read(directory: Path, name: str) -> list:
    with open(directory / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def _persona(raw: Optional[dict]) -> Optional[Persona]:
    if raw is None:
        return None
    return Persona(name_en=raw["name_en"], name_ja=raw["name_ja"],
                   trait=raw["trait"], ja_register=raw["ja_register"])


def load_parts(directory: Path = PARTS_DIR) -> Parts:
    """Read the four part files into typed, id-keyed pools. Shape only:
    references and vocabulary are check_parts' job."""
    archetypes = {
        a["id"]: Archetype(
            id=a["id"],
            requires_place_tags=tuple(a["requires_place_tags"]),
            default_place=a["default_place"],
            default_character=a["default_character"],
            place_bound_goals=tuple(a["place_bound_goals"]),
            alt_roles=tuple(AltRole(r["character_id"], tuple(r["threads"]))
                            for r in a["alt_roles"]),
        )
        for a in _read(directory, "archetypes")
    }
    places = {
        p["id"]: Place(id=p["id"], text=p["text"], translations=p["translations"],
                       tags=tuple(p["tags"]))
        for p in _read(directory, "places")
    }
    characters = {
        c["id"]: Character(
            id=c["id"], archetypes=tuple(c["archetypes"]), role=c["role"],
            speaker=c["speaker"], speaker_translations=c["speaker_translations"],
            persona=_persona(c["persona"]),
        )
        for c in _read(directory, "characters")
    }
    events = {
        e["id"]: Event(
            id=e["id"], kind=e["kind"], text=e["text"], translations=e["translations"],
            requires_place_tags=tuple(e["requires_place_tags"]),
            archetypes=tuple(e["archetypes"]),
        )
        for e in _read(directory, "events")
    }
    return Parts(archetypes=archetypes, places=places, characters=characters, events=events)
