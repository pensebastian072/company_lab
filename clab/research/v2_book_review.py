"""The v2 book, read as a book: what the whole workbook looks like beside production.

E36 asked whether the candidate model abstains less and E37 asked where the score movement
comes from. This asks the question a person actually opens the file with: **is this a
usable ranking, and is it the same ranking?**

DESCRIPTIVE ONLY. No prediction, no criterion, nothing to pass or fail - so it needs no
pre-registration and grants no licence. Every number here is "how the two books differ",
never "which one is right"; there is no forward-return grader in this repo (hard rule 1).

The three things worth knowing before trusting a ranking:

  1. **Is it banded?** A book where nearly everything clears the 0.80 coverage gate has
     stopped using abstention to discriminate, which is a change in what a top rank MEANS
     even when no company moved.
  2. **Is it the same order?** Rank correlation and top-50 overlap say whether this is the
     old book with better coverage or a different book.
  3. **What is broken in it?** Companies whose judged half failed to generate at all, and
     companies still below the gate.

    python -m clab.research.v2_book_review --v2-parquet D:\\company_lab_v2\\data\\scores.parquet
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .. import config
from ..net import atomic_write_json
from ..scoring import rubric

OUT_JSON = config.JOURNAL_DIR / "experiments" / "v2_book_review.json"
OUT_MD = config.JOURNAL_DIR / "experiments" / "v2_book_review.md"

#: Read from the rubric, never typed in. A hand-written list here dropped EXCEPTIONAL and
#: HIGH_CONVICTION on the first run - six companies vanished from a distribution table that
#: still looked tidy, which is the exact failure this whole module exists to notice.
BAND_ORDER = tuple(name for _threshold, name in rubric.BANDS) + (rubric.INSUFFICIENT_BAND,)
TOP_N = 50


def _spearman(a: pd.Series, b: pd.Series) -> float | None:
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 10:
        return None
    return float(d["a"].rank().corr(d["b"].rank()))


def _dist(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {"n": 0}
    return {
        "n": int(len(s)),
        "mean": round(float(s.mean()), 2),
        "p25": round(float(s.quantile(0.25)), 2),
        "median": round(float(s.median()), 2),
        "p75": round(float(s.quantile(0.75)), 2),
        "max": round(float(s.max()), 2),
    }


def _bands(df: pd.DataFrame) -> dict:
    counts = df["band"].value_counts().to_dict()
    return {b: int(counts.get(b, 0)) for b in BAND_ORDER} | {
        "other": int(sum(v for k, v in counts.items() if k not in BAND_ORDER))
    }


def run(v2_parquet: str, v1_parquet: str | None = None) -> dict:
    v1 = pd.read_parquet(v1_parquet or config.SCORES_PARQUET)
    v2 = pd.read_parquet(v2_parquet)
    both = v1.merge(v2, on="ticker", suffixes=("_v1", "_v2"))

    # Cross-sector comparison is `sector_neutral_score`, not `score` (2026-08-25). The
    # ranking questions below use it wherever both lanes have one.
    sn1, sn2 = "sector_neutral_score_v1", "sector_neutral_score_v2"
    has_sn = sn1 in both.columns and sn2 in both.columns

    top_overlap = None
    if has_sn:
        t1 = set(both.nlargest(TOP_N, sn1)["ticker"])
        t2 = set(both.nlargest(TOP_N, sn2)["ticker"])
        top_overlap = {
            "n": TOP_N,
            "shared": len(t1 & t2),
            "entered": sorted(t2 - t1)[:25],
            "left": sorted(t1 - t2)[:25],
        }

    sectors = []
    for sector, block in both.groupby("sector_v1"):
        if len(block) < 10:
            continue
        sectors.append({
            "sector": str(sector),
            "n": int(len(block)),
            "median_score_v1": round(float(block["score_v1"].median()), 1),
            "median_score_v2": round(float(block["score_v2"].median()), 1),
            "banded_v1": round(float((block["band_v1"] != "INSUFFICIENT_DATA").mean()), 3),
            "banded_v2": round(float((block["band_v2"] != "INSUFFICIENT_DATA").mean()), 3),
            "median_coverage_v1": round(float(block["coverage_v1"].median()), 3),
            "median_coverage_v2": round(float(block["coverage_v2"].median()), 3),
        })
    sectors.sort(key=lambda s: s["median_score_v2"] - s["median_score_v1"], reverse=True)

    # What is broken in the v2 book: a judged component with nothing in it. `*_available`
    # is the points that could have been earned, so zero means the component produced no
    # usable answer at all - not a low score, an absent one.
    broken = []
    for code in rubric.GENERATED_COMPONENTS:
        col = f"{code.lower()}_available_v2"
        if col not in both.columns:
            continue
        dead = both[(both[col] == 0) & (both[f"{code.lower()}_available_v1"] > 0)]
        broken.append({
            "component": code,
            "n_dead_in_v2": int(len(dead)),
            "tickers": sorted(dead["ticker"].tolist())[:25],
        })

    gate = rubric.MIN_COVERAGE_FOR_BAND if hasattr(rubric, "MIN_COVERAGE_FOR_BAND") else 0.80
    return {
        "study": "v2_book_review",
        "descriptive_only": True,
        "v2_parquet": str(v2_parquet),
        "n_v1": int(len(v1)),
        "n_v2": int(len(v2)),
        "n_comparable": int(len(both)),
        "n_v2_only": int(len(set(v2["ticker"]) - set(v1["ticker"]))),
        "n_v1_only": int(len(set(v1["ticker"]) - set(v2["ticker"]))),
        "score": {"v1": _dist(both["score_v1"]), "v2": _dist(both["score_v2"])},
        "coverage": {"v1": _dist(both["coverage_v1"]), "v2": _dist(both["coverage_v2"])},
        "coverage_gate": {
            "threshold": gate,
            "v1_clearing": int((both["coverage_v1"] >= gate).sum()),
            "v2_clearing": int((both["coverage_v2"] >= gate).sum()),
        },
        "bands": {
            "v1": _bands(both.rename(columns={"band_v1": "band"})),
            "v2": _bands(both.rename(columns={"band_v2": "band"})),
        },
        "agreement": {
            "spearman_score": _spearman(both["score_v1"], both["score_v2"]),
            "spearman_sector_neutral": _spearman(both[sn1], both[sn2]) if has_sn else None,
            "same_band": int((both["band_v1"] == both["band_v2"]).sum()),
            "top_overlap": top_overlap,
        },
        "sectors": sectors,
        "broken_components": broken,
        "top25_v2": (
            both.nlargest(25, sn2)[["ticker", "name_v1", "sector_v1", "score_v1",
                                    "score_v2", sn1, sn2, "band_v2"]]
            .round(1).to_dict("records") if has_sn else []
        ),
    }


def _fmt_md(res: dict) -> str:
    sc, cov, ag = res["score"], res["coverage"], res["agreement"]
    b1, b2 = res["bands"]["v1"], res["bands"]["v2"]
    lines = [
        "# The v2 book beside production",
        "",
        f"v1 {res['n_v1']} companies · v2 **{res['n_v2']}** · comparable "
        f"{res['n_comparable']} · in v2 only {res['n_v2_only']} · in v1 only "
        f"{res['n_v1_only']}. **Descriptive only** - no criterion, nothing promoted, and "
        "neither book has ever been graded against forward returns.",
        "",
        "## Shape of the two books",
        "",
        "| | n | mean | p25 | median | p75 | max |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| score v1 | {sc['v1']['n']} | {sc['v1']['mean']} | {sc['v1']['p25']} | "
        f"{sc['v1']['median']} | {sc['v1']['p75']} | {sc['v1']['max']} |",
        f"| score v2 | {sc['v2']['n']} | {sc['v2']['mean']} | {sc['v2']['p25']} | "
        f"{sc['v2']['median']} | {sc['v2']['p75']} | {sc['v2']['max']} |",
        f"| coverage v1 | {cov['v1']['n']} | {cov['v1']['mean']} | {cov['v1']['p25']} | "
        f"{cov['v1']['median']} | {cov['v1']['p75']} | {cov['v1']['max']} |",
        f"| coverage v2 | {cov['v2']['n']} | {cov['v2']['mean']} | {cov['v2']['p25']} | "
        f"{cov['v2']['median']} | {cov['v2']['p75']} | {cov['v2']['max']} |",
        "",
        f"Coverage gate {res['coverage_gate']['threshold']}: "
        f"**{res['coverage_gate']['v1_clearing']} → "
        f"{res['coverage_gate']['v2_clearing']}** of {res['n_comparable']}.",
        "",
        "| band | v1 | v2 |",
        "|---|---:|---:|",
    ]
    for band in BAND_ORDER:
        lines.append(f"| {band} | {b1.get(band, 0)} | {b2.get(band, 0)} |")
    lines += [
        "",
        "## Is it the same ranking?",
        "",
        f"* Spearman on `score`: **{ag['spearman_score']:.3f}**",
        f"* Spearman on `sector_neutral_score` (the cross-sector headline): "
        f"**{ag['spearman_sector_neutral']:.3f}**",
        f"* Same band: **{ag['same_band']}** of {res['n_comparable']} "
        f"(**{ag['same_band'] / max(res['n_comparable'], 1) * 100:.0f}%**)",
    ]
    if ag["top_overlap"]:
        t = ag["top_overlap"]
        lines += [
            f"* Top {t['n']} by `sector_neutral_score`: **{t['shared']} of {t['n']} "
            "shared**",
            f"  * entered: {', '.join(t['entered']) or 'none'}",
            f"  * left: {', '.join(t['left']) or 'none'}",
        ]
    lines += [
        "",
        "## By sector, most improved first",
        "",
        "| sector | n | median score v1 → v2 | banded v1 → v2 | median coverage v1 → v2 |",
        "|---|---:|---:|---:|---:|",
    ]
    for s in res["sectors"]:
        lines.append(
            f"| {s['sector']} | {s['n']} | {s['median_score_v1']} → "
            f"{s['median_score_v2']} | {s['banded_v1'] * 100:.0f}% → "
            f"{s['banded_v2'] * 100:.0f}% | {s['median_coverage_v1']} → "
            f"{s['median_coverage_v2']} |")
    lines += [
        "",
        "## Broken in the v2 book",
        "",
        "A judged component with **zero available points** in v2 where v1 had some: the "
        "component generated nothing usable. Not a low score - an absent one.",
        "",
        "| component | companies |",
        "|---|---:|",
    ]
    for b in res["broken_components"]:
        lines.append(f"| {b['component']} | {b['n_dead_in_v2']} |")
    for b in res["broken_components"]:
        if b["tickers"]:
            lines.append("")
            lines.append(f"{b['component']}: {', '.join(b['tickers'])}")
    lines += [
        "",
        "## Top 25 of the v2 book",
        "",
        "| # | ticker | sector | score v1 → v2 | sector-neutral v1 → v2 | band v2 |",
        "|---:|---|---|---:|---:|---|",
    ]
    for i, row in enumerate(res["top25_v2"], 1):
        lines.append(
            f"| {i} | {row['ticker']} | {row['sector_v1']} | "
            f"{row['score_v1']} → {row['score_v2']} | "
            f"{row['sector_neutral_score_v1']} → {row['sector_neutral_score_v2']} | "
            f"{row['band_v2']} |")
    lines += [
        "",
        "## What this is not",
        "",
        "Evidence that either book works. A higher score is a higher score; **no company "
        "here has been checked against what it did next.** `promoted` is false.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2-parquet", default=r"D:\company_lab_v2\data\scores.parquet")
    ap.add_argument("--v1-parquet", default=None)
    ap.add_argument("--json", default=str(OUT_JSON))
    ap.add_argument("--md", default=str(OUT_MD))
    args = ap.parse_args(argv)

    res = run(args.v2_parquet, args.v1_parquet)
    atomic_write_json(Path(args.json), res)
    Path(args.md).write_text(_fmt_md(res), encoding="utf-8")
    ag = res["agreement"]
    print(f"v1 {res['n_v1']} / v2 {res['n_v2']} / comparable {res['n_comparable']}")
    print(f"coverage gate {res['coverage_gate']['v1_clearing']} -> "
          f"{res['coverage_gate']['v2_clearing']}")
    print(f"spearman score {ag['spearman_score']}, sector-neutral "
          f"{ag['spearman_sector_neutral']}, top-50 shared "
          f"{(ag['top_overlap'] or {}).get('shared')}")
    print(f"wrote {args.json} and {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
