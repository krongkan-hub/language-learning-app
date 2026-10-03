from dataclasses import dataclass, field
from typing import Dict, List
import random
import re

# A goodbye ends the conversation, so a session holds at most one and it is
# always the last task. Every one of the 71 in the catalogue is phase 3, but
# phase alone only sorts it among the closing tasks: a playtest session
# (2026-09-27) asked for a farewell at task 8 of 10 and then again at 10.
_FAREWELL = re.compile(r'farewell|goodbye|good-bye', re.I)


def is_farewell(task) -> bool:
    return bool(_FAREWELL.search(task.goal))

@dataclass
class Task:
    goal: str
    hint: str
    done_when: str
    difficulty: str = "standard"  # "standard" or "advanced" (C1: negotiation,
                                  # justification, multi-step reasoning)
    # Optional ambient/environmental premise the learner's goal reacts to
    # (loud music, a dirty table, etc.). The actor shares this space, so unlike
    # a learner-initiated ask that needs no grounding, the fact only exists if
    # the actor makes it observably true in its OWN dialogue first — otherwise
    # the learner's complaint comes out of nowhere. Injected into the actor/
    # greeting prompt via build_task_setup_block; never seen by the task judge.
    scene_hint: str = ""
    # Rough conversational stage the task belongs to, used only to order a
    # session so objectives appear when they plausibly could:
    #   1 = opening (arrival/check-in: reservations, ID, spelling a name)
    #   2 = middle (the bulk of requests; the default)
    #   3 = closing (payment, receipts, billing disputes, farewells)
    # A billing dispute at the moment of check-in, or a goodbye up front, reads
    # as broken; phase keeps them in a believable order without hard-gating.
    phase: int = 2
    # True when this task presupposes a prior conversational exchange — an
    # order already placed, a drink received, a prior complaint. The session
    # builder will never place a reactive task as the first task.
    reactive: bool = False
    # Accepted renderings of this task's vocabulary target, per language, for
    # the 401 goals shaped "Learner used the word 'X'". `done_when` stores the
    # target in English only, which made those tasks unwinnable in Japanese
    # (judge_deterministic substring-tested 'sommelier' against Japanese text)
    # and made translate_hints render the goal line in Chinese — OPEN-18.
    #
    # A LIST per language, not a single string, deliberately breaking the
    # `Dict[str, str]` shape Scenario uses for name/place. A vocabulary target
    # legitimately has several correct renderings — judge_llm already credits
    # both デカフェ and カフェインレス for 'decaf' — so a single authored string
    # would reject a learner who used a valid synonym. Telling a learner they
    # failed a task they completed is the worst failure this project has, and
    # symmetry with Scenario is not worth manufacturing one.
    vocab_translations: Dict[str, List[str]] = field(default_factory=dict)
    # Authored translations of what the learner reads, per language:
    # {"Japanese": {"goal": ..., "hint": ...}}. The local model used to
    # translate these at session start — 18-33s on the loading screen, and
    # sometimes wrong enough to make a task unwinnable ("sterling silver"
    # rendered プラチナ銀製; whole goals left in English). OPEN-42.
    translations: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # The scenario story thread this task belongs to (Scenario.threads), or
    # 'general' for one that fits any visit (greeting, thanks, paying).
    # Empty when the scenario is unlabeled.
    thread: str = ""

