#!/usr/bin/env python3
"""Migrate Japanese scenario name and place translations into app/scenarios/data/scenario_NN.json files."""
import json
from pathlib import Path
import sys

def main():
    root = Path(__file__).resolve().parent.parent
    trans_path = root / "scratch" / "scenario_translations.json"
    with open(trans_path, "r", encoding="utf-8") as f:
        translations = json.load(f)

    jp_data = translations.get("Japanese", {})
    names = jp_data.get("names", [])
    places = jp_data.get("places", [])

    if len(names) != 80:
        raise ValueError(f"Expected 80 names, got {len(names)}")
    if len(places) != 80:
        raise ValueError(f"Expected 80 places, got {len(places)}")

    data_dir = root / "app" / "scenarios" / "data"
    json_files = sorted(data_dir.glob("scenario_*.json"), key=lambda p: p.name)
    if len(json_files) != 80:
        raise ValueError(f"Expected 80 scenario files, got {len(json_files)}")

    for i, filepath in enumerate(json_files):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["name_translations"] = {"Japanese": names[i]}
        data["place_translations"] = {"Japanese": places[i]}

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    print(f"Successfully migrated {len(json_files)} scenario JSON files.")

if __name__ == "__main__":
    main()
