"""The best-scoring companies OUTSIDE the current S&P 500, with their rank in the whole system.

The question this answers: of the ~1,000 mid and small caps the universe expansion added,
which score well, and where do they sit against the full 1,497?

Two things make a naive `sort by composite_strict` wrong today, and both are handled here:

  * **The judgement half is still filling.** A company with no SG/BQ/MG scores 0 on 50 of
    the 100 points, so an unscored company cannot rank and a partly-scored one is
    penalised for a queue position rather than a business. Only companies with the full
    judgement half AND >= MIN_COVERAGE are eligible, and the excluded count is reported.
  * **Rank means nothing without the same filter applied to everyone.** The system rank is
    computed over the eligible population, not over 1,497 rows of which half are blanks.

Read `docs/known_issues.md` and the E05/E11 verdicts before treating any of this as a buy
list. This ranking has NEVER been validated against forward returns; E05 measured the top
decile's median 3-year excess over SPY at -7.6%.

    python -m clab.research.outside_sp500
    python -m clab.research.outside_sp500 --top 25 --md docs/outside_sp500.md
"""
from __future__ import annotations

import argparse

import pandas as pd

from .. import config

#: hard rule 3: below this, a company gets NO band, so it must not get a rank either
MIN_COVERAGE = 0.80


def _sp500_tickers() -> set[str]:
    from ..runner import batch as batch_mod
    try:
        return {r["ticker"] for r in batch_mod.load_universe("sp500")}
    except Exception:                                   # noqa: BLE001
        return set()


def eligible(df: pd.DataFrame) -> pd.DataFrame:
    """Companies that can be ranked at all: full judgement half, adequate coverage."""
    ok = df.copy()
    ok["qual_available"] = ok.get("qual_available", False).fillna(False)
    have_qual = (ok["sg_available"].fillna(0) > 0) & (ok["mg_available"].fillna(0) > 0)
    return ok[have_qual & (ok["coverage"].fillna(0) >= MIN_COVERAGE)]


def run(top: int = 10) -> dict:
    df = pd.read_parquet(config.SCORES_PARQUET)
    sp500 = _sp500_tickers()

    elig = eligible(df).copy()
    elig = elig.sort_values("composite_strict", ascending=False).reset_index(drop=True)
    elig["system_rank"] = elig.index + 1

    outside = elig[~elig["ticker"].isin(sp500)] if sp500 else elig.iloc[0:0]

    return {
        "universe_rows": int(len(df)),
        "eligible": int(len(elig)),
        "excluded_no_judgement_or_coverage": int(len(df) - len(elig)),
        "sp500_known": len(sp500),
        "outside_eligible": int(len(outside)),
        "min_coverage": MIN_COVERAGE,
        "top": outside.head(top),
        "all_eligible": elig,
    }


def render(res: dict, top: int) -> str:
    t = res["top"]
    L = [f"# Best-scoring companies outside the current S&P 500", ""]
    L.append(f"{res['eligible']:,} of {res['universe_rows']:,} companies are rankable "
             f"today - the rest are **waiting on the judgement half** or sit under the "
             f"{res['min_coverage']:.0%} coverage floor and are excluded rather than "
             f"ranked low. Of the rankable, **{res['outside_eligible']:,} are outside "
             f"the current S&P 500**.")
    L.append("")
    L.append(f"`system_rank` is the position among all {res['eligible']:,} rankable "
             f"companies, S&P 500 included. That is the number that answers "
             f"\"where does this actually sit\".")
    L.append("")
    if t.empty:
        L.append("**Nothing outside the S&P 500 is rankable yet.** The judgement half has "
                 "not reached enough mid and small caps.")
        return "\n".join(L)
    L.append("| # | system rank | ticker | company | sector | composite | coverage | band |")
    L.append("|---:|---:|---|---|---|---:|---:|---|")
    for i, (_, r) in enumerate(t.iterrows(), 1):
        L.append(f"| {i} | **{int(r['system_rank'])}** | {r['ticker']} | "
                 f"{str(r['name'])[:34]} | {str(r['sector'])[:22]} | "
                 f"{r['composite_strict']:.1f} | {r['coverage']:.0%} | {r['band']} |")
    L.append("")
    ranks = [int(x) for x in t["system_rank"]]
    L.append(f"Their ranks run **{ranks[0]} to {ranks[-1]}** out of {res['eligible']:,}. "
             f"{sum(1 for r in ranks if r <= 50)} of the {len(ranks)} sit in the top 50.")
    L.append("")
    L.append("## Before treating this as a buy list")
    L.append("")
    L.append("- **This ranking has never been validated against forward returns.** There "
             "is no grader yet; it needs ~50 weekly snapshots and the `as_first_filed` "
             "restatement view, and grading on restated data would be look-ahead bias.")
    L.append("- **E05 measured the top decile's median 3-year excess over SPY at -7.6%.** "
             "The top decile of this very score underperformed the index at the median.")
    L.append("- **The score is substantially a sector bet** - three pre-registered "
             "studies say so, and BQ abstention being sector-structured (E12) is one "
             "mechanism by which it happens.")
    L.append("- **Half the points are a 7B model's judgement with no human review**, and "
             "a quarter of the universe scores 0 on Business Quality because it sits "
             "under the 6-of-11 dimension floor (E12).")
    L.append("- The judgement half is **still filling**, so this list will move. A "
             "company absent today may outrank these tomorrow.")
    L.append("")
    L.append("`promoted` is false. Nothing here is a recommendation.")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--md", help="also write the report here")
    args = ap.parse_args(argv)

    res = run(args.top)
    md = render(res, args.top)
    print(md)
    if args.md:
        from pathlib import Path
        Path(args.md).write_text(md, encoding="utf-8")
        print(f"\nwritten: {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
