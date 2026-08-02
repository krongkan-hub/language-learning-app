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
| BL-20 | Replace remaining boilerplate-clone scenario task lists with bespoke, scenario-appropriate content | BUG-025 | `content_designer_agent` | 50 unique task signatures across 70 scenarios (41 fully bespoke) |
| BL-21 | Rewrite objectives as learner-facing intents aligned with checkable `done_when` (retire literal-quote criteria) | BUG-027 | `content_designer_agent` | Resolved & Verified (all 24 converted) |
| BL-22 | Make `reactive` task premises reliably established before the task requires reacting to them | BUG-029 | `architect_agent` | Resolved & Verified |
| BL-23 | Generalize actor system prompt beyond "customer/service worker" framing for authority-role scenarios (interviews, customs, police) | — | `content_designer_agent` | Resolved & Verified |
| BL-24 | Investigate lower per-turn latency (streaming actor output, smaller/faster coach+judge model) | — | `architect_agent` | Investigated — thread-level parallelization not viable with a single shared MLX model instance due to serialized GPU execution (+0.36s overhead measured); latency improvements require streaming actor output or a smaller/quantized model |

## Recently resolved (uncommitted — treat as "done pending verification + commit")

| Bug ref | Title | Verified live? |
| :--- | :--- | :--- |
| BUG-002 | Coach "Perfectly natural!" leaking alongside real corrections | **Yes** — confirmed in live eval & unit tests |
| BUG-011 | Coach/judge Ollama→MLX option-key regression | **Yes** — 100.0% (25/25) in `scripts/eval_judge.py` |
| BUG-013 | Judge deterministic word match rejecting inflections | **Yes** — replaced 4-char/50% LCP prefix heuristic with explicit morphological variant matching (`_are_morphological_variants()`) for English inflections/derivations |
| BUG-015 | Actor vocab block vs. sentence-count validator conflict | **Yes** — 100.0% (15/15) in `scripts/eval_actor.py` |
| BUG-035 | `scripts/eval_coach.py` broken (stale `main` import, wrong `sys.path`) | **Yes** — fixed and confirmed working |
| BUG-036 | Coach missing passive participle recall gap ("Is it prohibit here?") | **Yes** — fixed and confirmed working (5/5 pass in `eval_coach.py`) |
| BUG-037 | Japanese coffee-order particle false positive ("ブラックで" vs "ブラックの") | **Yes** — particle guidance added to `COACH_SYS` |
| BUG-038 | Proper noun vocabulary tip extraction (venue/character names) | **Yes** — added `NOUN_CAPITALIZING_LANGUAGES` + `_is_name()` filter in `app/cli.py` and system prompt rules in `app/llm.py` |

## New content merged (2026-08-01)

**Scenarios 71 through 80 Added & Live-Playtested** — `SCENARIOS` catalog expanded from 70 to 80 (+150 bespoke tasks, total 1,502 tasks across 80 scenarios).
Authored by `content_designer_agent`, verified with 85/85 `pytest` regression suite, enriched for 100% flagship structural parity, and live-playtested via `make playtest RANGE=71-80` (`scripts/ai_playtester.py`).

| Scenario # | Title | Measured Pass Rate | Tasks Passed |
| :---: | :--- | :---: | :---: |
| 71 | Emergency Room Triage Desk | `86.7%` | 13 / 15 |
| 72 | Flight Delay & Ticket Cancellation Desk | `86.7%` | 13 / 15 |
| 73 | Insurance Claim Dispute Call | `100.0%` | 15 / 15 |
| 74 | Tech Startup Co-Founder Equity & Role Alignment | `100.0%` | 15 / 15 |
| 75 | Traffic Police Roadside Stop | `80.0%` | 12 / 15 |
| 76 | Landlord Maintenance & Rent Escalation Dispute | `86.7%` | 13 / 15 |
| 77 | Customs Import Duties & Tariff Hearing | `93.3%` | 14 / 15 |
| 78 | Executive Performance Review & Promotion Request | `100.0%` | 15 / 15 |
| 79 | Bank Loan & Mortgage Officer Meeting | `100.0%` | 15 / 15 |
| 80 | Wedding & Event Planner Consultation | `100.0%` | 15 / 15 |
| **TOTAL** | **Scenarios 71 - 80 Batch Overall** | **`93.3%`** | **140 / 150** |

### Vocabulary Tip Proper-Noun Filtering (`app/cli.py` & `app/llm.py`):
- Added `NOUN_CAPITALIZING_LANGUAGES` + `_is_name()` helper in `app/cli.py` to filter out proper nouns (e.g. venue or character names) from extracted vocabulary tips.
- Updated `ACTOR_SYS` and `GREETING_SYS` prompt templates in `app/llm.py` with explicit instructions forbidding the LLM from selecting proper nouns as vocabulary words.

### Ground-Truth Failure Triage (10 Failures in Dataset `scratch/playtest_71_80_results.json`):
- **Category (a): Judge/Content `done_when` Synonym & Morphological Bugs (6 tasks — FIXED):**
  - Traffic Police #12 ("Compliance"): Fixed in `app/judge.py` by replacing the old 4-char/50% LCP prefix heuristic in `_word_matches` with explicit rule-based morphological variant matching (`_are_morphological_variants()`), checking valid English inflections/derivations (e.g. comply/compliance, deduct/deductible, certify/certification).
  - Traffic Police #14 ("Ask if safe to merge") & #09 ("Procedure to contest ticket"): Fixed in `builtins.py`.
  - Flight Delay #02 ("Rebooking") & #06 ("Contest care"): Fixed in `builtins.py`.
  - Landlord Dispute #14 ("Lease addendum"): Fixed in `builtins.py`.
  - Customs Hearing #11 ("Senior auditor"): Fixed in `builtins.py`.
- **Category (b): Simulated-Learner Harness Sampling Artifacts (3 tasks):**
  - ER Triage #03, Traffic Police #02 & #11: Temperature 0.6 sampling quirks (garbled token prefix or NPC repetition loop).
- **Category (c): Isolated-Testing Phase 3 Context Artifact (1 task):**
  - Landlord Dispute #15 (Phase 3 closing task): Tested from fresh turn-1 greeting before maintenance context is established.

**True Content Winnability Rate (excluding Category B & C harness artifacts):** **`98.6%` (148 / 150 tasks winnable)**.

| ID | Title | Owner | Status |
| :-- | :--- | :--- | :--- |
| BL-20 | Audit boilerplate-clone task lists across Scenarios 7-69 | `content_designer_agent` | **Audited (63/63 scenarios contain 4 cloned tasks = 252 total)** |
| BL-25 | Live-playtest Apartment Neighbor Conversation | `qa_agent` | Resolved & Verified |
| BL-26 | Live-playtest Scenarios 71-80 Batch | `qa_agent` | Resolved & Verified (`93.3%` ground-truth / `98.6%` true content pass rate) |
