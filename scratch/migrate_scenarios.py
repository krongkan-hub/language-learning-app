import json
from pathlib import Path
from app.scenarios.builtins import SCENARIOS

def main():
    data_dir = Path("app/scenarios/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Exporting {len(SCENARIOS)} scenarios to {data_dir}...")
    for idx, s in enumerate(SCENARIOS, start=1):
        filename = data_dir / f"scenario_{idx:02d}.json"
        s_data = {
            "name": s.name,
            "place": s.place,
            "role": s.role,
            "speaker": s.speaker,
            "complications": list(s.complications or []),
            "tasks": [
                {
                    "goal": t.goal,
                    "hint": t.hint,
                    "done_when": t.done_when,
                    "difficulty": t.difficulty,
                    "scene_hint": t.scene_hint,
                    "phase": t.phase,
                    "reactive": t.reactive,
                }
                for t in s.tasks
            ],
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(s_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
    print("Done exporting scenarios!")

if __name__ == "__main__":
    main()