@dataclass
class Scenario:
    name: str
    place: str
    role: str
    speaker: str
    tasks: List[Task]
    # Optional pool of session-level obstacles. One is picked at random per
    # playthrough and injected into the actor prompt for flavour — never used
    # by the task judge. Empty means "no complication this scenario".
    complications: List[str] = field(default_factory=list)
    name_translations: Dict[str, str] = field(default_factory=dict)
    place_translations: Dict[str, str] = field(default_factory=dict)
    # Story threads: {id: description}. A session is drawn from one or two of
    # them (plus 'general'), so a visit tells one plausible story instead of
    # ten unrelated errands at one counter (playtest 2026-09-27, OPEN-53).
    threads: Dict[str, str] = field(default_factory=dict)

    def get_session_tasks(self, num_tasks=10, advanced_ratio=0.7, seen_goals=None, retry_goals=None) -> List[Task]:
        """Returns a session biased toward advanced (C1-style) tasks, with
        standard tasks filling the remainder."""
        max_retries = num_tasks // 3
        valid_retries = {t.goal for t in self.tasks if retry_goals and t.goal in retry_goals}
        if len(valid_retries) > max_retries:
            active_retries = set(random.sample(sorted(valid_retries), max_retries))
        else:
            active_retries = valid_retries

        def _order_pool(pool):
            retries = [t for t in pool if t.goal in active_retries]
            if seen_goals is not None:
                unseen = [t for t in pool if t.goal not in active_retries and t.goal not in seen_goals]
                already = [t for t in pool if t.goal not in active_retries and t.goal in seen_goals]
            else:
                unseen = [t for t in pool if t.goal not in active_retries]
                already = []
            random.shuffle(retries)
            random.shuffle(unseen)
            random.shuffle(already)
            return retries + unseen + already

        story = self._story_tasks(num_tasks, round(num_tasks * advanced_ratio), active_retries,
                                  seen_goals or set())
        advanced = [t for t in story if t.difficulty == "advanced"]
        standard = [t for t in story if t.difficulty == "standard"]
        if active_retries or seen_goals is not None:
            advanced = _order_pool(advanced)
            standard = _order_pool(standard)
        else:
            random.shuffle(advanced)
            random.shuffle(standard)

        num_advanced = min(len(advanced), round(num_tasks * advanced_ratio))
        num_standard = min(len(standard), num_tasks - num_advanced)
        session = advanced[:num_advanced] + standard[:num_standard]

        if len(session) < num_tasks:
            leftover = advanced[num_advanced:] + standard[num_standard:]
            session += leftover[:num_tasks - len(session)]

        session = self._one_farewell(session)
        random.shuffle(session)
        # Stable sort by conversational stage: opening tasks first, closing
        # tasks last (a farewell the very last), everything else in between.
        # Stability preserves the random order within each phase, so replays
        # still vary.
        session.sort(key=lambda t: (t.phase, is_farewell(t)))

        # Guarantee the FIRST task is not reactive — reactive tasks presuppose a
        # prior exchange (an order placed, a drink received) and read as
        # nonsensical at the start of a conversation, and they also feed
        # build_task_setup_block into the greeting, leaving the NPC to invent an
        # exchange that never happened.
        #
        # This used to look for the first phase-2 task, but phase-1 tasks sort
        # first and 13 of them are reactive, so it inspected a slot that was
        # never the opening one — 2.8% of draws opened reactive (OPEN-30).
        #
        # Two invariants have to hold together: phases must stay non-decreasing,
        # and the opening task must not be reactive. Reordering can only satisfy
        # both when a non-reactive task already sits at the opening phase, so
        # when one does not, the fix is to change WHAT was drawn rather than the
        # order — a scenario has 69 tasks and only ten are used, so an unused
        # non-reactive task of the same phase is almost always available.
        if session and session[0].reactive:
            opening_phase = session[0].phase
            swap = next((j for j in range(1, len(session))
                         if session[j].phase == opening_phase and not session[j].reactive
                         and not is_farewell(session[j])),
                        None)
            if swap is not None:
                session[0], session[swap] = session[swap], session[0]
            else:
                drawn = {t.goal for t in session}

                def _candidates(difficulty=None):
                    return [t for t in self.tasks
                            if t.phase == opening_phase
                            and not t.reactive
                            and not is_farewell(t)       # never open with a goodbye
                            and t.goal not in drawn
                            and (difficulty is None or t.difficulty == difficulty)]

                # Match the difficulty being replaced first. The session is
                # drawn to an advanced_ratio, and substituting a standard task
                # for an advanced one dilutes it — which showed up immediately
                # as a flaky failure in the advanced-bias test.
                pool = _candidates(session[0].difficulty) or _candidates()
                if pool:
                    session[0] = random.choice(pool)

        return session

    def _one_farewell(self, session: List[Task]) -> List[Task]:
        """Swap every farewell after the first for an unused, non-farewell
        task — of the same difficulty when there is one, so the advanced
        ratio holds."""
        farewells = [t for t in session if is_farewell(t)]
        if len(farewells) <= 1:
            return session
        drawn = {t.goal for t in session}
        out = []
        for t in session:
            if is_farewell(t) and t is not farewells[0]:
                spare = [u for u in self.tasks if u.goal not in drawn and not is_farewell(u)]
                pool = [u for u in spare if u.difficulty == t.difficulty] or spare
                if not pool:
                    continue                  # a short session beats a second goodbye
                t = random.choice(pool)
                drawn.add(t.goal)
            out.append(t)
        return out

    def _story_tasks(self, num_tasks: int, num_advanced: int, keep=frozenset(),
                     seen=frozenset()) -> List[Task]:
        """The tasks this session may draw from: one primary thread, one
        secondary, and the 'general' tasks — widened a thread at a time only
        when the pool cannot fill the session's counts. Tasks being retried
        (`keep`) are always in. Threads holding more tasks the learner has
        not seen come first, and the counts are met from unseen tasks where
        the catalogue allows, so variety across sessions is not traded away
        for a story. Unlabeled scenarios use every task."""
        if not self.threads:
            return list(self.tasks)
        ids = list(self.threads)
        random.shuffle(ids)                       # random among equals
        ids.sort(key=lambda tid: -sum(t.thread == tid and t.goal not in seen for t in self.tasks))
        fresh = [t for t in self.tasks if t.goal not in seen]
        if (sum(t.difficulty == 'advanced' for t in fresh) < num_advanced
                or sum(t.difficulty != 'advanced' for t in fresh) < num_tasks - num_advanced):
            seen = frozenset()                    # not enough unseen anywhere: ignore it
        chosen = {'general'}
        for tid in ids:
            chosen.add(tid)
            pool = [t for t in self.tasks if t.thread in chosen or t.goal in keep]
            unseen = [t for t in pool if t.goal not in seen]
            advanced = sum(t.difficulty == 'advanced' for t in unseen)
            standard = len(unseen) - advanced
            if (len(chosen) >= 3 and advanced >= num_advanced
                    and standard >= num_tasks - num_advanced):
                return pool
        return list(self.tasks)

