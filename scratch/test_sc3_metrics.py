import sys

sys.path.insert(0, '.')
from app.scenarios.models import Task, Scenario

with open('scratch/sc3_fixed.py') as f:
    code = f.read()

local_vars = {'Task': Task}
exec(code, local_vars)
tasks = local_vars['scenario_3_tasks']

sc = Scenario("Pharmacy", "Pharmacy", "Pharmacist", "Learner", tasks)

total = len(tasks)
sh_count = sum(1 for t in tasks if t.scene_hint and t.scene_hint.strip())
react_count = sum(1 for t in tasks if t.reactive)
adv_count = sum(1 for t in tasks if t.difficulty == "advanced")
vocab_count = sum(1 for t in tasks if "Learner used the word" in t.done_when or "Use the word" in t.goal)
p1_count = sum(1 for t in tasks if t.phase == 1)
p3_count = sum(1 for t in tasks if t.phase == 3)
goals = [t.goal for t in tasks]
intra_dups = len(goals) - len(set(goals))

c_total = (total == 69)
c_sh = (10 <= sh_count <= 16)
c_react = (14 <= react_count <= 18)
c_adv = (19 <= adv_count <= 24) and (adv_count >= 7)
c_vocab = (4 <= vocab_count <= 6)
c_p1 = (p1_count >= 5)
c_p3 = (p3_count >= 8)
c_dups = (intra_dups == 0)

sc_passed = c_total and c_sh and c_react and c_adv and c_vocab and c_p1 and c_p3 and c_dups

print(f"Scenario 4 checks: PASS={sc_passed}")
print(f"  Total: {total} ({c_total})")
print(f"  Hint: {sh_count} ({c_sh}) [req 10-16]")
print(f"  React: {react_count} ({c_react}) [req 14-18]")
print(f"  Adv: {adv_count} ({c_adv}) [req 19-24]")
print(f"  Vocab: {vocab_count} ({c_vocab}) [req 4-6]")
print(f"  P1: {p1_count} ({c_p1}) [req >=5]")
print(f"  P3: {p3_count} ({c_p3}) [req >=8]")
print(f"  Dups: {intra_dups} ({c_dups})")
