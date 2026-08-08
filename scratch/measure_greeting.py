import sys, os, re
sys.path.insert(0,'/Users/pk/language-learning-app')
from app.llm import _llm_chat, validate, GREETING_SYS, build_task_setup_block
from app.scenarios.builtins import SCENARIOS
import random
random.seed(11)
N=int(sys.argv[1]) if len(sys.argv)>1 else 12
fails=0; reasons={}
for i in range(N):
    sc=random.choice(SCENARIOS); task=random.choice(sc.tasks)
    sysmsg=GREETING_SYS.format(place=sc.place, role=sc.role, language='English', mood='neutral',
                            complication='', task_setup=build_task_setup_block(task))
    # Greeting is generated from prompt with a user invitation or scene start instruction
    conv=[{'role':'user','content':'Start the scene.'}]
    r=_llm_chat(messages=[{'role':'system','content':sysmsg}]+conv, options={'temperature':0.6,'max_tokens':220})
    txt=r["message"]["content"]
    ok,reason=validate(txt, max_sentences=3)
    if not ok:
        fails+=1; reasons[reason]=reasons.get(reason,0)+1
print(f"greeting turns generated: {N}")
print(f"failed validation       : {fails} ({fails/N*100:.0f}%)")
for k,v in sorted(reasons.items(), key=lambda x:-x[1]): print(f"   {v:>2}x {k}")
