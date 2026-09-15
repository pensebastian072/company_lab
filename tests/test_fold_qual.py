"""The fold that carries cached judgement scores onto scorecards.

Two failures on consecutive days motivated every test here, and both had the same
shape: the fold looked like it worked and the task exited 0.

  * 2026-08-15 - folding by BATCH MANIFEST stranded anything scored outside the last
    run, so an overnight catch-up would have sat in the cache forever.
  * 2026-08-16 - the fold was refused by the crawl probe gate, 99 scorecards stayed
    behind their cache, and the daily task still reported exit=0.
"""
from __future__ import annotations

import json

import pytest

from clab import config
from clab.runner import fold_qual


@pytest.fixture()
def qual_dirs(tmp_path, monkeypatch):
    """Point the module's two directories at a tmp tree."""
    cards = tmp_path / "scorecards"
    qual = tmp_path / "qual"
    cards.mkdir()
    qual.mkdir()
    monkeypatch.setattr(config, "SCORECARD_DIR", cards)
    monkeypatch.setattr(config, "QUAL_DIR", qual)
    return cards, qual


def _card(cards, cik, ticker, *, sg, bq):
    (cards / f"{cik}_{ticker}.json").write_text(json.dumps({
        "ticker": ticker,
        "components": {
            "SG": {"available_points": sg},
            "BQ": {"available_points": bq},
        },
    }), encoding="utf-8")


def _bq_cache(qual, cik, n_dims):
    dims = {f"d{i}": {"score": 1} for i in range(n_dims)}
    dims["absent"] = {"score": None}
    (qual / f"{cik}_BQ_hash.json").write_text(
        json.dumps({"dimensions": dims}), encoding="utf-8")


@pytest.fixture(autouse=True)
def resolvable_ciks(monkeypatch):
    """Fake tickers resolve to a fake CIK by default.

    main() now filters out tickers whose CIK cannot be resolved, because those can never
    be folded through --symbols (KMT's live case). Without this the suite's invented
    tickers all look unresolvable and no test would reach the batch at all. Tests that
    care about the unresolvable path override this explicitly.
    """
    monkeypatch.setattr("clab.sources.edgar_tickers.cik_for",
                        lambda t: f"cik-{t}")


@pytest.fixture()
def all_components(monkeypatch):
    """Stub the scorer's 'this CIK has a complete cached judgement half' answer."""
    seen = set()

    def _set(*ciks):
        seen.clear()
        seen.update(ciks)

    monkeypatch.setattr("clab.qual.scorer.ciks_with_all_components", lambda: set(seen))
    return _set


# ------------------------------------------------------------------ detection
def test_a_scorecard_with_no_judgement_half_is_stale(qual_dirs, all_components):
    cards, qual = qual_dirs
    all_components("0000000001")
    _card(cards, "0000000001", "AAA", sg=0, bq=0)
    # The cache must actually hold a score. A CIK reported by ciks_with_all_components
    # always has its files on disk, so a test that mocks the former without the latter
    # is describing a state the system cannot be in.
    (qual / "0000000001_SG_h.json").write_text(
        json.dumps({"scores": {"growth": {"score": 4}}}), encoding="utf-8")
    assert fold_qual.stale_tickers() == ["AAA"]


def test_a_scorecard_that_already_shows_its_cache_is_not_stale(qual_dirs, all_components):
    cards, qual = qual_dirs
    all_components("0000000001")
    _card(cards, "0000000001", "AAA", sg=20, bq=15)
    _bq_cache(qual, "0000000001", 8)
    assert fold_qual.stale_tickers() == []


def test_a_stale_bq_is_caught_even_when_sg_landed(qual_dirs, all_components):
    """The subtle case a missing-SG check misses entirely.

    BQ was generated while Ollama was degraded, came out under the 6-dimension floor
    and scored 0. It has since been re-generated and now clears the floor - but the
    scorecard still carries the 0. Checking only for a missing SG calls this up to date.
    """
    cards, qual = qual_dirs
    all_components("0000000001")
    _card(cards, "0000000001", "AAA", sg=20, bq=0)
    _bq_cache(qual, "0000000001", fold_qual.BQ_MIN_DIMENSIONS)
    assert fold_qual.stale_tickers() == ["AAA"]


def test_a_thinly_assessed_bq_is_now_stale(qual_dirs, all_components):
    """E19 inverted this case.

    Under the old cliff, five cached dimensions scored ZERO, so a scorecard showing 0 was
    correct and re-folding it forever was the bug. Now those five buy 7 of 15 points of
    availability, so the same scorecard IS behind - and leaving this test as written
    would have stranded every company assessed on one to five dimensions, which is 234 of
    them and the whole point of the change.
    """
    cards, qual = qual_dirs
    all_components("0000000001")
    _card(cards, "0000000001", "AAA", sg=20, bq=0)
    _bq_cache(qual, "0000000001", fold_qual.BQ_MIN_DIMENSIONS - 1)
    assert fold_qual.stale_tickers() == ["AAA"]


