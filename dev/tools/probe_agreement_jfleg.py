"""A subject-verb agreement net for English, measured on JFLEG before writing it. OPEN-50.

    python3 dev/tools/probe_agreement_jfleg.py JFLEG_DIR dev

Candidate rule: determiner + singular-looking noun + have/are/were/do. A fire
is GOOD when an annotator made that verb change. Measured 2026-10-08 on dev:
9 fires, 2 good, 7 bad (22%), so the net was NOT written — it mistakes
"that" as a conjunction ("...that we are...") and "will have". Fetch JFLEG
with dev/tools/probe_spelling_jfleg.py (JFLEG_DIR) first.
"""
import re, sys
J=sys.argv[1]; split=sys.argv[2]
src=open(f'{J}/{split}/{split}.src').read().split('\n')
refs=[open(f'{J}/{split}/{split}.ref{k}').read().split('\n') for k in range(4)]
FIX={'have':'has','are':'is','were':'was','do':'does',"don't":"doesn't"}
COLLECTIVE={'people','police','children','family','staff','team','data','media','government','public','majority','number','couple','crew','audience','class','group','youth','elderly','rich','poor','young','old','following','same','other','others','most','many','few','both','all','these','those'}
DET=r'(?:my|our|your|his|her|its|this|that|every|each|a|an|the)'
PAT=re.compile(rf'\b{DET}\s+([a-z]+)\s+(have|are|were|do|don\'t)\b', re.I)
def singular(n):
    n=n.lower()
    if n in COLLECTIVE: return False
    if n.endswith('s') and not n.endswith(('ss','us','is')): return False
    if n.endswith(('ing','ed','ly','ful','ous','ive','al','able','ible','ic','est','er')): return False
    return True
good=bad=0; clean_fire=0; examples=[]
for i,s in enumerate(src):
    if not s.strip(): continue
    unchanged=all(r[i].strip()==s.strip() for r in refs)
    for m in PAT.finditer(s):
        n,v=m.group(1),m.group(2)
        if not singular(n): continue
        right=FIX[v.lower()]
        if unchanged: clean_fire+=1
        hit=any(re.search(rf'\b{re.escape(n)}\s+{re.escape(right)}\b', r[i], re.I) for r in refs)
        if hit: good+=1
        else: bad+=1; examples.append(s[max(0,m.start()-20):m.end()+20])
print(f'{split}: fires {good+bad}, good {good}, bad {bad}, precision {100*good/max(1,good+bad):.1f}%, fires on clean {clean_fire}')
for e in examples[:12]: print('   BAD:', e)
