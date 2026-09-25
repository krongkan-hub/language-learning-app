"""The statistics an A/B result needs before anyone is allowed to call it a win.

This project runs experiments constantly — three review-block wordings, two
splitter designs, two translation detectors — and decides them by looking at
two fractions. That works until the fractions are close, and this repo already
knows how badly it can go wrong: `eval_baselines.json` records the actor's
English arm moving 10 points and the Japanese greeting cell reading 75/75/25
ON UNCHANGED CODE. A 6-point "improvement" at n=40 is indistinguishable from
that, and shipping it teaches the wrong lesson twice — once when it goes in,
once when it is defended later.

So: no new model calls, no new fixtures. Three functions over numbers the
probes already produce.

    wilson        an interval for one rate. 19/40 is not "47.5%", it is
                  somewhere in 33%-63%, and saying so stops a reader treating
                  the point estimate as the finding.
    mcnemar       the paired test. A/B here always runs BOTH arms on the same
                  cases, which is worth a great deal statistically: only the
                  turns where the arms DISAGREE carry information, and the
                  test asks whether the disagreements lean one way further
                  than a coin would.
    verdict       the sentence a human should be allowed to write, given the
                  above — including "too close to call", which is the output
                  this file exists to make available.

WHY McNEMAR AND NOT A t-TEST. The outcome per turn is binary (the word was
reused or it was not), the arms are paired by construction, and n is small
enough that normal approximations are a lie. McNemar's exact form is a
binomial test on the discordant pairs, which needs no library and no
assumption beyond the pairing.
"""
import math


def wilson(successes: int, trials: int, z: float = 1.96) -> tuple:
    """A 95% confidence interval for a proportion, Wilson score form.

    Wilson rather than the textbook normal interval because at these counts
    the normal one is wrong in a way that matters: for 0/40 it produces
    0%-0%, a claim of certainty from a sample that has simply not seen a rare
    event yet.
    """
    if trials <= 0:
        return (0.0, 0.0)
    p = successes / trials
    denom = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    margin = (z * math.sqrt(p * (1 - p) / trials
                            + z * z / (4 * trials * trials)) / denom)
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def mcnemar(a_only: int, b_only: int) -> float:
    """Two-sided exact McNemar p-value from the two discordant counts.

    `a_only` is pairs where A succeeded and B did not; `b_only` the reverse.
    Pairs where both arms agree are deliberately absent — they carry no
    information about a difference, which is the whole point of pairing.
    """
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def verdict(a_name: str, a_successes: int, b_name: str, b_successes: int,
            trials: int, a_only: int, b_only: int, alpha: float = 0.05) -> str:
    """One sentence, and it is allowed to say nothing was shown."""
    p = mcnemar(a_only, b_only)
    lo_a, hi_a = wilson(a_successes, trials)
    lo_b, hi_b = wilson(b_successes, trials)
    better, worse = ((b_name, a_name) if b_successes > a_successes
                     else (a_name, b_name))
    head = (f'{a_name} {a_successes}/{trials} '
            f'[{100 * lo_a:.0f}-{100 * hi_a:.0f}%]  vs  '
            f'{b_name} {b_successes}/{trials} '
            f'[{100 * lo_b:.0f}-{100 * hi_b:.0f}%]  '
            f'(discordant {a_only}/{b_only}, p={p:.4f})')
    if a_successes == b_successes:
        return f'{head}\n  -> identical. Nothing to choose between them.'
    if p < alpha:
        return f'{head}\n  -> {better} wins (p<{alpha}).'
    return (f'{head}\n  -> TOO CLOSE TO CALL. {better} leads {worse}, but at '
            f'this sample size that lead is what unchanged code produces. '
            f'Do not ship it as an improvement; run more, or measure something '
            f'else.')


def paired_counts(a_outcomes: list, b_outcomes: list) -> tuple:
    """(a_only, b_only) from two equal-length lists of booleans, in pair order.

    Raises rather than truncating on a length mismatch: a silently shortened
    pairing is the kind of bug that produces a confident wrong answer, and
    this file exists to prevent those.
    """
    if len(a_outcomes) != len(b_outcomes):
        raise ValueError(f'unpaired: {len(a_outcomes)} vs {len(b_outcomes)}')
    a_only = sum(1 for a, b in zip(a_outcomes, b_outcomes) if a and not b)
    b_only = sum(1 for a, b in zip(a_outcomes, b_outcomes) if b and not a)
    return a_only, b_only
