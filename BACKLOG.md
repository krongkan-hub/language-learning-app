# Backlog

Owned by `pm_agent`. Every open signal (bug report, feature ask,
architecture follow-up) gets exactly one entry here — dedupe against
existing entries before adding a new one. Entries link to `bug_reports/`
where a written repro exists.

## Quick wins

| ID | Title | Bug ref | Owner | Status |
| :-- | :--- | :--- | :--- | :--- |
| BL-01 | Display `Task.hint` after a failed attempt (content already authored for all 1330 tasks, just never surfaced) | — | `content_designer_agent` + `architect_agent` | Resolved & Verified |
| BL-02 | Commit + live-verify the coach/judge option-key fix (`num_predict`→`max_tokens`) | BUG-011 | `architect_agent` → `qa_agent` verify | Resolved & Verified |
| BL-03 | Harden judge verdict parsing beyond the current substring heuristic (adversarial phrasing check) | BUG-010 | `qa_agent` | Resolved & Verified |
| BL-04 | Confirm `judge_deterministic` stem-matching fix with live cases | BUG-013 | `qa_agent` | Resolved & Verified |
| BL-05 | Suppress cross-section coach duplicates (Feedback ↔ Level-up) + enforce max-2-corrections in code | BUG-008, BUG-009 | `architect_agent` | Resolved & Verified |
| BL-06 | Fix HF_HUB_OFFLINE first-run contradiction with setup.sh | BUG-031 | `architect_agent` | Resolved & Verified |
| BL-07 | Remove hardcoded vocab examples ("single-origin"/"saffron-infused") from actor prompts | BUG-017 | `content_designer_agent` | Resolved & Verified |
| BL-08 | Remove dead `BASE_MODEL='qwen3:8b'` + `/no_think` leftovers in coach.py/judge.py | BUG-014 | `architect_agent` | Resolved & Verified |
| BL-09 | Add spinner/latency indicator around coach/judge/actor calls | BUG-033 | `architect_agent` | Resolved & Verified |
| BL-10 | Narrow `MLX_ERRORS` catch scope so real bugs surface instead of being reported as generic engine errors | BUG-032 | `architect_agent` | Resolved & Verified |
| BL-11 | .gitignore stray `*.db`/`db_dump.txt` runtime artifacts | BUG-034 | `architect_agent` | Resolved & Verified |

## Medium

| ID | Title | Bug ref | Owner | Status |
| :-- | :--- | :--- | :--- | :--- |
| BL-12 | Promote grammatically-corrective Level-up bullets into Feedback (stop demoting real errors) | BUG-001 | `architect_agent` + coach prompt work | Resolved & Verified |
| BL-13 | Fix `validate()`'s 4 closed-question gaps (last-sentence-only, first-word-only, `' or '` escape, non-Latin blind spot) | BUG-019 | `architect_agent` | Resolved & Verified |
| BL-14 | Surface validation failures after 3 failed actor attempts instead of shipping silently | BUG-018 | `architect_agent` | Resolved & Verified |
| BL-15 | Add end-of-session summary (tasks completed/skipped/failed + consolidated corrections) from existing SQLite log | — | `architect_agent` | Resolved & Verified |
| BL-16 | Sanitize/quarantine learner input before it reaches the actor prompt (prompt-injection hijack) | BUG-023 | `architect_agent` | Resolved & Verified |
| BL-17 | Re-verify task-data bugs (unwinnable tasks, literal-quote `done_when`, reactive-premise timing, `skip` scene-setting) against current `builtins.py` | BUG-026, BUG-027, BUG-029, BUG-030 | `qa_agent` | Needs live re-verification before scoping fixes |
| BL-18 | De-duplicate colliding goal strings in `translate_hints` (dict keyed by goal only) | BUG-028 | `content_designer_agent` | Resolved & Verified |

## Bigger

| ID | Title | Bug ref | Owner | Status |
| :-- | :--- | :--- | :--- | :--- |
| BL-19 | Decide fate of `scripts/fill_69_tasks.py` + `scripts/ai_playtester.py` — formalize into `content_designer_agent`/`qa_agent`'s standing toolset, or discard | BUG-025, see `ARCHITECTURE.md` §5 | `architect_agent` (ADR) then `content_designer_agent` | Resolved & Verified (ADR-003) |
| BL-20 | Replace remaining boilerplate-clone scenario task lists with bespoke, scenario-appropriate content | BUG-025 | `content_designer_agent` | Needs re-verification of current clone status first |
| BL-21 | Rewrite objectives as learner-facing intents aligned with checkable `done_when` (retire literal-quote criteria) | BUG-027 | `content_designer_agent` | Open |
| BL-22 | Make `reactive` task premises reliably established before the task requires reacting to them | BUG-029 | `architect_agent` | Open |
| BL-23 | Generalize actor system prompt beyond "customer/service worker" framing for authority-role scenarios (interviews, customs, police) | — | `content_designer_agent` | Open |
| BL-24 | Investigate lower per-turn latency (streaming actor output, smaller/faster coach+judge model) | — | `architect_agent` | Open, no target yet |

## Recently resolved (uncommitted — treat as "done pending verification + commit")

| Bug ref | Title | Verified live? |
| :--- | :--- | :--- |
| BUG-002 | Coach "Perfectly natural!" leaking alongside real corrections | **Yes** — confirmed in live eval & unit tests |
| BUG-011 | Coach/judge Ollama→MLX option-key regression | **Yes** — 100.0% (25/25) in `scripts/eval_judge.py` |
| BUG-013 | Judge deterministic word match rejecting inflections | **Yes** — 100.0% (25/25) in `scripts/eval_judge.py` |
| BUG-015 | Actor vocab block vs. sentence-count validator conflict | **Yes** — 100.0% (15/15) in `scripts/eval_actor.py` |
| BUG-035 | `scripts/eval_coach.py` broken (stale `main` import, wrong `sys.path`) | **Yes** — fixed and confirmed working |
| BUG-036 | Coach missing passive participle recall gap ("Is it prohibit here?") | **Yes** — fixed and confirmed working (5/5 pass in `eval_coach.py`) |
| BUG-037 | Japanese coffee-order particle false positive ("ブラックで" vs "ブラックの") | **Yes** — particle guidance added to `COACH_SYS` |

## New content merged (2026-07-31)

**Apartment Neighbor Conversation** scenario added — `SCENARIOS` now 70
(69→70), `scenario_69_tasks` (22 tasks) in `app/scenarios/builtins.py`.
Authored by `content_designer_agent`, checklist-verified, and live-playtested
via `scripts/playtest_scenario_70.py`.

| ID | Title | Owner | Status |
| :-- | :--- | :--- | :--- |
| BL-25 | Live-playtest Apartment Neighbor Conversation | `qa_agent` | Resolved & Verified |
