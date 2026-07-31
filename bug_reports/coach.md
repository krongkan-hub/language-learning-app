# Bug Reports — Coach (`app/coach.py`)

### BUG-001 · OPEN · High
**Real errors demoted into `⬆️ Level up` while `💡 Feedback` still says "Perfectly natural!"**
Most-repeated defect in the original playtest (~6 occurrences). Example: coach's
own stated reason was "to agree with the plural 'two'" — a grammar correction —
filed under Level up instead of Feedback, while Feedback read "Perfectly
natural!". `filter_coach_output` treats the two sections independently; a
correction-shaped Level-up bullet coexisting with the Feedback sentinel is
never caught.
*Suggested fix:* if a Level-up bullet reads as a grammatical correction (not a
stylistic upgrade), promote it into Feedback and drop the sentinel.

### BUG-002 · FIXED-UNCOMMITTED
**"Perfectly natural!" leaked through alongside real corrections.**
Working-tree diff (`app/coach.py`, `filter_coach_output`) now strips any
"perfectly natural" line whenever `corrections` is non-empty. Logic looks
correct; needs a live eval run to confirm (see `eval/coach_cases.json`).

### BUG-003 · OPEN · High
**Target-language leakage in the reason text.** With `language='English'`,
reasons came back in Chinese (`形容词"fast"需要改为…`) and Japanese
(`自然な表現です`). The reason is the entire pedagogical payload of the
feature; an unreadable reason makes the correction worthless. Prompt-level
issue — `COACH_SYS` already says "Everything you write ... must be in
{language}" but the model doesn't reliably comply. No code-level fix found in
the working tree.

### BUG-004 · OPEN · Medium
**Factually wrong metalanguage in a reason.** `"what happen"→"what happens"`
was explained as "use plural verb for plural subject" — backwards; "happens"
is 3rd-person singular. Correction was right, the taught grammar rule was
wrong. Model-behavior issue, not caught by any current guard.

### BUG-005 · OPEN · High
**Meaning-changing corrections**, explicitly forbidden by `COACH_SYS` ("Never
change the MEANING of what the learner said"). Examples: `"it is broken"→"it
was broken"` when the screen was still broken; Japanese `夜9時です→夜9時までです`
turned "my flight is at 9pm" into "until 9pm". No code-level guard exists —
this is a prompt-adherence failure that needs either a stronger prompt
constraint or a post-hoc check (e.g. re-ask the model "does the correction
preserve the original meaning?").

### BUG-006 · OPEN · Medium
**False-positive correction of a valid synonym**, also forbidden by
`COACH_SYS`. `"decided"` was marked wrong in favor of `"determined"` — both
are correct.

### BUG-007 · OPEN · Medium
**Level up chains off the coach's own correction rather than the learner's
original words.** Observed: Feedback corrected `decided`→`determined`, then
Level up suggested `determined`→`set`. Three words of noise for one
correction. `filter_coach_output` doesn't currently pass the *original*
learner phrase forward as the anchor for Level-up suggestions.

### BUG-008 · OPEN · Low
**Exact/near-duplicate content across Feedback and Level-up not filtered.**
One run printed the identical correction in both sections. `_clean_level_up_block`
only compares quotes *within* one bullet — there's no Feedback↔Level-up
cross-check, and no containment check (a separate run's Level-up suggestion
contained the original phrase verbatim as a "different" alternative).

### BUG-009 · OPEN · Low
**"Maximum 2 corrections" rule isn't enforced in code.** `COACH_SYS` states
the rule but one run emitted 3 Feedback bullets. Add a hard cap in
`filter_coach_output` rather than relying on prompt compliance alone.

### BUG-036 · OPEN (live-confirmed) · High
**Live eval run (2026-07-31, `scripts/eval_coach.py`, temp=0.2, 5 iterations)
reproduces the recall-failure pattern from the cross-cutting note below as a
100%-reproducible miss.** Input `"Is it prohibit here?"` (missing passive
participle, should be "prohibited") got `💡 Feedback: Perfectly natural!` on
**5/5** runs at temperature 0.2 — not a flaky occasional miss, a
deterministic-at-this-temperature blind spot for this error shape. This is
the same failure family as BUG-001 (real error → no correction surfaced) but
distinct: BUG-001 is *misclassification* (error caught but filed in the
wrong section); this is *non-detection* (error not caught at all). Filed as
`eval/coach_cases.json` case 11 — currently failing and should stay in the
suite as a known-red regression case until the prompt/detection logic
improves, not deleted to make the suite green.

### BUG-037 · NEEDS-DISCUSSION (live-confirmed) · Medium
**Possible new false-positive correction, or an eval-fixture calibration
issue — needs a Japanese-fluent reviewer, not just code-reading.** Same live
run, input `"コーヒーを一つ欲しいだ、ブラックで。"` (pre-existing eval case 6, expects
a polite request form in the correction). 5/5 runs: coach correctly fixed
`一つ欲しいだ→一つ欲しい` (drops the ungrammatical だ) but *also* corrected
`ブラックで→ブラックの`. "〜で" here is the standard idiomatic way to specify how
a drink is ordered ("ブラックで お願いします" = "[I'd like it] black") — sounds like
a legitimate `BUG-006`-class false-positive on valid phrasing, changing で
(instrumental/manner) to の (possessive/adjectival). *Or* the eval fixture's
`must_contain` list (`ください`/`お願い`/`ほしい`/`欲しいです`) is simply too
narrow and doesn't anticipate this (otherwise correct) alternative
completion — in which case this is a test-fixture gap, not a coach bug.
Don't resolve either direction without a native/fluent judgment call.

---
**Cross-cutting note:** recall is size-dependent — short 1-2-error sentences
tend to get "Perfectly natural!"; long, error-dense sentences get 2-3 good
catches but miss others. BUG-036 above is now a concrete, reproducible
instance of this pattern rather than just an observed tendency.
