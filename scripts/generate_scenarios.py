import json
import re
import ollama
import httpx
import time
import sys

BASE_MODEL = 'qwen3:8b'

# ---------------------------------------------------------------------------
# System Prompt & Few-Shot Examples
# ---------------------------------------------------------------------------

GENERATOR_SYS = """\
You are a Game Master for a language-learning role-play application. The learner
will practice conversation in a real-world setting defined by the TOPIC below.

Your job: design ONE complete scenario with exactly these parts:

1. **name** — a short, evocative name for the setting (2-4 words).
2. **place** — a one-sentence description of the physical location.
3. **role** — "You are a ..." sentence defining the NPC the AI will play.
4. **speaker** — a single word: the NPC's role title (e.g. "Clerk", "Waiter").
5. **complications** — a JSON array of 4-5 short strings. Each is a realistic
   obstacle the NPC might face (out of stock, system down, policy limit, etc.).
6. **tasks** — a JSON array of exactly 40 task objects (see format below).

TASK FORMAT — every task is a JSON object with these keys:
- "goal": a short, specific instruction for the learner (what they must say/do).
- "hint": a longer coaching sentence giving context and strategy.
- "done_when": a sentence starting with "Learner " that describes the observable
  speech act the judge will look for. For multi-clause advanced tasks, join
  clauses with " AND ". EVERY done_when MUST start with "Learner".
- "difficulty": either "standard" (simple request) or "advanced" (negotiation, etc.).
  CRITICAL: You MUST include exactly 20 "standard" tasks and exactly 20 "advanced" tasks.
- "phase": integer 1, 2, or 3.
  1 = opening tasks. CRITICAL: Include exactly 10 phase-1 tasks.
  2 = middle tasks. CRITICAL: Include exactly 20 phase-2 tasks. (At least 10 must be reactive: false)
  3 = closing tasks. CRITICAL: Include exactly 10 phase-3 tasks.
- "reactive": boolean. true if the task presupposes something already happened.
  CRITICAL: Include exactly 15 reactive tasks overall.
- "scene_hint": a string. Non-empty ONLY when the task requires an ambient
  environmental condition (loud noise, a dirty surface) that the NPC must establish.

CRITICAL REQUIREMENT: Every single "done_when" string MUST BE COMPLETELY UNIQUE. Do not repeat any "done_when" text across tasks.

BENCHMARK / EXAMPLES OF HIGH-QUALITY TASKS (From "Coffee Shop" setting):

{"goal": "Ask for the price", "hint": "You need information. Ask how much it costs.", "done_when": "Learner asked about the price or total.", "difficulty": "standard", "phase": 2, "reactive": false, "scene_hint": ""}
{"goal": "Pay with a credit card", "hint": "You need to communicate this. Say you'll pay by card.", "done_when": "Learner mentioned paying with a card.", "difficulty": "standard", "phase": 3, "reactive": false, "scene_hint": ""}
{"goal": "Say you changed your mind about the order", "hint": "You need to communicate this. Say you want to change your order.", "done_when": "Learner expressed a change of mind.", "difficulty": "standard", "phase": 2, "reactive": true, "scene_hint": ""}
{"goal": "Say the music is too loud", "hint": "You have a delicate request. Politely ask them to turn down the music.", "done_when": "Learner complained about loud music.", "difficulty": "standard", "phase": 2, "reactive": false, "scene_hint": "music is playing over the shop's speakers, and it's turned up high — upbeat and loud enough to talk over."}
{"goal": "Negotiate when your order isn't available", "hint": "The size or drink you want is out of stock. Weigh it against an alternative, and commit to one.", "done_when": "Learner acknowledged the unavailability AND compared it to an alternative AND committed to a substitute with a reason.", "difficulty": "advanced", "phase": 2, "reactive": true, "scene_hint": ""}
{"goal": "Dispute a billing mistake", "hint": "You were charged for something you didn't order. Point out exactly what's wrong, and ask for it to be corrected.", "done_when": "Learner identified the specific billing error AND requested a correction, without being accusatory.", "difficulty": "advanced", "phase": 3, "reactive": false, "scene_hint": ""}
{"goal": "Escalate after the first fix wasn't enough", "hint": "Your first request for a fix wasn't sufficient. Push back and explain why the first offer doesn't solve it.", "done_when": "Learner acknowledged the initial response AND explained why it was insufficient AND asked for a further remedy.", "difficulty": "advanced", "phase": 2, "reactive": true, "scene_hint": ""}
{"goal": "Weigh a health trade-off out loud", "hint": "You're deciding between two drinks for a specific reason (caffeine, sugar, etc). Explain the trade-off and ask for their opinion.", "done_when": "Learner explained a personal constraint relevant to the choice AND asked for the barista's recommendation based on it.", "difficulty": "advanced", "phase": 2, "reactive": false, "scene_hint": ""}

OUTPUT: respond with a single valid JSON object — no commentary, no markdown fences, no explanation. Just the raw JSON.
"""

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_scenario_json(data: dict) -> None:
    for key in ('name', 'place', 'role', 'speaker', 'tasks'):
        if key not in data or not data[key]:
            raise ValueError(f"Missing or empty top-level key: '{key}'")
    for key in ('name', 'place', 'role', 'speaker'):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"'{key}' must be a non-empty string")

    if not isinstance(data.get('complications', []), list) or len(data['complications']) < 4:
        raise ValueError("'complications' must be a list of at least 4 items")

    tasks = data['tasks']
    if not isinstance(tasks, list) or len(tasks) < 40:
        raise ValueError(f"Need at least 40 tasks, got {len(tasks) if isinstance(tasks, list) else 'non-list'}")

    valid_difficulties = {'standard', 'advanced'}
    valid_phases = {1, 2, 3}

    advanced_count = 0
    phase_1_count = 0
    phase_3_count = 0
    reactive_count = 0
    non_reactive_phase_2 = 0
    done_whens = set()

    for i, t in enumerate(tasks):
        for field in ('goal', 'hint', 'done_when'):
            if not isinstance(t.get(field), str) or not t[field].strip():
                raise ValueError(f"Task {i}: missing or empty '{field}'")
        
        dw = t['done_when'].strip()
        if not dw.startswith('Learner'):
            raise ValueError(f"Task {i}: done_when must start with 'Learner'")
        if dw in done_whens:
            raise ValueError(f"Task {i}: duplicate done_when '{dw}'")
        done_whens.add(dw)
        
        if t.get('difficulty', 'standard') not in valid_difficulties:
            raise ValueError(f"Task {i}: invalid difficulty '{t.get('difficulty')}'")
        if t.get('phase', 2) not in valid_phases:
            raise ValueError(f"Task {i}: invalid phase '{t.get('phase')}'")
        if not isinstance(t.get('reactive', False), bool):
            raise ValueError(f"Task {i}: 'reactive' must be boolean")
        
        if t.get('difficulty') == 'advanced': advanced_count += 1
        if t.get('phase') == 1: phase_1_count += 1
        if t.get('phase') == 3: phase_3_count += 1
        if t.get('reactive'): reactive_count += 1
        if t.get('phase') == 2 and not t.get('reactive'):
            non_reactive_phase_2 += 1

    if advanced_count < 10:
        raise ValueError(f"Need at least 10 advanced tasks, got {advanced_count}")
    if phase_1_count < 4:
        raise ValueError(f"Need at least 4 phase-1 tasks, got {phase_1_count}")
    if phase_3_count < 4:
        raise ValueError(f"Need at least 4 phase-3 tasks, got {phase_3_count}")
    if reactive_count < 5:
        raise ValueError(f"Need at least 5 reactive tasks, got {reactive_count}")
    if non_reactive_phase_2 < 5:
        raise ValueError(f"Need at least 5 non-reactive phase-2 tasks, got {non_reactive_phase_2}")

# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    start = text.find('{')
    if start == -1:
        raise ValueError("No JSON object found")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("Unterminated JSON object")


def generate_scenario(topic: str, max_attempts: int = 5) -> dict:
    client = ollama.Client(timeout=httpx.Timeout(300.0, connect=10.0))
    prompt = f"TOPIC: {topic}\nTARGET LANGUAGE for all task text: English."
    
    for attempt in range(max_attempts):
        try:
            print(f"  Attempt {attempt + 1}/{max_attempts} for topic: {topic}")
            response = client.chat(
                model=BASE_MODEL,
                messages=[
                    {"role": "system", "content": GENERATOR_SYS},
                    {"role": "user", "content": prompt},
                ]
            )
            raw = response['message']['content']
            data = _extract_json(raw)
            validate_scenario_json(data)
            return data
        except Exception as e:
            print(f"  [Error]: {e}")
            
    raise RuntimeError(f"Failed to generate valid scenario for {topic} after {max_attempts} attempts.")


# ---------------------------------------------------------------------------
# Appending to scenarios.py
# ---------------------------------------------------------------------------

def escape_str(s: str) -> str:
    s = s.replace('"', '\\"')
    return f'"{s}"'

def format_python_code(data: dict, var_prefix: str) -> tuple[str, str]:
    tasks_var = f"{var_prefix}_tasks"
    
    tasks_code = f"\n# Scenario: {data['name']}\n{tasks_var} = [\n"
    for t in data['tasks']:
        diff = escape_str(t.get('difficulty', 'standard'))
        phase = t.get('phase', 2)
        reactive = t.get('reactive', False)
        sh = escape_str(t.get('scene_hint', ''))
        
        args = [
            escape_str(t['goal']),
            escape_str(t['hint']),
            escape_str(t['done_when'])
        ]
        
        kwargs = []
        if diff != '"standard"': kwargs.append(f"difficulty={diff}")
        if phase != 2: kwargs.append(f"phase={phase}")
        if reactive: kwargs.append(f"reactive={reactive}")
        if sh != '""': kwargs.append(f"scene_hint={sh}")
        
        if kwargs:
            tasks_code += f"    Task({', '.join(args)}, {', '.join(kwargs)}),\n"
        else:
            tasks_code += f"    Task({', '.join(args)}),\n"
    tasks_code += "]\n"

    comp_code = "[\n"
    for c in data['complications']:
        comp_code += f"            {escape_str(c)},\n"
    comp_code += "        ]"

    scenario_code = (
        f"    Scenario(\n"
        f"        name={escape_str(data['name'])},\n"
        f"        place={escape_str(data['place'])},\n"
        f"        role={escape_str(data['role'])},\n"
        f"        speaker={escape_str(data['speaker'])},\n"
        f"        tasks={tasks_var},\n"
        f"        complications={comp_code}\n"
        f"    ),"
    )
    
    return tasks_code, scenario_code

