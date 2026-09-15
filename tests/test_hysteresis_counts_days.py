"""E27: a band reading is a calendar day, not an invocation of the scorer.

F3 exists because E03 R4 measured raw bands flipping in 27.2% of months with a median
2-month life, and `BAND_CONFIRM_READINGS = 2` was supposed to mean "two readings agree".
It counted CALLS instead. Fifteen full re-scores over three days of rubric work advanced
every company's hysteresis fifteen times, and the run that exposed it changed **zero** of
1,500 composite scores while moving **54 bands** - MU to HIGH_CONVICTION, GOOGL down to
WATCHLIST - on no new information at all.

H1 below is that bug written as a test.
"""
from clab.scoring import composite, rubric
from clab.scoring.types import ComponentScore, Status, SubTest


def _card(points, *, as_of, prior_band=None, prior_pending=None, prior_streak=0,
          prior_date=None):
    comps = {}
    for code, (_label, mx) in rubric.COMPONENTS.items():
        earned = min(mx, max(0, int(round(mx * points / rubric.TOTAL_POINTS))))
        comps[code] = ComponentScore(
            code=code, label=code, max_points=mx,
            subtests=[SubTest(key=f"{code}_x", label=code, max_points=mx,
                              earned=earned, status=Status.SCORED)])
    return composite.Scorecard(
        ticker="T", cik="1", as_of=as_of, components=comps,
        prior_band=prior_band, prior_band_pending=prior_pending,
        prior_band_streak=prior_streak, prior_band_reading_date=prior_date)


# ------------------------------------------------------------------ H1
def test_rescoring_the_same_day_does_not_advance_the_band():
    """The bug. Two calls, one day, no new information -> the band must not move."""
    first = _card(72, as_of="2026-08-23T09:00:00+00:00",
                  prior_band="WATCHLIST", prior_pending="INVESTABLE", prior_streak=1,
                  prior_date="2026-08-23")
    assert first.band == "WATCHLIST"           # NOT confirmed by a same-day re-run
    assert first.band_pending == "INVESTABLE"
    assert first.band_pending_streak == 1

    # and again, an hour later, still the same day
    second = _card(72, as_of="2026-08-23T10:30:00+00:00",
                   prior_band=first.band, prior_pending=first.band_pending,
                   prior_streak=first.band_pending_streak,
                   prior_date=first.band_reading_date)
    assert second.band == "WATCHLIST"
    assert second.band_pending_streak == 1


# ------------------------------------------------------------------ H2
def test_a_new_day_still_confirms():
    """The smoothing has to survive the fix, or the cure is worse than the disease."""
    card = _card(72, as_of="2026-08-24T09:00:00+00:00",
                 prior_band="WATCHLIST", prior_pending="INVESTABLE", prior_streak=1,
                 prior_date="2026-08-23")
    assert card.band == "INVESTABLE"           # second reading, second day: confirmed


def test_the_state_machine_itself_is_a_no_op_on_the_same_day():
    same = rubric.advance_band("WATCHLIST", "INVESTABLE", 1, "INVESTABLE", same_day=True)
    assert same == ("WATCHLIST", "INVESTABLE", 1)
    nextday = rubric.advance_band("WATCHLIST", "INVESTABLE", 1, "INVESTABLE",
                                  same_day=False)
    assert nextday[0] == "INVESTABLE"


def test_a_scorecard_written_before_E27_is_not_frozen():
    """No stored reading date reads as 'a different day', so the first run after the fix
    behaves exactly as it did before rather than pinning every band forever."""
    card = _card(72, as_of="2026-08-23T09:00:00+00:00",
                 prior_band="WATCHLIST", prior_pending="INVESTABLE", prior_streak=1,
                 prior_date=None)
    assert card.band == "INVESTABLE"


def test_the_reading_date_comes_from_as_of_not_the_clock():
    """`build_scorecard` is deterministic and takes its time from the caller. A clock
    here would make the same inputs produce different bands on different days."""
    card = _card(72, as_of="2019-01-02T00:00:00+00:00")
    assert card.band_reading_date == "2019-01-02"


# ------------------------------------------------------------------ E33: the ordering
# E27 added the same-day no-op ABOVE the coverage-gate exemption, and that exemption's
# own comment says it "has to be exempt to work at all here". The no-op returned `current`
# and short-circuited it, so a company whose coverage crossed 0.80 on a day it was
# re-scored stayed INSUFFICIENT_DATA until the next calendar day. Measured 2026-08-25:
# 13 companies displayed as unrankable while holding a real band_raw - BMY among them at
# coverage 0.894 and score 72 with band_raw INVESTABLE.
def test_crossing_the_coverage_gate_beats_the_same_day_no_op():
    from clab.scoring.rubric import INSUFFICIENT_BAND, advance_band
    shown, pending, streak = advance_band(INSUFFICIENT_BAND, None, 0, "INVESTABLE",
                                          same_day=True)
    assert shown == "INVESTABLE", "a same-day coverage gain must still band the company"
    assert pending is None and streak == 0


def test_losing_the_coverage_gate_is_exempt_in_the_same_direction():
    """Symmetric, so the exemption cannot bias the ranking upward."""
    from clab.scoring.rubric import INSUFFICIENT_BAND, advance_band
    shown, _p, _s = advance_band("INVESTABLE", None, 0, INSUFFICIENT_BAND, same_day=True)
    assert shown == INSUFFICIENT_BAND


def test_the_same_day_no_op_still_governs_ordinary_score_wobble():
    """E27's property must survive: re-scoring twice in one day cannot advance a band
    that is merely drifting across a threshold."""
    from clab.scoring.rubric import advance_band
    assert advance_band("INVESTABLE", None, 0, "WATCHLIST", same_day=True) \
        == ("INVESTABLE", None, 0)
    assert advance_band("INVESTABLE", None, 0, "WATCHLIST", same_day=False) \
        == ("INVESTABLE", "WATCHLIST", 1)
