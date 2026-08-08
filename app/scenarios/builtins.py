import json
from pathlib import Path
from typing import List
from .models import Scenario, Task

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_scenarios() -> List[Scenario]:
    if not DATA_DIR.is_dir():
        raise RuntimeError(f"Scenario data directory missing: {DATA_DIR}")

    json_files = sorted(DATA_DIR.glob("scenario_*.json"), key=lambda p: p.name)
    if not json_files:
        raise RuntimeError(f"No scenario files found in {DATA_DIR}")

    scenarios = []
    for filepath in json_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to read/parse scenario file {filepath.name}: {e}") from e

        try:
            tasks = [
                Task(
                    goal=t["goal"],
                    hint=t["hint"],
                    done_when=t["done_when"],
                    difficulty=t["difficulty"],
                    scene_hint=t["scene_hint"],
                    phase=t["phase"],
                    reactive=t["reactive"],
                )
                for t in data["tasks"]
            ]
            scenario = Scenario(
                name=data["name"],
                place=data["place"],
                role=data["role"],
                speaker=data["speaker"],
                complications=data["complications"],
                tasks=tasks,
                name_translations=data.get("name_translations", {}),
                place_translations=data.get("place_translations", {}),
            )
        except Exception as e:
            raise RuntimeError(f"Malformed scenario content in {filepath.name}: {e}") from e

        scenarios.append(scenario)

    return scenarios


SCENARIOS: List[Scenario] = load_scenarios()
