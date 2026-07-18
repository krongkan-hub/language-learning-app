import ollama
import random
import sys
from scenarios import SCENARIOS

MODEL_NAME = 'language-teacher'
JUDGE_MODEL = 'qwen3:14b'

def evaluate_task(user_input: str, goal: str) -> bool:
    """Uses a separate LLM call to check if the goal was accomplished."""
    prompt = f"""
Evaluate if the user's message accomplishes or shows intent to accomplish the following goal.
Even if phrased slightly differently, or if it naturally moves the conversation towards the goal, consider it accomplished.
Goal: {goal}
User's message: "{user_input}"

Answer ONLY with "YES" or "NO".
"""
    try:
        response = ollama.generate(model=JUDGE_MODEL, prompt=prompt)
        text = response.get('response', '').strip().upper()
        # Some models might say "YES." or "YES, they did."
        if text.startswith('YES') or 'YES' in text[:10]:
            return True
        return False
    except Exception as e:
        print(f"\n[Error checking task: {e}]")
        return False

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
    
    # Simple check if ollama model exists
    try:
        ollama.show(MODEL_NAME)
    except ollama.ResponseError as e:
        if e.status_code == 404:
            print(f"Error: Model '{MODEL_NAME}' not found.")
            print("Please run `./setup.sh` first to create the model.")
            sys.exit(1)
        else:
            print(f"Ollama error: {e}")
            sys.exit(1)
            
    language = input("Which language do you want to practice? (e.g., English, Japanese): ").strip()
    if not language:
        language = "English"
        
    scenario = select_scenario()
    tasks = scenario.get_session_tasks(num_tasks=10)
    
    print(f"\nStarting Scenario: {scenario.name}")
    print(f"Place: {scenario.place}")
    print(f"Role of AI: {scenario.role}")
    print("========================================\n")
    
    messages = [
        {
            "role": "user",
            "content": f"[Setup - PLACE: {scenario.place} | YOUR ROLE: {scenario.role} | TARGET LANGUAGE: {language}]\nHello. (Let's start the roleplay. You go first.)"
        }
    ]
    
    # Get initial greeting from AI
    print("[Coach is typing...]")
    try:
        response = ollama.chat(model=MODEL_NAME, messages=messages)
        ai_message = response['message']['content']
        messages.append({"role": "assistant", "content": ai_message})
        print(f"\n[Coach]: {ai_message}")
    except Exception as e:
        print(f"Failed to communicate with Ollama: {e}")
        sys.exit(1)
    
    current_task_idx = 0
    total_tasks = len(tasks)
    
    while current_task_idx < total_tasks:
        current_task = tasks[current_task_idx]
        print(f"\n--- Task {current_task_idx + 1}/{total_tasks} ---")
        print(f"🎯 Your Goal: {current_task.hint}")
        
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            print("Exiting...")
            break
            
        messages.append({"role": "user", "content": user_input})
        
        # 1. Main Roleplay Call
        print("\n[Coach is thinking...]")
        temp_messages = messages + [{
            "role": "system",
            "content": f"[Director's Note: The user's current goal is to '{current_task.goal}'. End your next response by naturally steering the conversation toward this topic so the user can achieve their goal. DO NOT say the goal outright.]"
        }]
        response = ollama.chat(model=MODEL_NAME, messages=temp_messages)
        ai_reply = response['message']['content']
        messages.append({"role": "assistant", "content": ai_reply})
        
        # Print reply
        print(f"\n[Coach]: {ai_reply}")
        
        # 2. Check Task Completion
        print(" (Checking task...) ", end='\r')
        is_done = evaluate_task(user_input, current_task.done_when)
        
        if is_done:
            print(f"✅ TASK COMPLETED! Moving to next...          ")
            current_task_idx += 1
        else:
            print(f"❌ Task not yet completed (or you asked a question). Keep trying!")

    if current_task_idx == total_tasks:
        print("\n========================================")
        print("🎉 CONGRATULATIONS! You completed all tasks! 🎉")
        print("========================================")

if __name__ == "__main__":
    main()
