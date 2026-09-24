"""F0.5, the metric the GEC field scores corrections with.

    F0.5 = 1.25 * P * R / (0.25 * P + R)

It weights precision twice as heavily as recall, for the reason this project
arrived at independently and wrote into OPEN-39 and OPEN-49: a learner told
their correct sentence is wrong loses more than a learner told nothing. Using
the field's metric rather than a private one means our numbers can be compared
with published ones, and that the weighting is a citation rather than an
opinion.

HOW P AND R ARE COUNTED HERE, because the mapping is an approximation and
should not be quoted as if it were ERRANT's:

    TP  a probe sentence whose planted error was corrected
    FN  a probe sentence whose planted error was missed
    FP  a CLEAN sentence that was "corrected" anyway

Real ERRANT aligns edits, so it also counts a wrong correction of a real error
as both FP and FN. Our probes carry exactly one planted error and score by
whether the expected fix appears, so a wrong fix counts only as FN and our
precision reads slightly high. The clean arm is what keeps it honest, and it
is why every suite here runs one.
"""


def f_half(tp: int, fn: int, fp: int) -> tuple:
    """Return (precision, recall, F0.5) as fractions of 1.0."""
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    denom = 0.25 * precision + recall
    f = (1.25 * precision * recall / denom) if denom else 0.0
    return precision, recall, f


def format_f_half(tp: int, fn: int, fp: int) -> str:
    """One reportable line. Deliberately NOT worded 'Final ... Score', which
    is the string check_evals.sh gates on — the floors are set against the
    recall numbers those suites already print, and a second matching line
    would silently become the gated one."""
    precision, recall, f = f_half(tp, fn, fp)
    return (f"F0.5 (precision-weighted, GEC convention): {100 * f:.1f}%  "
            f"[P {100 * precision:.1f}% R {100 * recall:.1f}%, "
            f"TP {tp} FN {fn} FP {fp}]")
