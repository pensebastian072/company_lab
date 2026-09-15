"""The E43 contradiction gate must be able to fire AND to stay silent.

A rule that can only do one of those is not a check. E34's lesson on this box: a
verification that reads the wrong field passes quietly, and that is worse than no check at
all — so both directions are pinned here, not just the interesting one.
"""
from __future__ import annotations

import pytest

from clab.external import local_phase_b as PB


FIRES = [
    ("LAGGARD", "We are a leading global provider of security products and solutions."),
    ("CHALLENGER", "We are one of the largest vehicle technology suppliers in the world."),
    ("LAGGARD", "The Company is the world's largest producer of industrial gases."),
]

SILENT = [
    # the value agrees with the sentence
    ("LEADER", "We are a leading global provider of security products and solutions."),
    ("DOMINANT", "We are the largest producer in every market we serve."),
    # the leadership belongs to SOMEONE ELSE - evidence of nothing about the filer
    ("LAGGARD", "We offer an expansive list of products from leading suppliers."),
    ("CHALLENGER", "We acquired Traverse Systems, an industry-leading provider."),
    # no leadership assertion at all
    ("LAGGARD", "The Company operates 400 distribution centers across twelve states."),
]


@pytest.mark.parametrize("value,quote", FIRES)
def test_gate_fires_on_a_self_contradicting_claim(value, quote):
    assert PB.contradicts("competitive_position", value, quote) is not None


@pytest.mark.parametrize("value,quote", SILENT)
def test_gate_stays_silent_when_it_should(value, quote):
    assert PB.contradicts("competitive_position", value, quote) is None


def test_gate_ignores_fields_it_has_no_rule_for():
    """A rule for one field must never leak onto another."""
    assert PB.contradicts("pricing_power", "LOW",
                          "We are a leading global provider.") is None


def test_gate_tolerates_an_empty_quote():
    assert PB.contradicts("competitive_position", "LAGGARD", "") is None


def test_every_rule_names_values_that_exist_in_the_vocabulary():
    """A refuted value that the schema cannot produce is a dead rule."""
    from clab.external import schema as S
    for field, (_pred, refuted) in PB.CONTRADICTION_RULES.items():
        vocab = {v.upper() for v in S.VOCABULARIES[field]}
        assert refuted <= vocab, f"{field}: {refuted - vocab} not in the vocabulary"
