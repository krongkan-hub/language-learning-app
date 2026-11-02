# Dynamic scenarios + drop-in character — plan (approved by พี 2026-10-31)

## 1. Core constraint
- Tasks are bound to a role (80 files × 69 tasks = 5,520, `dev/check_all.sh` `--expect-total=5520`). Judge grades `done_when` only. So the gradeable unit is the **archetype** = one of today's 80 scenarios. Scenario content stays byte-identical (check_catalog_roundtrip, check_task_depth, check_scenario_parity stay green); only display translations such as `place_translations` may be corrected, and a default place's Japanese is its scenario's.
- Free to vary: **place** (any place whose tags fit the archetype), **who** (persona on the archetype's role: name, age, register, trait; optional alt_roles restricted to some threads), **events** (complications + drop-ins).

## 2. Data model: `app/scenarios/parts/*.json`
- `archetypes.json`: `{id: "scenario_01", requires_place_tags, default_place, default_character, goal_requires_place_tags: {goal: [tags]}, lexicon_waivers: {goal: [terms]}, alt_roles: [{character_id, threads}]}`
- `places.json`: `{id, text, translations:{Japanese}, tags:[closed vocabulary: venue (what it is), attribute (indoor, queue, formal…), feature (what it has: parking, basement, lake, airport…)]}`
- `characters.json`: `{id, archetypes:[...], role, speaker, speaker_translations, persona:{name_en, name_ja, trait, ja_register}}`
- `events.json`: `{id, kind:"complication"|"dropin", text, requires_place_tags, archetypes?}`; drop-ins add `{speaker, speaker_translations, persona, entry_brief, anchor_terms:{en,ja}, exit_line:{English,Japanese}, task:{goal, hint, done_when, translations, phase:2}}`.
- Compatibility: place.tags ⊇ archetype.requires_place_tags (`!tag` excludes: the engineering interview is not held in the marketing department); character ∈ archetype; place fits event.requires_place_tags (same `!` rule: the departure boards are not shown at customs); a goal is drawn only where the place meets its `goal_requires_place_tags` (`!tag` = must not have it: "the express bus to the airport" is not asked at the airport).
- `compose(archetype, rng) -> (Scenario, SceneSpec)` returns the existing `Scenario` dataclass so downstream is unchanged.
- Extraction: `dev/tools/extract_parts.py` seeds pools from the 80 files (place, role, speaker, complications, place_translations). Tags and goal requirements curated by hand. `check_parts` runs two lexicons over every task — venue words compared by place text (vineyard, culinary school…) and feature words compared by tag (flight, basement, lake, pool…) — and fails on any goal drawable at a place lacking what it names, unless a requirement keeps it away or a waiver says the word is not about the place (a beach read, the learner's own basement). The default composition (default place + default character, no persona) is exactly the legacy scenario: the default place carries every feature its goals require, so all of them are drawn there, and the default character's Japanese speaker label is the one the legacy UI shows (`i18n.speaker_label`); `check_parts` enforces both. Better per-archetype labels go on personas.
- Tasks are never generated. Composed session = `archetype.get_session_tasks(...)` minus goals the drawn place does not meet (`Parts.goal_fits`), plus ≤1 authored drop-in task.
- No LLM glue in v1 (greeting sets the scene). Composed name = `{archetype name} · {place}` from translations. `speaker_label` gets overrides from part translations for composed scenes only; `SPEAKER_LABELS` (legacy UI) is not edited.
- As built (PR 2, `app/scenarios/compose.py`): the composed name applies only when the place is not the default, so a persona-only scene keeps the legacy name. A spec's events are the archetype's own complications that fit the place plus one ambient one, and they become `Scenario.complications` (runtime still picks one). A persona's label is always `{name} ({role})` / `{name_ja}（{role_ja}）` (`Ryuji Kato (Officer)` / `加藤 竜二（巡査）`): a persona character's `speaker`/`speaker_translations` hold the role alone, never a name — the 20 that read 'Officer Kato' / 'プランナーのアシュフォード' were cut to the role, and `test_every_persona_label_is_name_then_role` holds every persona to it. Default characters keep the legacy label untouched; it travels on a new `Scenario.speaker_translations` field (empty for non-persona characters, so `SPEAKER_LABELS` applies), and the persona's name, trait and Japanese register are appended to `role`. `compose` takes a seed from `rng` and draws from `Random(seed)`, which the spec records.

## 3. Identity & persistence
- `SceneSpec = {v:1, seed, archetype, place, character, events:[...], dropin:{id, at_task}}`; signature = sha1(canonical json without seed)[:10]; `--seed` for CLI/tests/evals.
- `sessions.scenario_name` stays the archetype name → mastery, seen/unfinished goals, mistakes, stats unchanged.
- New `scene JSONB NULL` via `ALTER TABLE sessions ADD COLUMN IF NOT EXISTS` in `_SCHEMA` (no-migrations rule). NULL = default composition.
- `create_session(scene=None)`; `get_resumable_session` returns it; resume uses `compose_from_spec(spec)` with fallback to defaults if a part id vanished; goal check must include the drop-in goal (don't refire if logged).

## 4. Drop-in character
- Trigger: seeded at compose time, 0 or 1 per session, p≈0.5 (flag; 0 at first). Inserted after a phase-2 task; never first/last, never adjacent to phase 1/3; only becomes current via judge YES (`_advance_after_judge`).
- While D is current the drop-in persona replies (interrupts instead of main NPC). On done/exhausted (max_attempts=2): print authored `exit_line` (no generation), then main NPC replies for next task with a one-line system note to acknowledge briefly.
- Cache: `_actor_system(sess, idx)` returns `DROPIN_SYS` when tasks[idx] is D; reuse parity slots + existing task_idx+1 warm job; no new slot; PROMPT_CACHE_MAX_ENTRIES unchanged. Warm path and turn path build messages via one `_actor_messages(sess, idx)` helper (unit test: identical prompts).
- Messages get a `speaker` key; main NPC's `actor_view` drops drop-in exchange (replaced by system note); drop-in sees only its own exchange + entry_brief. DROPIN_SYS short, target language, 1–2 sentences, no vocab card.
- CLI: `sentence` and `stage:replying` events carry `speaker`; objective line shows "→ {drop-in label}".
- Judge: D is an ordinary authored task; no judge prompt change in v1; add judge cases; fallback = labelled speakers in context_str.
- Coach: capture `addressed = sess.current_task` before the judge; situation uses the addressed speaker.

## 5. Evals & tests
- Deterministic (in make check): `dev/checks/check_parts.py` (ids/refs, closed tags, ≥3 eligible places per archetype, every drop-in placeable, EN/JA parity, venue + feature lexicons against goal requirements, ≥40 goals drawable at every place). `dev/tests/test_compose.py` (defaults == legacy Scenario; same seed same spec; constraints over 10k seeds; drop-in schedule invariants; spec round-trip/resume). CLI tests for speaker labels, actor_view filter, parity cache key, prefill==turn prompts, coach addressed situation. Coverage floor 90.
- LLM: new `dropin` suite (EN+JA, rule-graded: script, ≤2 sentences, anchor_terms, not main NPC's name; resume case). Judge cases for addressing intruder vs main NPC. actor/rawactor `--composed N --seed` mode. Acceptance: AI-playtest completion on composed ≥ legacy − 5pt. Baselines added after measuring.
- Latency: probe `--dropin`; non-drop-in p50 ≈ 6.0s unchanged; drop-in turns p50 ≤ 8s.

## 6. PR sequence (each make check green; no default behaviour change until 4 and 7)
1. Parts data + extractor + loader + check_parts. Scenario JSON untouched.
2. compose()/SceneSpec/signature, pure, with equivalence & invariant tests. Not wired.
3. Persistence: scene column, create_session(scene=), resume via spec.
4. CLI wiring: random offer in select_scenario serves a composed scene behind LANGUAGE_COACH_COMPOSE=1; list pick stays legacy; banner/speaker overrides; composed actor eval + playtest; then flip default.
5. Speaker-aware plumbing: speaker on messages/events, actor_view filter, _actor_messages helper. No behaviour change.
6. Drop-in content + scheduler, persisted with p=0.
7. Drop-in runtime: DROPIN_SYS, responder switch, exit line, coach addressed fix, judge cases, dropin suite, baselines, latency probe; then raise p.

## 7. Risks
Persona bleed (7B), judge confusion, place-swap breaking premises, cold first drop-in turn if learner types fast (~1–2s once), content gaps (archetype with 1 place → check_parts minimum + default fallback).
