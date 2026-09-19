"""The model layer: everything that talks to the 7B, and the guards on it.

Split by job:

    client.py     loading the model, the prompt cache, one chat call
    guards.py     script checks, question shape, the actor validator
    vocab.py      the vocabulary block and reading it back
    translate.py  task objectives into the language being studied
    actor.py      the NPC prompt, its repair loop, and both read paths

Every name the single-file version exposed is re-exported here, so nothing
that imports `app.llm` needed changing when this was split.
"""
from .client import (BASE_MODEL, DEBUG, MLX_ERRORS, TRANSLATE_OPTS,
                     PROMPT_CACHE_MAX_ENTRIES, PROMPT_CACHE_MAX_KV_SIZE,
                     PROMPT_CACHE_PREFIX_THRESHOLD, _llm_chat, _ensure_model,
                     _longest_common_prefix, _prepare_prompt_cache_for_call,
                     _save_prompt_cache_on_success, _prompt_caches,
                     describe_llm_error, reset_prompt_caches, strip_think_tags)
from .client import CLOSED_OPENERS, WH_WORDS, EMOJI_PATTERN
from .guards import (_SIMPLIFIED_CHARS, _SIMPLIFIED_RANGES,
                     _TRADITIONAL_CHARS, _FOREIGN_SCRIPT_RANGES,
                     find_english_clause, find_english_word,
                     find_wrong_script,
                     is_closed_question, is_question, sanitize,
                     sanitize_learner_input, sentence_rejection_reason,
                     validate)
from .vocab import (match_vocab_block, match_vocab_fields, strip_vocab_block)
from .translate import (TRANSLATE_RETRY_LIMIT, find_foreign_wording,
                        translate_hints, _looks_untranslated,
                        _JOINERS, _KANA_OR_KANJI, _LATIN_RUN)
from .actor import (ACTOR_OPTS, ACTOR_SYS, GREETING_SYS, NPC_MOODS,
                    FALLBACK_ACTOR_LINE, FALLBACK_ACTOR_LINE_JA,
                    SALVAGE_QUESTIONS, SALVAGE_QUESTIONS_JA,
                    build_task_setup_block, call_actor, repair_actor_output,
                    salvage_actor_output, stream_actor)

# Everything the single-file version exposed. Declared so the linter
# knows a front door re-exports on purpose.
__all__ = [
    ACTOR_OPTS, ACTOR_SYS, BASE_MODEL,
    CLOSED_OPENERS, DEBUG, EMOJI_PATTERN,
    FALLBACK_ACTOR_LINE, FALLBACK_ACTOR_LINE_JA, GREETING_SYS,
    MLX_ERRORS, NPC_MOODS, PROMPT_CACHE_MAX_ENTRIES,
    PROMPT_CACHE_MAX_KV_SIZE, PROMPT_CACHE_PREFIX_THRESHOLD, SALVAGE_QUESTIONS,
    SALVAGE_QUESTIONS_JA, TRANSLATE_OPTS, TRANSLATE_RETRY_LIMIT,
    WH_WORDS, _FOREIGN_SCRIPT_RANGES, _JOINERS,
    _KANA_OR_KANJI, _LATIN_RUN, _SIMPLIFIED_CHARS,
    _SIMPLIFIED_RANGES, _TRADITIONAL_CHARS, _ensure_model,
    _llm_chat, _longest_common_prefix, _looks_untranslated,
    _prepare_prompt_cache_for_call, _prompt_caches, _save_prompt_cache_on_success,
    build_task_setup_block, call_actor, describe_llm_error,
    find_english_clause, find_english_word, find_foreign_wording,
    find_wrong_script,
    is_closed_question, is_question, match_vocab_block,
    match_vocab_fields, repair_actor_output, reset_prompt_caches,
    salvage_actor_output, sanitize, sanitize_learner_input,
    sentence_rejection_reason, stream_actor, strip_think_tags,
    strip_vocab_block, translate_hints, validate,
]
