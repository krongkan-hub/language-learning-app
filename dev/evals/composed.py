"""Composed scenes for the actor suites' `--composed N --seed S` mode.

The archetypes are drawn exactly as eval_rawactor draws legacy scenarios
(`Random(seed).sample` over the catalogue), so `--composed 40 --seed 42` and
the default `--scenarios 40 --seed 42` cover the same 40 archetypes and differ
only in place, persona and complications. `default=True` gives each drawn
archetype's default composition — the legacy scenario — for a matched control.
"""
import random

from app.scenarios.compose import ARCHETYPES, compose, compose_from_spec, default_spec


def composed_scenes(n: int, seed: int, default: bool = False) -> list:
    """[(Scenario, SceneSpec)] for n archetypes, reproducible from seed."""
    ids = sorted(ARCHETYPES)
    picks = random.Random(seed).sample(range(len(ids)), min(n, len(ids)))
    out = []
    for i in picks:
        aid = ids[i]
        out.append(compose_from_spec(default_spec(aid)) if default
                   else compose(aid, random.Random(f'{seed}-{aid}')))
    return out
