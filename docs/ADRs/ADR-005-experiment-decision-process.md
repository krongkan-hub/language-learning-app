# ADR-005: How experiments are decided in this repo

**Status:** Accepted
**Owner:** `architect_agent`

## Context

This project runs experiments constantly — review-block wordings, splitter
designs, translation detectors, coach nets — and for a long time decided
each one by looking at two fractions and picking the bigger one. That works
until the fractions are close, and this repo has direct, repeated evidence
of how badly "close" can mislead:

- `dev/fixtures/eval_baselines.json` records the actor's English arm
  reading 84.0 / 80.0 / 87.0 / 82.0 across four runs of **identical code** —
  a 10-point-wide spread with no change in the tree, on a suite whose
  documented failure signature never fired.
- The same file records the Japanese greeting cell in `eval_rawactor.py`
  swinging 75.0 / 75.0 / 25.0 across three readings of identical code — at
  n=48 the binomial standard error is 6.7 points, so a 95% interval is
  roughly ±13, wide enough to swallow a 50-point-looking swing.
- `docs/BACKLOG.md` OPEN-39 records a coach net that scored *higher* on its
  target metric (58/60 vs. 50/60) and was rejected anyway, because the
  higher score came from over-correcting short replies the metric's clean
  arm never sampled — a case where the better fraction was the worse
  change.

A 6-point "improvement" at n=40 is statistically indistinguishable from
noise this repo has already measured on unchanged code. Shipping it teaches
the wrong lesson twice: once when it goes in, and again when someone has to
explain later why it didn't hold.

## Decision

An experiment in this repo is not decided by comparing two fractions. It is
decided by `dev/evals/abstats.py` and `dev/evals/fhalf.py`, applied to
paired per-case data an existing probe already wrote out, read with
`dev/tools/ab_report.py`:

1. **Wilson score intervals**, not raw percentages. 19/40 is reported as
   "somewhere in 33%-63%," not "47.5%," so a point estimate is never read as
   the finding on its own. The Wilson form is used rather than the textbook
   normal interval because at these sample sizes the normal interval lies
   in a way that matters — 0/40 under it reads as a 0%-0% claim of
   certainty from a sample that has simply not seen a rare event yet.

2. **Exact McNemar, on paired outcomes.** Every A/B comparison in this repo
   runs both arms on the *same* cases, which means only the turns where the
   two arms disagree carry any information about a difference — turns where
   both succeed or both fail say nothing about which is better. McNemar's
   exact form is a binomial test on those discordant pairs alone, needing no
   library and no normal-approximation assumption, which matters because n
   is often small enough that the approximation would lie. This is also why
   a two-sample test (unpaired, e.g. a t-test on two independent fractions)
   is the wrong tool here: it would throw away the pairing this repo's
   probes are specifically designed to produce.

3. **A verdict that is allowed to say nothing.** `abstats.verdict()` returns
   one of: the two arms are numerically identical; one wins at p<0.05; or
   **TOO CLOSE TO CALL** — explicitly, "do not ship this as an improvement;
   run more, or measure something else." The third outcome is the point of
   the file. A tool that only ever names a winner would have called four of
   the last several actor readings above a difference that was later shown
   to be the same code.

4. **F0.5, not accuracy or plain recall, for any correction-style probe**
   (the coach nets, the translation detectors). Precision is weighted twice
   recall — `F0.5 = 1.25·P·R / (0.25·P + R)` — because a learner told their
   correct sentence is wrong loses more than a learner told nothing, a
   position this repo reached independently on two different probes
   (OPEN-39, OPEN-49) before adopting the published GEC field's metric
   instead of keeping that weighting as an unlabelled house opinion. Using
   the field's metric, rather than a private one, also means these numbers
   can be compared against published results instead of only against
   themselves.

5. **`ab_report.py` as the one path from probe output to a claim.** Probes
   already write per-case JSON as they run, so a result is re-analysable
   without spending another second of 7B time. `ab_report.py` reads one
   file's control/treatment arms, or the same arm across two files (for
   comparing two wordings, each measured against its own control on the
   same scenarios), pairs by `(case name, iteration index)`, and refuses to
   silently drop or mis-pair a case — an unpaired case is reported, not
   guessed at.

## Consequences

- **Positive:** a change is not called a win until the paired test clears
  p<0.05 against the arms it was actually run on. This directly targets the
  failure mode this repo has hit more than once — a swing inside a suite's
  own known noise band being written up as a result.
- **Positive:** "too close to call" is a legitimate, expected output, not a
  tool failure. Several of the swings cited in Context would have produced
  exactly that verdict had this existed at the time, instead of the
  numbers-moved-so-something-must-have-changed reading that followed them.
- **Negative — accepted:** this raises the bar for calling anything a win,
  which means some real, small improvements will correctly report as
  unproven rather than shipped. That is the trade being made on purpose: a
  gate that ships noise as improvement is worse than one that occasionally
  under-claims.
- **Negative — accepted:** McNemar's paired design only has statistical
  power where the arms disagree; a probe that produces very few
  discordant pairs (small n, or two arms that mostly agree) will read "too
  close to call" even for a real but small effect. The fix is more paired
  samples, not a different test — abstats.py takes no shortcut around this.
- **Rejected:** a t-test or other normal-approximation test on the two raw
  fractions. Rejected because it discards the pairing every probe here is
  built to produce, and because n is frequently too small for the normal
  approximation to be trustworthy at all.
- **Rejected:** judging a correction-style probe on accuracy or on plain
  recall. Both were rejected in favor of F0.5 specifically because this
  project independently found, on its own probes, that a wrong correction
  costs a learner more than a missed one — see OPEN-39's over-correction of
  short replies for the concrete case that motivated this.

## Follow-up

`ab_report.py`'s two-file mode compares the *same* arm across two files (two
wordings, each with its own control), not two different arms across two
files. Anyone reaching for it to compare an old experiment's treatment arm
against a new experiment's control arm is using it outside what the pairing
guarantees and should re-derive McNemar by hand rather than trust the tool's
output.
