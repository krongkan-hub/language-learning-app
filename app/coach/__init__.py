"""The coach: grammar feedback on what the learner just wrote.

Split by job, and each part says what it is for:

    prompt.py       what the model is told
    filters.py      what survives between its reply and the screen
    nets/           deterministic rules that catch what the model missed
    verdict.py      the clean verdict, and reading corrections back out
    pipeline.py     assembling one turn from all of the above

Every name the single-file version exposed is re-exported here, so nothing
that imports `app.coach` needed changing when this was split.
"""
from .prompt import (COACH_OPTS, COACH_SITUATION, COACH_SYS,
                     coach_system, describe_situation)
from .filters import (filter_coach_output, _clean_level_up_block,
                      _introduces_new_content, _normalize_phrase,
                      _normalize_quotes, _promote_fit_bullet,
                      _quote_is_the_learners, _tidy_whitespace)
from .nets.english import apply_verbform_net
from .nets.japanese import (apply_apology_net, apply_collocation_net,
                            apply_conjugation_net, apply_counter_net,
                            apply_existence_net, apply_particle_net,
                            apply_register_net, apply_transitivity_net,
                            apply_word_order_net, _ja_subject_is_someone_else)
from .verdict import (CLEAN_MARKERS, CLEAN_SENTINEL, clean_marker,
                      correction_targets, is_clean_verdict,
                      localize_clean_verdict, _drop_foreign_reasons)
from .pipeline import call_coach, coach_feedback

# Everything the single-file version exposed. Declared so the linter
# knows a front door re-exports on purpose.
__all__ = [
    CLEAN_MARKERS, CLEAN_SENTINEL, COACH_OPTS,
    COACH_SITUATION, COACH_SYS, _clean_level_up_block,
    _drop_foreign_reasons, _introduces_new_content, _ja_subject_is_someone_else,
    _normalize_phrase, _normalize_quotes, _promote_fit_bullet,
    _quote_is_the_learners, _tidy_whitespace, apply_apology_net,
    apply_collocation_net, apply_conjugation_net, apply_counter_net,
    apply_existence_net, apply_particle_net, apply_register_net,
    apply_transitivity_net, apply_verbform_net, apply_word_order_net,
    call_coach, clean_marker, coach_feedback,
    coach_system, correction_targets, describe_situation,
    filter_coach_output, is_clean_verdict, localize_clean_verdict,
]
