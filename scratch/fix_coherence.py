import ast
import re
import sys

def apply_fixes():
    with open('app/scenarios/builtins.py', 'r') as f:
        content = f.read()

    updates = {
        # 1. NEAR-DUPLICATE GOALS
        (4, 65): {
            'goal': "Request additional clothing hangers for your room closet",
            'hint': "Ask front desk to send up extra coat hangers.",
            'done_when': "Learner requested extra clothing hangers for the room closet.",
        },
        (8, 15): {
            'goal': "Ask if the express train features power outlets and onboard Wi-Fi",
            'hint': "Inquire about electrical sockets and internet connectivity on the train.",
            'done_when': "Learner asked about onboard power outlets and Wi-Fi.",
        },
        (13, 20): {
            'goal': "Inquire if the bookstore offers domestic shipping for gift purchases",
            'hint': "Ask if the store can mail a purchased book directly to a friend.",
            'done_when': "Learner inquired about domestic shipping options for gift books.",
        },
        (14, 18): {
            'goal': "Ask if the salon offers a complimentary neck trim between full haircuts",
            'hint': "Inquire if touch-up neck trims are free for regular clients.",
            'done_when': "Learner asked about complimentary neck touch-up trims.",
        },
        (15, 15): {
            'goal': "Inquire if discounted membership rates are available for students or seniors",
            'hint': "Ask if student or senior citizen ID qualifies for reduced monthly dues.",
            'done_when': "Learner inquired about student or senior membership discount rates.",
        },
        (15, 17): {
            'goal': "Inquire about parking availability and designated member parking spaces",
            'hint': "Ask if the gym facility provides free parking for members.",
            'done_when': "Learner inquired about member parking availability and validation.",
        },
        (23, 65): {
            'goal': "Request a clear self-adhesive plastic pouch for international customs forms",
            'hint': "Ask the clerk for a transparent document sleeve to attach customs papers.",
            'done_when': "Learner requested a clear plastic pouch for customs documentation.",
        },
        (33, 19): {
            'goal': "Ask if customized background music or ambient sound preferences can be selected",
            'hint': "Inquire if relaxing music or ambient sounds can be adjusted in the massage room.",
            'done_when': "Learner asked about background music and ambient sound options.",
        },
        (34, 15): {
            'goal': "Inquire about available application fee waiver codes for prospective students",
            'hint': "Ask if the admissions office provides fee waiver codes for online applications.",
            'done_when': "Learner inquired about application fee waiver codes.",
        },
        (34, 20): {
            'goal': "Ask if recommendation letters must be sent directly from high school counselors",
            'hint': "Inquire whether teachers must submit recommendation letters through the official portal.",
            'done_when': "Learner asked about teacher recommendation submission procedures.",
        },
        (34, 21): {
            'goal': "Request a grace period for submitting official translated transcripts",
            'hint': "Politely ask for additional time to mail certified non-English transcript translations.",
            'done_when': "Learner requested a grace period for submitting translated transcripts.",
        },
        (34, 24): {
            'goal': "Address issue where submitted standardized test scores are missing from your portal",
            'hint': "Inform the officer that your official test score report is not showing on your account.",
            'done_when': "Learner reported missing test scores on the admissions portal.",
        },
        (35, 16): {
            'goal': "Ask if temporary resident permits or student IDs qualify for library card registration",
            'hint': "Inquire whether a student card or lease agreement is accepted for registration.",
            'done_when': "Learner asked about alternative ID forms for library registration.",
        },
        (35, 18): {
            'goal': "Inquire about renewal limits when another patron places a hold on a book",
            'hint': "Ask if books can be renewed if someone else has requested them.",
            'done_when': "Learner inquired about renewal restrictions on reserved items.",
        },
        (35, 63): {
            'goal': "Confirm that your online library account barcode can be scanned from a smartphone",
            'hint': "Ask the librarian if the digital card barcode on your phone works at checkout.",
            'done_when': "Learner confirmed digital barcode scanning compatibility.",
        },

        # 2. TRIVIAL VOCABULARY
        (23, 5): {
            'goal': "Use the word 'restriction'",
            'hint': "A restriction is a rule or limitation that limits what is allowed. Ask about shipping restrictions for hazardous liquids.",
            'done_when': "Learner used the word 'restriction'.",
        },
        (30, 5): {
            'goal': "Use the word 'quota'",
            'hint': "A quota is a fixed limit or allocation of a resource. Ask if your monthly data plan has an unthrottled high-speed quota.",
            'done_when': "Learner used the word 'quota'.",
        },
        (69, 3): {
            'goal': "Use the word 'disturbance'",
            'hint': "A disturbance is an interruption of peace, quiet, or public order. Apologize for any late-night noise disturbance caused by your visitors.",
            'done_when': "Learner used the word 'disturbance'.",
        },
        (70, 3): {
            'goal': "Use the word 'escalate'",
            'hint': "To escalate means to increase rapidly or become more intense. Explain that severe abdominal pain began to escalate an hour ago.",
            'done_when': "Learner used the word 'escalate'.",
        },
        (73, 3): {
            'goal': "Use the word 'provisional'",
            'hint': "Provisional describes an arrangement that is temporary and subject to later revision. Suggest setting a provisional equity split until funding arrives.",
            'done_when': "Learner used the word 'provisional'.",
        },
        (73, 11): {
            'goal': "Use the word 'severance'",
            'hint': "Severance refers to compensation or terms provided when an employment or partnership terminates. Discuss severance conditions if a founder leaves early.",
            'done_when': "Learner used the word 'severance'.",
        },
        (76, 3): {
            'goal': "Use the word 'levy'",
            'hint': "A levy is an official tax, fee, or fine imposed by an authority. Inquire if an additional administrative levy applies to custom entries.",
            'done_when': "Learner used the word 'levy'.",
        },
        (76, 27): {
            'goal': "Use the word 'authorization'",
            'hint': "Authorization is official permission or formal approval granted by an authority. Request written authorization to release the detained commercial goods.",
            'done_when': "Learner used the word 'authorization'.",
        },
        (77, 26): {
            'goal': "Use the word 'remuneration'",
            'hint': "Remuneration means payment or compensation received for work performed. Discuss adjusting your executive remuneration package based on annual targets.",
            'done_when': "Learner used the word 'remuneration'.",
        },

        # 3. GOAL / DONE_WHEN DISAGREEMENT
        (69, 42): {
            'done_when': "Learner discussed shared electric vehicle charging outlet turn-taking.",
        },
        (71, 34): {
            'done_when': "Learner inquired if unattended minor assistance is maintained on rebooked flight.",
        },
        (73, 52): {
            'done_when': "Learner discussed press release quote approval rights between co-founders.",
        },
        (73, 56): {
            'done_when': "Learner discussed domain name and trademark ownership transfer to company.",
        },
        (79, 67): {
            'done_when': "Learner inquired about vendor payment schedule deadlines.",
        },
    }

    # Split content by scenario_X_tasks = [
    pattern = re.compile(r'^(scenario_(\d+)_tasks\s*=\s*\[)', re.MULTILINE)
    matches = list(pattern.finditer(content))

    new_content = ""
    last_end = 0

    for idx, match in enumerate(matches):
        si = int(match.group(2))
        start_pos = match.start()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else content.find('SCENARIOS = [')
        
        block = content[start_pos:end_pos]
        
        task_call_pattern = re.compile(r'Task\((.*?)\)(?=\s*,\s*\n|\s*\]|\s*\n\s*Task|\s*\n\s*\])', re.DOTALL)
        tasks_in_block = list(task_call_pattern.finditer(block))
        
        block_new = ""
        block_last = 0
        for ti, tmatch in enumerate(tasks_in_block):
            if (si, ti) in updates:
                upd = updates[(si, ti)]
                t_text = tmatch.group(1)
                
                # Parse t_text using AST
                # Wrap as AST Call node: Task(<t_text>)
                call_code = f"Task({t_text})"
                try:
                    tree = ast.parse(call_code)
                    call_node = tree.body[0].value
                except Exception as e:
                    print(f"AST parse error for Sc{si+1} Task {ti}: {e}\nCode: {call_code}")
                    sys.exit(1)
                
                # Extract args and kwargs from call_node
                args_map = {}

                # Positional args order: 0: goal, 1: hint, 2: done_when
                pos_names = ['goal', 'hint', 'done_when']
                for p_idx, arg_node in enumerate(call_node.args):
                    if isinstance(arg_node, ast.Constant):
                        args_map[pos_names[p_idx]] = arg_node.value
                
                # Keyword args
                kw_nodes = {}
                for kw in call_node.keywords:
                    if kw.arg in pos_names:
                        if isinstance(kw.value, ast.Constant):
                            args_map[kw.arg] = kw.value.value
                    else:
                        # retain other kwargs as code strings
                        kw_nodes[kw.arg] = ast.unparse(kw.value)
                
                # Apply updates
                for k, v in upd.items():
                    args_map[k] = v
                
                # Build new call code
                arg_strs = [repr(args_map['goal']), repr(args_map['hint']), repr(args_map['done_when'])]
                for k, v_str in kw_nodes.items():
                    arg_strs.append(f"{k}={v_str}")
                
                new_task_str = "Task(" + ", ".join(arg_strs) + ")"
                
                block_new += block[block_last:tmatch.start()] + new_task_str
                block_last = tmatch.end()
        
        block_new += block[block_last:]
        new_content += content[last_end:start_pos] + block_new
        last_end = end_pos

    new_content += content[last_end:]

    with open('app/scenarios/builtins.py', 'w') as f:
        f.write(new_content)

    print("Updated app/scenarios/builtins.py successfully.")

if __name__ == '__main__':
    apply_fixes()
