# ADR-007: Composed scenes — vary place, character and events around a fixed archetype

**Status:** Accepted, 2026-10-31
**Owner:** พี (project owner)
**Plan:** [docs/plans/dynamic-scenarios.md](../plans/dynamic-scenarios.md)

## Context

Every session of a scenario happens at the same place, with the same
unnamed NPC, so replays feel identical even when the drawn tasks differ.
But the tasks are what the judge grades, and each one is written against its
scenario's role (5,520 tasks, `check_task_depth --expect-total=5520`).
Generating tasks, or moving them between roles, would put ungraded content in
front of the judge.

## Decision

1. **The archetype is the gradeable unit.** Each of the 80 scenario files is
   an archetype and stays byte-identical; its tasks are never generated.
2. **Everything around it is drawn from parts** in `app/scenarios/parts/`:
   places (with tags from a closed vocabulary), characters (named personas on
   the archetype's role) and ambient complications. A place fits an
   archetype when its tags cover the archetype's `requires_place_tags`; an
   event fits a place when the place has the event's tags.
3. **A task that needs something of the place carries a requirement.**
   `goal_requires_place_tags` names the tags its place must have (or, with
   `!`, must not); a goal is drawn only where they hold, the default place
   included. Two lexicons in `check_parts.py` — venue words compared by
   place text, feature words (flight, basement, lake, pool…) compared by
   tag — fail any goal drawable at a place lacking what it names, unless a
   requirement or an explicit waiver covers it.
4. **Seeded, then curated.** `dev/tools/extract_parts.py` derives the defaults
   from the scenario files and keeps every hand-curated field, so a default
   composition stays equal to its scenario.
5. A drop-in third character is part of the plan but lands later (plan PR 6–7),
   behind a probability that starts at 0.

## Consequences

- Session identity, mastery and stats stay keyed on the archetype name.
- Content gaps are caught by `make check` (`check_parts.py`: ≥3 eligible
  places and ≥2 personas per archetype, EN/JA parity on every part), not by a
  learner meeting a premise the place cannot hold.
- Wiring into the CLI is gated on the composed-actor eval and an AI playtest
  (plan §5–6); until then nothing at runtime reads the parts.