def append_to_scenarios_file(filepath: str, tasks_code: str, scenario_code: str):
    with open(filepath, 'r') as f:
        content = f.read()

    # Find the SCENARIOS = [ list start
    scenarios_list_idx = content.find("SCENARIOS = [")
    if scenarios_list_idx == -1:
        raise ValueError("Could not find 'SCENARIOS = [' in scenarios.py")
    
    # Insert tasks_code right before SCENARIOS = [
    new_content = content[:scenarios_list_idx] + tasks_code + "\n" + content[scenarios_list_idx:]
    
    # We now have to find the ending bracket of the SCENARIOS list in the new content
    # A simple approach since the file is well-formed is to look for the last ']' in the file, 
    # but we need to make sure we don't pick up something else. 
    # Let's find SCENARIOS = [ again in new_content, then match brackets or just find the final ']'
    start_idx = new_content.find("SCENARIOS = [")
    bracket_idx = new_content.find('[', start_idx)
    depth = 0
    end_idx = -1
    for i in range(bracket_idx, len(new_content)):
        if new_content[i] == '[':
            depth += 1
        elif new_content[i] == ']':
            depth -= 1
            if depth == 0:
                end_idx = i
                break
                
    if end_idx == -1:
        raise ValueError("Could not find closing bracket for SCENARIOS list")

    # Insert scenario_code right before the closing bracket
    final_content = new_content[:end_idx] + scenario_code + "\n" + new_content[end_idx:]
    
    with open(filepath, 'w') as f:
        f.write(final_content)

# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test-run', action='store_true', help="Run only 1 topic to test")
    args = parser.parse_args()

    topics = [
        "Airport Customs",
        "Job Interview",
        "Dentist Appointment",
        "Renting an Apartment",
        "Reporting a Stolen Wallet",
        "Visiting a Bank",
        "Car Rental",
        "Calling Tech Support",
        "Buying Electronics",
        "Doctor's Clinic"
    ]
    
    if args.test_run:
        topics = topics[:1]
        
    for topic in topics:
        print(f"\nGenerating scenario for: {topic}")
        var_prefix = topic.lower().replace(" ", "_").replace("'", "")
        
        try:
            data = generate_scenario(topic)
            tasks_code, scenario_code = format_python_code(data, var_prefix)
            
            append_to_scenarios_file("scenarios.py", tasks_code, scenario_code)
            print(f"Successfully added {topic} to scenarios.py")
            
        except Exception as e:
            print(f"Failed to process {topic}: {e}")

if __name__ == '__main__':
    main()
