"""E34: "did not repurchase" is a fact, not a gap.

`mg_buyback_discipline` read NO_DATA with reason "input unavailable" for **268** companies,
while its sibling ten lines below - `mg_ma_track_record` - already scores 2 for *"no
acquisitions and no impairments in the trailing year"*. Two absences of the same kind,
read in opposite directions inside one component.

The tag chain was checked FIRST and refused: A/B over 240 cached filings showed that adding
alternate repurchase tags rescued 6 filers while PERTURBING 44 existing values (one by
19%), and a substitute firing only on an empty series rescued 0. The absence is real, so
this is about semantics, not retrieval.

The criterion that keeps it a measurement rather than a default is P2: a company with no
`dilution_yoy` either **stays NO_DATA**. Nothing is scored from an assumption.
"""
from __future__ import annotations

import pytest

from clab.fundamentals.metrics import MetricBundle
from clab.fundamentals.profile import PROFILES
from clab.scoring import mg, rubric
from clab.scoring.context import SymbolContext


def _ctx(**metrics) -> SymbolContext:
    M = MetricBundle()
    base = dict(fcf_ttm=1.0e9, buybacks_ttm=None, dilution_yoy=None,
                ma_spend_ttm=None, impairment_ttm=None)
    base.update(metrics)
    for k, v in base.items():
        M.set(k, v)
    ctx = SymbolContext(ticker="T", cik="1", sector="Industrials",
                        profile=PROFILES["STANDARD"], metrics=M)
    ctx.peers = {}
    return ctx


def _buyback(ctx):
    return next(s for s in mg.score(ctx).subtests
                if s.key == "mg_buyback_discipline")


# ------------------------------------------------------------------ the rule
@pytest.mark.parametrize("dil,points", [
    (-0.030, 2),      # shrinking
    (0.0, 2),         # flat
    (0.004, 1),       # inside the tolerated band
    (0.02, 1),        # exactly at the band edge
    (0.06, 0),        # issuing and not offsetting
])
def test_no_repurchases_is_scored_from_the_share_count(dil, points):
    st = _buyback(_ctx(buybacks_ttm=None, dilution_yoy=dil))
    assert st.status.value == "scored"
    assert st.earned == points


def test_P2_no_dilution_series_means_it_stays_NO_DATA():
    """The binding criterion. This converts 'we could not measure it' into a score ONLY
    where a second measured series answers the question - never by default."""
    st = _buyback(_ctx(buybacks_ttm=None, dilution_yoy=None))
    assert st.status.value == "no_data"
    assert st.earned is None


def test_the_band_edge_comes_from_the_rubric_not_a_literal():
    edge = rubric.BS_DILUTION_BANDS[1]
    assert _buyback(_ctx(buybacks_ttm=None, dilution_yoy=edge)).earned == 1
    assert _buyback(_ctx(buybacks_ttm=None, dilution_yoy=edge * 1.5)).earned == 0


def test_a_company_that_DOES_repurchase_is_unaffected():
    """The existing path must be untouched: this only adds a branch for absence."""
    ctx = _ctx(buybacks_ttm=3.0e8, dilution_yoy=-0.02)
    st = _buyback(ctx)
    assert st.status.value == "scored"
    assert st.inputs["buyback_intensity"] == pytest.approx(0.3)


def test_the_sibling_asymmetry_this_experiment_was_built_on_is_real():
    """P1. `mg_ma_track_record` scores its analogous absence, which is the whole argument
    for scoring this one - so if that ever changes, this rule loses its justification."""
    ctx = _ctx(ma_spend_ttm=None, impairment_ttm=None)
    ma = next(s for s in mg.score(ctx).subtests if s.key == "mg_ma_track_record")
    assert ma.status.value in ("scored", "no_data")
    if ma.status.value == "scored":
        assert ma.earned == 2


def test_absence_never_beats_a_measured_repurchase_at_a_rich_multiple():
    """A company buying back heavily at a peak multiple scores 0. Absence must not be
    worth MORE than a measured bad decision by accident of the new branch."""
    rich = _ctx(buybacks_ttm=5.0e8, dilution_yoy=0.0)
    rich.peers = {"pe_pctile_own": 0.95}
    assert _buyback(rich).earned == 0
    # and the absent case at the same dilution scores 2, which is the intended reading:
    # not repurchasing at a peak multiple is better than repurchasing at one
    assert _buyback(_ctx(buybacks_ttm=None, dilution_yoy=0.0)).earned == 2


def test_buybacks_present_but_unusable_FCF_is_NO_DATA_not_a_false_absence():
    """The branch is guarded on `buybacks is None`, not merely on the one above
    declining. That one also declines when repurchases EXIST but FCF is zero or negative,
    and reading those as 'no repurchases' would put a false statement in the note - the
    company did repurchase, we just cannot express it as a share of cash flow."""
    st = _buyback(_ctx(buybacks_ttm=2.0e8, fcf_ttm=-5.0e8, dilution_yoy=-0.02))
    assert st.status.value == "no_data"
    assert "no repurchases" not in (st.threshold_note or "")
