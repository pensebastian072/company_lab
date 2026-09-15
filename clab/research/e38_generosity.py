"""E38 - is the candidate's extra generosity the MODEL or the FORMAT?

Registered at `journal/experiments/E38_control_lane_preregistration.md`.

E37 found that half of the v2 lane's +8.74 is not abstention-filling at all: the candidate
awards **more points on the sub-tests both lanes scored**, +4.22 in score units, and it is
nearly one question - `bq_moat`. E36 could not say whether that was the model or the
schema-plus-token-budget it ran under. Three caches now exist, so the difference splits:

    qwen-v1  -> qwen-structured    the FORMAT effect   (same model, new regime)
    qwen-structured -> LFM2.5      the MODEL effect    (same regime, new model)
    qwen-v1  -> LFM2.5             what E36 measured   (both at once)

Everything here is measured on **BQ moat dimensions**, read straight from the payloads,
for two reasons: the control lane is never folded into scorecards (there is no third
workbook), and `bq_moat` is where E37 localised the disagreement. `bq_points` is E39's
rubric-A2 reimplementation, which has its own tests.

Two views, because they answer different questions:

* **`bq_moat` points** - what the framework would actually award, 0-15, computed only
  where BOTH lanes clear the 6-of-11 quorum. This is the number that moves a ranking.
* **Common-support dimension delta** - mean 0-5 difference over the dimensions **both
  lanes scored**, per company. Immune to one lane simply answering more questions.

    python -m clab.research.e38_generosity
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
from pathlib import Path

from .. import config
from ..net import atomic_write_json
from ..scoring import rubric
from .e39_unjustified_dimensions import bq_points

OUT_JSON = config.JOURNAL_DIR / "experiments" / "E38_generosity.json"
OUT_MD = config.JOURNAL_DIR / "experiments" / "E38_generosity.md"

V1_DIR = str(config.DATA_ROOT / "qual")
CONTROL_DIR = str(config.DATA_ROOT / "qual_qwen_struct")
V2_DIR = str(config.DATA_ROOT / "qual_lfm25")


def load_bq(directory: str) -> dict[str, dict[str, int]]:
    """{ticker: {dimension: score}} - only dimensions that carry a score."""
    out: dict[str, dict[str, int]] = {}
    for path in glob.glob(os.path.join(directory, "*_BQ_*.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        ticker = payload.get("ticker")
        if not ticker:
            continue
        out[ticker] = {
            key: rec["score"]
            for key, rec in (payload.get("dimensions") or {}).items()
            if isinstance(rec, dict) and isinstance(rec.get("score"), int)
            and not isinstance(rec.get("score"), bool)
        }
    return out


def compare(a: dict, b: dict, label_a: str, label_b: str) -> dict:
    """b minus a, paired on companies present in both caches."""
    common = sorted(set(a) & set(b))
    pts_a: list[int] = []
    pts_b: list[int] = []
    dim_deltas: list[float] = []
    n_shared_dims = 0

    for ticker in common:
        sa, sb = a[ticker], b[ticker]
        pa, pb = bq_points(list(sa.values())), bq_points(list(sb.values()))
        # Both lanes must clear the 6-of-11 quorum, or the pair is not a pair: comparing
        # a scored company against an unscored one measures coverage, not generosity.
        if pa is not None and pb is not None:
            pts_a.append(pa)
            pts_b.append(pb)
        shared = set(sa) & set(sb)
        if shared:
            n_shared_dims += len(shared)
            dim_deltas.append(statistics.fmean(sb[k] - sa[k] for k in shared))

    return {
        "from": label_a,
        "to": label_b,
        "n_paired_companies": len(common),
        "bq_moat": {
            "n_both_scored": len(pts_a),
            "mean_from": round(statistics.fmean(pts_a), 2) if pts_a else None,
            "mean_to": round(statistics.fmean(pts_b), 2) if pts_b else None,
            "delta": round(statistics.fmean(pts_b) - statistics.fmean(pts_a), 3)
            if pts_a else None,
            "max_points": rubric.COMPONENTS["BQ"][1],
        },
        "common_support_dimension_delta": {
            "n_companies": len(dim_deltas),
            "n_shared_dimensions": n_shared_dims,
            "mean": round(statistics.fmean(dim_deltas), 3) if dim_deltas else None,
            "median": round(statistics.median(dim_deltas), 3) if dim_deltas else None,
            "share_positive": round(
                sum(1 for d in dim_deltas if d > 0) / len(dim_deltas), 3)
            if dim_deltas else None,
            "scale": rubric.BQ_DIMENSION_MAX,
        },
    }


def run(v1_dir: str = V1_DIR, control_dir: str = CONTROL_DIR,
        v2_dir: str = V2_DIR) -> dict:
    v1, control, v2 = load_bq(v1_dir), load_bq(control_dir), load_bq(v2_dir)
    if not control:
        raise SystemExit(f"no control payloads in {control_dir} - has the lane run?")

    fmt = compare(v1, control, "qwen-v1", "qwen-structured")
    model = compare(control, v2, "qwen-structured", "LFM2.5")
    both = compare(v1, v2, "qwen-v1", "LFM2.5")

    f_delta = fmt["bq_moat"]["delta"] or 0.0
    m_delta = model["bq_moat"]["delta"] or 0.0
    total = both["bq_moat"]["delta"] or 0.0
    return {
        "experiment": "E38",
        "n_control_companies": len(control),
        "min_for_reporting": 100,
        "sufficient": len(control) >= 100,
        "format_effect": fmt,
        "model_effect": model,
        "e36_pair": both,
        "attribution": {
            "bq_moat_total_delta": total,
            "share_format": round(f_delta / total, 3) if total else None,
            "share_model": round(m_delta / total, 3) if total else None,
        },
    }


def _fmt_md(res: dict) -> str:
    def row(block: dict) -> str:
        b, c = block["bq_moat"], block["common_support_dimension_delta"]
        return (f"| {block['from']} → **{block['to']}** | {block['n_paired_companies']} | "
                f"{b['n_both_scored']} | {b['mean_from']} → {b['mean_to']} | "
                f"**{b['delta']:+}** | {c['mean']:+} |")

    att = res["attribution"]
    lines = [
        "# E38 - generosity: the model or the format?",
        "",
        f"Control lane at **{res['n_control_companies']} companies** "
        + ("(past the registered 100 minimum)." if res["sufficient"]
           else "- BELOW the registered 100 minimum, so no criterion is called.")
        + " Measured on BQ moat dimensions read from the payloads; the control lane is "
          "never folded, and `bq_moat` is where E37 localised the disagreement.",
        "",
        "| comparison | paired | both scored | mean `bq_moat` /15 | Δ points | Δ per "
        "shared dimension /5 |",
        "|---|---:|---:|---:|---:|---:|",
        row(res["format_effect"]),
        row(res["model_effect"]),
        row(res["e36_pair"]),
        "",
        "`bq_moat` is compared only where **both** lanes clear the 6-of-11 quorum - "
        "otherwise the number measures coverage, not generosity. The last column is the "
        "mean 0-5 gap over the dimensions both lanes scored, which no amount of "
        "answering-more-questions can move.",
        "",
        "## Attribution",
        "",
        f"Of the **{att['bq_moat_total_delta']:+}** points E36 measured between "
        "production and the v2 lane:",
        "",
        f"* the **format** (schema + 2,500 tokens) accounts for "
        f"**{(att['share_format'] or 0) * 100:.0f}%**",
        f"* the **model** accounts for **{(att['share_model'] or 0) * 100:.0f}%**",
        "",
        "## What this does not establish",
        "",
        "That the more generous scorer is the better one. There is no forward-return "
        "grader in this repo, so a higher moat score is a higher moat score. `promoted` "
        "stays false.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v1-dir", default=V1_DIR)
    ap.add_argument("--control-dir", default=CONTROL_DIR)
    ap.add_argument("--v2-dir", default=V2_DIR)
    ap.add_argument("--json", default=str(OUT_JSON))
    ap.add_argument("--md", default=str(OUT_MD))
    args = ap.parse_args(argv)

    res = run(args.v1_dir, args.control_dir, args.v2_dir)
    atomic_write_json(Path(args.json), res)
    Path(args.md).write_text(_fmt_md(res), encoding="utf-8")
    att = res["attribution"]
    print(f"control n={res['n_control_companies']}  "
          f"format {res['format_effect']['bq_moat']['delta']:+}  "
          f"model {res['model_effect']['bq_moat']['delta']:+}  "
          f"total {att['bq_moat_total_delta']:+} of 15")
    print(f"share format {att['share_format']}, share model {att['share_model']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
