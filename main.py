import ollama
import re
import random
import sys
from scenarios import SCENARIOS

BASE_MODEL = 'qwen3:8b'

ACTOR_OPTS = {'temperature': 0.6, 'num_ctx': 8192}
COACH_OPTS = {'temperature': 0.2, 'num_ctx': 4096}
JUDGE_OPTS = {'temperature': 0.2, 'num_ctx': 4096}

ACTOR_SYS = """\
You are a role-play character in a language-learning conversation.

SETTING: {place}
YOUR ROLE: {role}

Rules:
- Stay fully in character. You are a real person, not an AI assistant.
- Respond ONLY in {language}.
- Say exactly 1-2 short sentences of natural, spoken dialogue, then stop.
- Always end with a question to keep the conversation going.
- Use natural everyday language with occasional intermediate-to-advanced vocabulary.
- Write ONLY spoken words. No narration, no stage directions, no asterisks,
  no parentheses, no emojis, no character name prefixes.
- Accept whatever the customer or visitor says or orders. Never refuse or
  invent excuses.
- React like a real person: have opinions, make small talk, be specific
  about your place.
- On your first turn, name the place, introduce yourself, and set the scene.
/no_think"""

COACH_SYS = """\
You are a language coach. The learner is practicing {language}.

Analyze the learner's most recent message and respond in EXACTLY this format:

💡 Feedback:
- You said: "[exact quote]" → Better: "[correction]" (reason)

If their grammar, spelling, and word choice were all perfect, write exactly:
💡 Feedback: Perfectly natural!

Rules:
- ONLY correct the learner's message. Never comment on anything else.
- Keep the learner's original pronouns (my stays my, I stays I).
- Quote their exact words before correcting.
- Maximum 2 corrections.
/no_think"""


# ---------------------------------------------------------------------------
# Sanitization & Validation
# ---------------------------------------------------------------------------

def sanitize(text: str) -> str:
    """Strip reasoning traces, stage directions, character prefixes, and emoji."""
    # 1. Remove <think>...</think> blocks (qwen3 reasoning traces)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    # 2. Remove markdown bold/italic wrapping actions: *(grins)*, **Barista:**
    text = re.sub(r'\*+[^*]*\*+', '', text)
    # 3. Remove parenthetical actions: (glancing up briefly)
    text = re.sub(r'\([^)]*\)', '', text)
    # 4. Remove leading character name prefix: "Barista: "
    text = re.sub(r'^\s*\w+:\s*', '', text, flags=re.MULTILINE)
    # 5. Remove emoji
    text = re.sub(r'[\U0001F300-\U0001F9FF\u2600-\u27BF]', '', text)
    # 6. Collapse whitespace and strip wrapping quotes
    text = re.sub(r'\s{2,}', ' ', text).strip()
    text = text.strip('"')
    return text


def validate(text: str) -> tuple[bool, str]:
    """Check sanitized actor output against format rules."""
    if not text:
        return False, "Empty response"
    if re.search(r'[*\[\]<>]', text):
        return False, "Contains residual markup characters"
    if re.search(r'[\U0001F300-\U0001F9FF\u2600-\u27BF]', text):
        return False, "Contains emoji"
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if len(sentences) > 2:
        return False, f"Too many sentences ({len(sentences)})"
    return True, ""


# ---------------------------------------------------------------------------
# LLM Call Wrappers
# ---------------------------------------------------------------------------

def call_actor(messages: list, system_prompt: str) -> str:
    """Call the actor, sanitize and validate. Retry up to 2x on failure."""
    cleaned = ""
    reason = ""
    for attempt in range(3):
        call_messages = [{"role": "system", "content": system_prompt}] + messages
        if attempt > 0:
            call_messages.append({
                "role": "system",
                "content": f"Your previous response was rejected: {reason}. "
                           "Reply with ONLY 1-2 short spoken sentences. "
                           "No asterisks, no parentheses, no character names."
            })
        response = ollama.chat(
            model=BASE_MODEL, messages=call_messages, options=ACTOR_OPTS
        )
        raw = response['message']['content']
        cleaned = sanitize(raw)
        ok, reason = validate(cleaned)
        if ok:
            return cleaned
    print("  [Warning: actor output failed validation after 3 attempts]")
    return cleaned


def call_coach(user_input: str, language: str) -> str:
    """Get language feedback on the learner's message."""
    system = COACH_SYS.format(language=language)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_input},
    ]
    response = ollama.chat(
        model=BASE_MODEL, messages=messages, options=COACH_OPTS
    )
    raw = response['message']['content']
    raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
    raw = re.sub(r'<[^>]+>', '', raw)
    return raw.strip()


# ---------------------------------------------------------------------------
# Task Evaluation (hybrid: deterministic + LLM)
# ---------------------------------------------------------------------------

def judge_deterministic(user_input: str, done_when: str):
    """Check 'used the word X' patterns via word-boundary match.

    Returns True/False for a match, or None if LLM evaluation is needed.
    """
    match = re.search(r"Learner used the word '(\w+)'", done_when)
    if match:
        word = match.group(1)
        return bool(
            re.search(rf'\b{re.escape(word)}\b', user_input, re.IGNORECASE)
        )
    return None


