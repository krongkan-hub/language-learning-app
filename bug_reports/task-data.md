# Bug Reports — Task/Scenario data (`app/scenarios/builtins.py`)

**Note:** this file is under heavy active change in the working tree
(`app/scenarios/builtins.py` is +2264/−? lines vs. last commit, and
`app/scenarios/generator.py` was deleted). Two new *untracked* scripts,
`scripts/fill_69_tasks.py` and `scripts/ai_playtester.py`, appear to be an
unfinished attempt to regenerate real per-scenario task content using an
LLM author-loop validated by an automated learner-playtester — i.e. a
hand-rolled precursor to what `content_designer_agent` + `qa_agent` should
own going forward. Every item below needs re-verification against whatever
`builtins.py` looks like once that work lands; do not assume OPEN items here
are still accurate without re-checking.

### BUG-025 · NEEDS-VERIFICATION · was Critical
**63 of 69 scenarios shared an identical boilerplate task list** (originally:
only the "Greet the {speaker}" line varied per scenario; the same 8 generic
goals like "Inquire about available options and rates" repeated verbatim
across a job interview, a customs desk, and a coffee shop). Effectively 6
authored scenarios + 63 clones, none of the clones had `scene_hint` set. This
is very likely what `scripts/fill_69_tasks.py` + `scripts/ai_playtester.py`
were built to fix (an LLM generates new tasks per scenario, an AI-learner
playtester validates each one is actually achievable before accepting it).
Confirm whether that pipeline has been run and its output merged into
`builtins.py`, or whether it's still a standalone unwired script.

### BUG-026 · NEEDS-VERIFICATION · was High
**Unwinnable tasks** — objective and grading criteria mismatched. Example:
objective told the learner to "inquire about discounts" in a job interview;
learner did exactly that; judge rejected it for not naming "a specific
discount", which doesn't exist in that context. Only escape was `skip`. If
this came from the boilerplate-clone problem (BUG-025), it may already be
resolved by whatever replaces the cloned task lists — verify with a live
playthrough of a previously-affected scenario (Job Interview, Customs).

### BUG-027 · NEEDS-VERIFICATION · was Medium
**24 tasks had `done_when` requiring a literal quoted sentence**, e.g.
`Learner says 'Could the steak be prepared without onions?'` — unguessable
from the stated goal, and doesn't match `judge_deterministic`'s pattern so it
falls through to the LLM judge, which then demands the exact scenario (steak
+ onions) rather than the general intent (dietary restriction). Convert to
semantic `done_when` criteria the judge can evaluate on intent, not literal
text match.

### BUG-028 · NEEDS-VERIFICATION · Low
**Duplicate goal strings collide in `translate_hints`.** Fine Dining had 69
tasks but only 62 unique goal strings (e.g. "Inquire about dietary
restrictions" appeared 3x with 3 *different* grading criteria).
`translate_hints` returns a dict keyed by `t.goal`, so same-goal tasks with
different `done_when` silently collapse to one translated hint. Needs a
compound key (goal + task id) or de-duplicated goal text.

### BUG-029 · NEEDS-VERIFICATION · Medium
**Reactive task premise often unestablished.** Tasks with `reactive=True`
(e.g. "Clarify a mismatched order", "Push back after tasting your drink")
sometimes came up before the NPC had actually created the premise (no wrong
order existed; no drink had been served yet), forcing the learner to invent
context that was never given. `app/llm.py`'s `build_task_setup_block` is
meant to inject this via the actor prompt — check whether it's reliably
firing given `app/cli.py`'s large diff.

### BUG-030 · NEEDS-VERIFICATION · Medium
**`skip` advances the task index without an actor turn.** Because no actor
turn runs on `skip`, the new task's scene-setting (via
`build_task_setup_block`) never executes for that transition, so dialogue
can go stale relative to the new objective. Re-check current `app/cli.py`
skip handling (it changed substantially in the working tree).
