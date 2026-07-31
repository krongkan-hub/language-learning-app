# ADR-002: Adopt a multi-agent development harness for this project

**Status:** Accepted
**Owner:** `architect_agent` (recorded on behalf of the team; the full
governance spec lives in Antigravity's own store, referenced below)

## Context
A single manual playtest session (10 runs, non-native-learner persona,
mixed pass/fail coverage) surfaced roughly 30 distinct, concrete defects
across the actor/coach/judge pipeline and the scenario content — several
of them the app's core value proposition failing silently (the coach
saying "Perfectly natural!" on sentences with real errors). That session's
findings existed only as chat scrollback with no mechanism to prevent
regressions, track resolution, or avoid re-discovering the same bug twice.

Separately, the team had already sketched a 5-agent structure (Lead +
`pm_agent`, `architect_agent`, `qa_agent`, `content_designer_agent`) but
without artifact ownership, a typed handoff contract, or loop-termination
guards, agents would either collide on the same files or produce
unstructured prose reports the Lead has to re-parse by hand every time.

## Decision
Adopt the harness specification recorded at
`~/.gemini/antigravity-cli/brain/d484a452-6961-4bc8-a888-244b6c0d6a7d/multi_agent_harness_specification.md`:
- **Artifact ownership** — each agent owns exactly one set of files it
  writes; read-only elsewhere. (`BACKLOG.md` → `pm_agent`; this file and
  `ARCHITECTURE.md` → `architect_agent`; `bug_reports/` and
  `eval/coach_cases.json` → `qa_agent`; `app/scenarios/*.py` and pedagogy
  docs → `content_designer_agent`.)
- **Typed `Report` handoff** — every subagent turn ends in a structured
  `{status, evidence, artifacts_touched, next_action}` block, not free
  prose, so the Lead can evaluate `done_when` mechanically.
- **Orchestration loop with a loop-drift guard** — the Lead dispatches
  `Task{owner, done_when, budget}`, and stops escalating silently after two
  consecutive `blocked` reports on the same task rather than retrying
  forever.

## Consequences
- Scaffolded the owned artifacts in-repo so the design isn't just aspirational
  text: `BACKLOG.md`, `ARCHITECTURE.md`, `ADRs/`, `bug_reports/`, and seeded
  `eval/coach_cases.json` with regression cases from the original playtest.
- `bug_reports/` was seeded from the pre-harness playtest findings, cross-
  checked against the actual working-tree state at scaffolding time — several
  findings turned out to already have uncommitted fixes in progress,
  demonstrating exactly the problem this ADR addresses: without a shared,
  persistent artifact, that fix work and the bug findings would never have
  been reconciled against each other.
- `qa_agent`'s first standing task is to re-verify every FIXED-UNCOMMITTED
  and NEEDS-VERIFICATION entry in `bug_reports/` via a live run, not to
  trust code-reading alone.
- **Verified in practice, 2026-07-31:** dispatched a scenario-authoring task
  to `content_designer_agent` (Apartment Neighbor Conversation) with a
  9-point checklist and a typed `Report` requirement. The agent returned
  `status: done` with a table claiming 100% pass on all 9 items. Independent
  review (Lead, not re-trusting the agent's self-check) found two of those
  nine claims were wrong: the advanced-task ratio was miscounted (claimed
  63.6%, actual 54.5%), and 2 of 3 `reactive=True` tasks were missing the
  `scene_hint` the checklist explicitly required — reproducing BUG-029 in
  brand-new content despite the dispatch prompt naming that exact bug as
  something to avoid. Confirms the harness's core premise: a subagent's own
  "checklist passed" report is a claim to verify, not a fact to integrate on.
