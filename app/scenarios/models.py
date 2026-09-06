from dataclasses import dataclass, field
from typing import Dict, List
import random

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

        advanced = [t for t in self.tasks if t.difficulty == "advanced"]
        standard = [t for t in self.tasks if t.difficulty == "standard"]
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

        random.shuffle(session)
        # Stable sort by conversational stage: opening tasks first, closing
        # tasks last, everything else in between. Stability preserves the
        # random order within each phase, so replays still vary.
        session.sort(key=lambda t: t.phase)

        # Guarantee the first phase-2 task is not reactive — reactive tasks
        # presuppose a prior exchange (an order placed, a drink received, etc.)
        # and read as nonsensical at the start of a conversation.
        first_mid = next((i for i, t in enumerate(session) if t.phase == 2), None)
        if first_mid is not None and session[first_mid].reactive:
            swap = next((j for j in range(first_mid + 1, len(session))
                         if session[j].phase == 2 and not session[j].reactive),
                        None)
            if swap is not None:
                session[first_mid], session[swap] = session[swap], session[first_mid]

        return session

