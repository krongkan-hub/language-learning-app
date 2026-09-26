"""Words the feedback filter (app/coach/filters.py) reads, in both languages.

Data only — no functions.
"""

# Reasons that mark a Level up bullet as a SITUATIONAL FIT problem rather than
# ordinary polish. Measured on real output: told "Give me a large coffee." at a
# café, the model files the fix under Level up with "more polite and natural in
# a service context", leaving Feedback saying "Perfectly natural!". The eval
# scores Feedback and the repeat drill only drills Feedback, so those fixes
# reached neither. Promoting them is what makes the situational feature bite —
# it caught roughly a third of violations without this.
#
# The list is deliberately about POLITENESS AND REGISTER, not "more natural":
# the latter is ordinary style polish, which is what Level up is for and which
# the learner should not be made to retype.
_FIT_MARKERS = (
    'polite', 'politeness', 'courteous', 'respectful', 'formal', 'rude',
    'blunt', 'demanding', 'softer', 'service context',
    '丁寧', '敬語', '失礼', 'ぶっきらぼう', '柔らか', '目上', '接客',
)

# Politeness already present in the learner's own sentence. Japanese: the
# ます/です register and the request forms built on it. English: the modal and
# softener set that makes a request rather than a command.
_POLITE_ALREADY = (
    'ます', 'です', 'ください', 'いただけ', 'もらえ', 'でしょうか', 'ますか',
    'please', 'could you', 'could i', 'would you', 'would like', 'may i',
    # Any "Can I ..." / "Can you ...": seen live, "Can I pay by card?" at a
    # café came back as a drilled ❌ → "May I pay by card, please?".
    'can i ', 'can you ', 'excuse me', "i'd like",
)
