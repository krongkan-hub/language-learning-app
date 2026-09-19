"""Deterministic rules that catch what the model missed.

One file per class of error, because a net is only as safe as the
must-stay-quiet fixtures beside it and both should be findable.

Every net here obeys one rule: it only ever overturns a CLEAN verdict. A
real model correction always wins.
"""
from .apology import apply_apology_net
from .collocation import apply_collocation_net
from .conjugation import apply_conjugation_net
from .counter import apply_counter_net
from .english import apply_verbform_net
from .existence import apply_existence_net
from .particles import apply_particle_net
from .register import apply_register_net
from .transitivity import apply_transitivity_net
from .word_order import apply_word_order_net

__all__ = ['apply_apology_net', 'apply_collocation_net',
           'apply_conjugation_net', 'apply_counter_net',
           'apply_existence_net', 'apply_particle_net',
           'apply_register_net', 'apply_transitivity_net',
           'apply_verbform_net', 'apply_word_order_net']
