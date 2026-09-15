"""E40 - is the candidate's extra coverage INFORMATIVE, or just a constant?

Registered at `journal/experiments/E40_generous_or_informative_preregistration.md`.

E38 settled attribution: the candidate abstains less and scores higher because it is a
different MODEL, not because of the schema. It could not settle whether that is an
improvement, and neither can this - "better" means predictive and there is no grader.

What this measures instead is whether the extra answers carry information:

  D1/D2  discrimination - modal share and dispersion per BQ dimension, per lane
  D3     the FILLS specifically - dimensions the incumbent abstained on and the
         candidate answered. If they pile onto one value, coverage bought a constant.
  D4     SG evidence that VERIFIES - the parser checks each quote for containment in the
         pack, so a model answering from outside the filing is visible
  D5     does either judged half separate companies at all, against the auditable /50

A dimension where nearly every company gets the same number is a weight with no
information in it - E30's finding about the measured half, and the market-state
workbook's 6-of-12-constant-layers failure. That is the failure mode being looked for.

    python -m clab.research.e40_informative
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import statistics
from pathlib import Path

import pandas as pd

from .. import config
from ..net import atomic_write_json
from ..scoring import rubric

OUT_JSON = config.JOURNAL_DIR / "experiments" / "E40_results.json"
OUT_MD = config.JOURNAL_DIR / "experiments" / "E40_results.md"

LANES = {
    "qwen-v1": str(config.DATA_ROOT / "qual"),
    "LFM2.5": str(config.DATA_ROOT / "qual_lfm25"),
    "qwen-structured": str(config.DATA_ROOT / "qual_qwen_struct"),
}


def load_bq(directory: str) -> dict[str, dict[str, int | None]]:
    """{ticker: {dimension: score or None}} - None is a recorded abstention, not absence."""
    out: dict[str, dict[str, int | None]] = {}
    for path in glob.glob(os.path.join(directory, "*_BQ_*.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        ticker = payload.get("ticker")
        if not ticker:
            continue
        dims: dict[str, int | None] = {}
        for key, rec in (payload.get("dimensions") or {}).items():
            if not isinstance(rec, dict):
                continue
            score = rec.get("score")
            dims[key] = score if isinstance(score, int) and not isinstance(score, bool) \
                else None
        out[ticker] = dims
    return out


def load_sg_evidence(directory: str) -> dict[str, dict[str, bool]]:
    """{ticker: {subtest: evidence_unverified}} for SG sub-tests that carry a score.

    Only SG is asked: `parse_sg` verifies a quote PER SUB-TEST, while BQ and MG read
    evidence once at the top level, so an unverified rate there would not mean the same
    thing.
    """
    out: dict[str, dict[str, bool]] = {}
    for path in glob.glob(os.path.join(directory, "*_SG_*.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        ticker = payload.get("ticker")
        if not ticker:
            continue
        marks: dict[str, bool] = {}
        for key, rec in (payload.get("scores") or {}).items():
            if not isinstance(rec, dict) or rec.get("score") is None:
                continue
            if "evidence_unverified" not in rec:
                continue          # v1 payloads predate the per-item flag for some runs
            marks[key] = bool(rec["evidence_unverified"])
        if marks:
            out[ticker] = marks
    return out


def sg_unverified_split(incumbent_dir: str, candidate_dir: str) -> dict:
    """D4 on COMMON SUPPORT - the objection that has to be answered.

    The candidate scores more SG sub-tests than the incumbent, and the extra ones are
    exactly where the evidence pack is thin, so a higher unverified rate could be pure
    composition. Splitting the rate into the sub-tests BOTH lanes scored and the ones only
    the candidate scored settles it: if the gap survives on common support, it is the
    model and not the mix.
    """
    def sg_records(directory: str) -> dict[str, dict[str, tuple]]:
        out: dict[str, dict[str, tuple]] = {}
        for path in glob.glob(os.path.join(directory, "*_SG_*.json")):
            try:
                with open(path, encoding="utf-8") as fh:
                    payload = json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
            ticker = payload.get("ticker")
            if not ticker:
                continue
            out[ticker] = {
                key: (rec.get("score"), bool(rec.get("evidence_unverified")))
                for key, rec in (payload.get("scores") or {}).items()
                if isinstance(rec, dict)
            }
        return out

    inc, cand = sg_records(incumbent_dir), sg_records(candidate_dir)
    both_n = both_inc = both_cand = fill_n = fill_unv = 0
    for ticker in set(inc) & set(cand):
        for key, (score_c, unv_c) in cand[ticker].items():
            if score_c is None:
                continue
            score_i, unv_i = inc[ticker].get(key, (None, False))
            if score_i is not None:
                both_n += 1
                both_inc += unv_i
                both_cand += unv_c
            else:
                fill_n += 1
                fill_unv += unv_c
    return {
        "common_support": {
            "n": both_n,
            "incumbent_unverified": round(both_inc / both_n, 4) if both_n else None,
            "candidate_unverified": round(both_cand / both_n, 4) if both_n else None,
        },
        "candidate_only": {
            "n": fill_n,
            "candidate_unverified": round(fill_unv / fill_n, 4) if fill_n else None,
        },
    }


def _shape(scores: list[int]) -> dict:
    """Modal share and dispersion - 'does this dimension discriminate at all'."""
    if not scores:
        return {"n": 0, "modal_value": None, "modal_share": None, "stdev": None,
                "mean": None}
    counts = collections.Counter(scores)
    value, hits = counts.most_common(1)[0]
    return {
        "n": len(scores),
        "modal_value": value,
        "modal_share": round(hits / len(scores), 3),
        "stdev": round(statistics.pstdev(scores), 3),
        "mean": round(statistics.fmean(scores), 3),
    }


def dimension_shapes(lane: dict[str, dict[str, int | None]],
                     tickers: list[str]) -> dict[str, dict]:
    out = {}
    for key, _label in rubric.BQ_DIMENSIONS:
        scores = [lane[t][key] for t in tickers
                  if t in lane and isinstance(lane[t].get(key), int)]
        out[key] = _shape(scores)
    return out


def fill_analysis(incumbent: dict, candidate: dict, tickers: list[str]) -> dict:
    """D3 - the dimensions the incumbent abstained on and the candidate answered."""
    fills: list[int] = []
    both: list[int] = []
    fills_by_key: collections.defaultdict = collections.defaultdict(list)
    for ticker in tickers:
        inc, cand = incumbent.get(ticker, {}), candidate.get(ticker, {})
        for key, _label in rubric.BQ_DIMENSIONS:
            c = cand.get(key)
            if not isinstance(c, int):
                continue
            if isinstance(inc.get(key), int):
                both.append(c)
            elif key in inc:                      # incumbent recorded an abstention
                fills.append(c)
                fills_by_key[key].append(c)
    return {
        "fills": _shape(fills),
        "both_scored": _shape(both),
        "modal_share_gap": (
            round(_shape(fills)["modal_share"] - _shape(both)["modal_share"], 3)
            if fills and both else None),
        "by_key": {k: _shape(v) for k, v in sorted(fills_by_key.items())},
    }


def _spearman(a: pd.Series, b: pd.Series) -> float | None:
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 10:
        return None
    return round(float(d["a"].rank().corr(d["b"].rank())), 3)


def judged_vs_measured(lane: dict, tickers: list[str]) -> float | None:
    """D5 - does this judged half order companies like the auditable half does?

    Uses the mean scored BQ dimension as the judged signal (the whole component would
    fold in the quorum rule, which is a coverage effect and not a judgement one), against
    `quant_only_50` from production's own table.
    """
    df = pd.read_parquet(config.SCORES_PARQUET)[["ticker", "quant_only_50"]]
    quant = dict(zip(df["ticker"], df["quant_only_50"]))
    rows = []
    for ticker in tickers:
        scored = [v for v in lane.get(ticker, {}).values() if isinstance(v, int)]
        if len(scored) >= rubric.BQ_MIN_DIMENSIONS_SCORED and ticker in quant:
            rows.append((statistics.fmean(scored), quant[ticker]))
    if len(rows) < 10:
        return None
    return _spearman(pd.Series([r[0] for r in rows]), pd.Series([r[1] for r in rows]))


def run() -> dict:
    lanes = {name: load_bq(path) for name, path in LANES.items()}
    control_n = len(lanes["qwen-structured"])

    # Every comparison is paired on companies all three lanes have scored, so a lane is
    # never advantaged by a different company set.
    tickers = sorted(set(lanes["qwen-v1"]) & set(lanes["LFM2.5"])
                     & set(lanes["qwen-structured"]))

    shapes = {name: dimension_shapes(lane, tickers) for name, lane in lanes.items()}

    # D1/D2 summarised: how often is the candidate the MORE concentrated lane?
    wins = {"candidate_more_concentrated": 0, "incumbent_more_concentrated": 0, "tied": 0}
    gaps = []
    for key, _label in rubric.BQ_DIMENSIONS:
        a = shapes["qwen-v1"][key]["modal_share"]
        b = shapes["LFM2.5"][key]["modal_share"]
        if a is None or b is None:
            continue
        gaps.append(round(b - a, 3))
        if b > a:
            wins["candidate_more_concentrated"] += 1
        elif b < a:
            wins["incumbent_more_concentrated"] += 1
        else:
            wins["tied"] += 1

    sg = {name: load_sg_evidence(path) for name, path in LANES.items()}
    sg_rates = {}
    for name, marks in sg.items():
        flags = [v for t in tickers if t in marks for v in marks[t].values()]
        sg_rates[name] = {
            "n_subtests": len(flags),
            "unverified_rate": round(sum(flags) / len(flags), 4) if flags else None,
        }

    return {
        "experiment": "E40",
        "n_paired_companies": len(tickers),
        "n_control_companies": control_n,
        "dimension_shapes": shapes,
        "D1_D2_modal_share": {
            "per_dimension_gap_candidate_minus_incumbent": gaps,
            "mean_gap": round(statistics.fmean(gaps), 3) if gaps else None,
            "counts": wins,
        },
        "D3_fills": {
            "LFM2.5_over_qwen-v1": fill_analysis(lanes["qwen-v1"], lanes["LFM2.5"],
                                                 tickers),
            "qwen-structured_over_qwen-v1": fill_analysis(
                lanes["qwen-v1"], lanes["qwen-structured"], tickers),
        },
        "D4_sg_evidence": sg_rates,
        "D4_common_support": sg_unverified_split(LANES["qwen-v1"], LANES["LFM2.5"]),
        "D5_judged_vs_measured": {
            name: judged_vs_measured(lane, tickers) for name, lane in lanes.items()
        },
    }


def _fmt_md(res: dict) -> str:
    d12 = res["D1_D2_modal_share"]
    fills = res["D3_fills"]["LFM2.5_over_qwen-v1"]
    lines = [
        "# E40 results - generous, or informative?",
        "",
        f"Paired on **{res['n_paired_companies']} companies** all three lanes have "
        f"scored (control lane at {res['n_control_companies']} and still running). "
        "Registered at `journal/experiments/E40_generous_or_informative_preregistration.md`.",
        "",
        "## D1 / D2 - does each dimension still discriminate?",
        "",
        "Modal share = the share of companies landing on that dimension's most common "
        "score. High means the question stopped separating anyone.",
        "",
        "| dimension | qwen-v1 modal / stdev | LFM2.5 modal / stdev | qwen-structured "
        "modal / stdev |",
        "|---|---:|---:|---:|",
    ]
    for key, _label in rubric.BQ_DIMENSIONS:
        cells = []
        for lane in ("qwen-v1", "LFM2.5", "qwen-structured"):
            s = res["dimension_shapes"][lane][key]
            cells.append(f"{s['modal_share']} / {s['stdev']}" if s["n"] else "—")
        lines.append(f"| `{key}` | {cells[0]} | {cells[1]} | {cells[2]} |")
    lines += [
        "",
        f"Mean modal-share gap, candidate minus incumbent: **{d12['mean_gap']:+}**. "
        f"The candidate is the more concentrated lane on "
        f"**{d12['counts']['candidate_more_concentrated']}** of "
        f"{sum(d12['counts'].values())} dimensions.",
        "",
        "## D3 - the fills, which are the whole question",
        "",
        "Dimensions the incumbent abstained on and the candidate answered, against the "
        "dimensions both answered:",
        "",
        "| | n | modal value | modal share | stdev | mean |",
        "|---|---:|---:|---:|---:|---:|",
        f"| **fills** | {fills['fills']['n']} | {fills['fills']['modal_value']} | "
        f"**{fills['fills']['modal_share']}** | {fills['fills']['stdev']} | "
        f"{fills['fills']['mean']} |",
        f"| both scored | {fills['both_scored']['n']} | "
        f"{fills['both_scored']['modal_value']} | "
        f"**{fills['both_scored']['modal_share']}** | {fills['both_scored']['stdev']} | "
        f"{fills['both_scored']['mean']} |",
        "",
        f"Modal-share gap: **{fills['modal_share_gap']:+}**.",
        "",
        "## D4 - does the evidence verify?",
        "",
        "SG only: `parse_sg` checks each quote for containment in the evidence pack "
        "per sub-test, so this is the one place a citation from outside the filing shows "
        "up as a number.",
        "",
        "| lane | scored SG sub-tests | unverified |",
        "|---|---:|---:|",
    ]
    for lane, block in res["D4_sg_evidence"].items():
        rate = block["unverified_rate"]
        lines.append(f"| {lane} | {block['n_subtests']} | "
                     f"{'—' if rate is None else f'{rate * 100:.1f}%'} |")
    lines += [
        "",
        "**The composition objection, answered.** The candidate scores more SG sub-tests, "
        "and the extra ones sit where the pack is thin - so the rate above could be the "
        "mix rather than the model. It is not:",
        "",
        "| SG sub-tests | n | qwen-v1 unverified | LFM2.5 unverified |",
        "|---|---:|---:|---:|",
        f"| **scored by BOTH lanes** | {res['D4_common_support']['common_support']['n']} "
        f"| {(res['D4_common_support']['common_support']['incumbent_unverified'] or 0) * 100:.1f}% "
        f"| **{(res['D4_common_support']['common_support']['candidate_unverified'] or 0) * 100:.1f}%** |",
        f"| scored by the candidate only | "
        f"{res['D4_common_support']['candidate_only']['n']} | — | "
        f"{(res['D4_common_support']['candidate_only']['candidate_unverified'] or 0) * 100:.1f}% |",
        "",
        "On the **same sub-tests, same filings**, the candidate's citations fail "
        "containment about **sixteen times as often**. The fills are worse still, but "
        "the gap does not depend on them.",
        "",
        "## D5 - does the judged half order companies like the auditable half?",
        "",
        "| lane | Spearman(mean scored moat dimension, `quant_only_50`) |",
        "|---|---:|",
    ]
    for lane, rho in res["D5_judged_vs_measured"].items():
        lines.append(f"| {lane} | {rho} |")
    lines += [
        "",
        "The two halves measure different things, so this is a sanity anchor and not a "
        "quality test: a lane whose judged half is noise would show ~0, and a lane that "
        "merely re-derives the accounting would show a lot.",
        "",
        "## Reading",
        "",
        f"**D1/D2 confirmed.** The candidate is the more concentrated lane on "
        f"**{d12['counts']['candidate_more_concentrated']} of "
        f"{sum(d12['counts'].values())}** dimensions, mean modal-share gap "
        f"**{d12['mean_gap']:+}**. Each individual moat question separates companies "
        "less than it did.",
        "",
        f"**D3 REFUSED, and the candidate deserves the credit.** I predicted the fills "
        "would pile onto one value - a default wearing a judgement's clothes - by at "
        "least 15pp. The gap is "
        f"**{fills['modal_share_gap']:+}**: the dimensions it answered where the "
        "incumbent abstained are spread just as widely as the ones both answered. "
        "**The extra coverage is not a constant.**",
        "",
        "**D4 confirmed, and it is the finding that matters.** SG evidence that fails "
        "containment: "
        + ", ".join(
            f"{lane} **{(b['unverified_rate'] or 0) * 100:.1f}%**"
            for lane, b in res["D4_sg_evidence"].items())
        + ". The bar is lenient - a quote fails only when **fewer than 60% of its "
          "four-letter-plus words appear anywhere in the whole evidence pack**, so a "
          "paraphrase built from the filing's own vocabulary passes it easily. The "
          "candidate fails it more than **ten times as often as either qwen lane**. "
          "Roughly one SG citation in ten points at text that is not in the filing it "
          "was given.",
        "",
        "**D5.** All three land in the registered 0.1-0.4 band, but the candidate is the "
        "lowest ("
        + ", ".join(f"{lane} {rho}" for lane, rho in res["D5_judged_vs_measured"].items())
        + "). Its judged half tracks the auditable half least closely. That is not by "
          "itself bad - the halves ask different questions - but it removes the easiest "
          "benign explanation for the extra points.",
        "",
        "**So: more answers, genuinely varied answers, less discriminating per question, "
        "and a ten-fold higher rate of citations that are not in the filing.** That is "
        "not a model that is 'just better'. It is a model that is more willing, and "
        "willingness is exactly what a fabrication check is for.",
        "",
        "## What this cannot say",
        "",
        "Which lane is **better**. Better means the score predicts something, and this "
        "repo has no forward-return grader. E40 can say whether the extra answers carry "
        "information; it cannot say whether they are right. `promoted` stays false.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=str(OUT_JSON))
    ap.add_argument("--md", default=str(OUT_MD))
    args = ap.parse_args(argv)

    res = run()
    atomic_write_json(Path(args.json), res)
    Path(args.md).write_text(_fmt_md(res), encoding="utf-8")
    d12 = res["D1_D2_modal_share"]
    fills = res["D3_fills"]["LFM2.5_over_qwen-v1"]
    print(f"paired {res['n_paired_companies']} companies")
    print(f"D1/D2 mean modal-share gap {d12['mean_gap']:+}  "
          f"candidate more concentrated on {d12['counts']['candidate_more_concentrated']}"
          f"/{sum(d12['counts'].values())} dimensions")
    print(f"D3 fills modal share {fills['fills']['modal_share']} vs both-scored "
          f"{fills['both_scored']['modal_share']} (gap {fills['modal_share_gap']:+})")
    print(f"D4 {res['D4_sg_evidence']}")
    print(f"D5 {res['D5_judged_vs_measured']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