def judge_llm(conversation: list, done_when: str) -> bool:
    """Use LLM to evaluate task completion with last two turns as context."""
    context = conversation[-4:]
    context_str = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in context
    )
    prompt = (
        f"Given this conversation:\n{context_str}\n\n"
        f"Has this goal been met: {done_when}\n\n"
        f"Answer YES or NO only. /no_think"
    )
    try:
        response = ollama.generate(
            model=BASE_MODEL, prompt=prompt, options=JUDGE_OPTS
        )
        text = response.get('response', '').strip()
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text).strip()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        return lines[-1].upper().startswith('YES') if lines else False
    except Exception as e:
        print(f"\n[Error checking task: {e}]")
        return False


def evaluate_task(user_input: str, done_when: str, conversation: list) -> bool:
    """Evaluate task: deterministic first, LLM fallback."""
    result = judge_deterministic(user_input, done_when)
    if result is not None:
        return result
    return judge_llm(conversation, done_when)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def select_scenario():
    valid_scenarios = [s for s in SCENARIOS if len(s.tasks) > 0]
    if not valid_scenarios:
        print("Error: No scenarios with tasks found!")
        sys.exit(1)

    random_scenario = random.choice(valid_scenarios)
    print(f"\nRandomly selected scenario: {random_scenario.name}")

    choice = input("Do you want to play this scenario? (y/n): ").strip().lower()
    if choice == 'y' or choice == '':
        return random_scenario

    print("\nAvailable Scenarios:")
    for i, s in enumerate(valid_scenarios):
        print(f"{i + 1}. {s.name} ({len(s.tasks)} tasks available)")

    while True:
        try:
            sel = input("\nEnter the number of the scenario you want: ").strip()
            idx = int(sel) - 1
            if 0 <= idx < len(valid_scenarios):
                return valid_scenarios[idx]
            else:
                print("Invalid number. Try again.")
        except ValueError:
            print("Please enter a valid number.")


def main():
    print("========================================")
    print("   Language Conversation Coach CLI")
    print("========================================")

    try:
        ollama.show(BASE_MODEL)
    except ollama.ResponseError as e:
        if e.status_code == 404:
            print(f"Error: Model '{BASE_MODEL}' not found.")
            print(f"Please run: ollama pull {BASE_MODEL}")
            sys.exit(1)
        else:
            print(f"Ollama error: {e}")
            sys.exit(1)

    language = input(
        "Which language do you want to practice? (e.g., English, Japanese): "
    ).strip()
    if not language:
        language = "English"

    scenario = select_scenario()
    tasks = scenario.get_session_tasks(num_tasks=10)
    speaker = scenario.role.rstrip('.').split()[-1].capitalize()

    print(f"\nStarting Scenario: {scenario.name}")
    print(f"Place: {scenario.place}")
    print(f"Role of AI: {scenario.role}")
    print("========================================\n")

    actor_system = ACTOR_SYS.format(
        place=scenario.place, role=scenario.role, language=language
    )

    # Initial greeting — the seed "Hello." triggers the actor but is NOT
    # persisted in the conversation history.  Only the greeting itself is kept.
    print(f"[{speaker} is getting ready...]")
    try:
        seed = [{"role": "user", "content": "Hello."}]
        greeting = call_actor(seed, actor_system)
    except Exception as e:
        print(f"Failed to communicate with Ollama: {e}")
        sys.exit(1)

    messages = [{"role": "assistant", "content": greeting}]
    print(f"\n[{speaker}]: {greeting}")

    current_task_idx = 0
    total_tasks = len(tasks)

    while current_task_idx < total_tasks:
        current_task = tasks[current_task_idx]
        print(f"\n--- Task {current_task_idx + 1}/{total_tasks} ---")
        print(f"🎯 Objective: {current_task.hint}")

        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            print("Exiting...")
            break

        messages.append({"role": "user", "content": user_input})

        # 1. Actor response (knows nothing about tasks)
        print(f"\n[{speaker} is thinking...]")
        actor_reply = call_actor(messages, actor_system)
        messages.append({"role": "assistant", "content": actor_reply})
        print(f"\n[{speaker}]: {actor_reply}")

        # 2. Coach feedback (separate call, never enters conversation history)
        coach_feedback = call_coach(user_input, language)
        print(f"\n{coach_feedback}")

        # 3. Task evaluation
        is_done = evaluate_task(user_input, current_task.done_when, messages)
        if is_done:
            print(f"\n✅ TASK COMPLETED! Moving to next...")
            current_task_idx += 1
        else:
            print(f"\n❌ Task not yet completed. Keep trying!")

    if current_task_idx == total_tasks:
        print("\n========================================")
        print("🎉 CONGRATULATIONS! You completed all tasks! 🎉")
        print("========================================")


if __name__ == "__main__":
    main()