def test_a_fully_abstained_cache_is_not_called_stale(qual_dirs, all_components):
    """MFP's live case: SG, BQ and MG all cached, every score null.

    Folding awards no points because there are none to award, so the scorecard's 0 is
    correct. Flagging it re-folds forever and - once the fold reports failure loudly -
    turns the watchdog permanently red for a company with nothing wrong with it.
    """
    cards, qual = qual_dirs
    all_components("0000000001")
    _card(cards, "0000000001", "MFP", sg=0, bq=0)
    (qual / "0000000001_SG_h.json").write_text(json.dumps(
        {"scores": {"growth": {"score": None}, "tam": {"score": None}}}),
        encoding="utf-8")
    assert fold_qual.stale_tickers() == []


def test_a_cache_with_one_real_score_IS_still_stale(qual_dirs, all_components):
    """The other side of it: one usable score means the fold has something to do."""
    cards, qual = qual_dirs
    all_components("0000000001")
    _card(cards, "0000000001", "AAA", sg=0, bq=0)
    (qual / "0000000001_SG_h.json").write_text(json.dumps(
        {"scores": {"growth": {"score": 3}, "tam": {"score": None}}}),
        encoding="utf-8")
    assert fold_qual.stale_tickers() == ["AAA"]


def test_a_ticker_with_no_resolvable_cik_is_named_not_buried(monkeypatch, capsys):
    """KMT's live case: the scorecard exists, et.cik_for returns None.

    batch --symbols logs "skip: no CIK", so the fold can never repair it and would
    report the same failure every run with no actionable difference.
    """
    monkeypatch.setattr(fold_qual, "stale_tickers", lambda: ["KMT", "AAA"])
    monkeypatch.setattr("clab.sources.edgar_tickers.cik_for",
                        lambda t: None if t == "KMT" else "0000000001")
    seen = {}
    monkeypatch.setattr("clab.runner.batch.main",
                        lambda argv: (seen.setdefault("argv", argv), 0)[1])

    fold_qual.main([])
    out = capsys.readouterr().out
    assert "no resolvable CIK" in out and "KMT" in out
    # and it must not be handed to a batch that will silently skip it
    assert "KMT" not in seen["argv"][1]


def test_a_cik_without_a_complete_cache_is_never_folded(qual_dirs, all_components):
    cards, _ = qual_dirs
    all_components()                              # nothing has a complete judgement half
    _card(cards, "0000000001", "AAA", sg=0, bq=0)
    assert fold_qual.stale_tickers() == []


# ------------------------------------------------------------------ the run
def test_the_fold_bypasses_the_probe_gate(monkeypatch, capsys):
    """A fold is a re-score from disk, not a cold crawl.

    On 2026-08-16 the probe aged out at 8 days, the gate refused a 99-company fold,
    and the day's judgement scores never reached a scorecard.
    """
    n = config.PROBE_GATE_SYMBOLS + 1
    stale = [f"T{i}" for i in range(n)]
    seen = {}

    monkeypatch.setattr(fold_qual, "stale_tickers", lambda: stale if not seen else [])
    monkeypatch.setattr("clab.runner.batch.main",
                        lambda argv: (seen.setdefault("argv", argv), 0)[1])

    assert fold_qual.main([]) == 0
    assert "--i-know" in seen["argv"]
    assert "bypassing the probe gate" in capsys.readouterr().out


def test_scorecards_still_behind_after_a_fold_exit_non_zero(monkeypatch, capsys):
    """The 2026-08-16 failure, asserted: never report success on an unfinished fold."""
    monkeypatch.setattr(fold_qual, "stale_tickers", lambda: ["AAA", "BBB"])
    monkeypatch.setattr("clab.runner.batch.main", lambda argv: 0)

    rc = fold_qual.main([])
    assert rc != 0
    out = capsys.readouterr().out
    assert "ERROR" in out and "STILL behind" in out


def test_a_clean_fold_exits_zero(monkeypatch, capsys):
    calls = {"n": 0}

    def _stale():
        calls["n"] += 1
        return ["AAA"] if calls["n"] == 1 else []

    monkeypatch.setattr(fold_qual, "stale_tickers", _stale)
    monkeypatch.setattr("clab.runner.batch.main", lambda argv: 0)

    assert fold_qual.main([]) == 0
    assert "after folding: 0 still stale" in capsys.readouterr().out


def test_a_failing_batch_propagates_its_code(monkeypatch):
    monkeypatch.setattr(fold_qual, "stale_tickers", lambda: ["AAA"])
    monkeypatch.setattr("clab.runner.batch.main", lambda argv: 1)
    assert fold_qual.main([]) == 1


def test_dry_run_never_folds(monkeypatch):
    monkeypatch.setattr(fold_qual, "stale_tickers", lambda: ["AAA"])

    def _boom(argv):
        raise AssertionError("dry run must not call the batch")

    monkeypatch.setattr("clab.runner.batch.main", _boom)
    assert fold_qual.main(["--dry-run"]) == 0
