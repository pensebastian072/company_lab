"""E42 — paired comparison of the two Phase B scorers on identical candidate pools.

Registered in `journal/experiments/E42_lfm25_vs_qwen_paired.md` BEFORE this ran.

The two books are a controlled pair: `candidates()` is a model-independent regex sweep, so
both models were shown the SAME numbered sentences, under the same prompt, with the same
inherited fields. Only the model differs. That makes agreement and distribution
comparisons meaningful in a way they would not be if each arm had built its own evidence.

Nothing here has ground truth and nothing here invents one. Every metric is a property of
the answer distribution or an agreement measure between two readings of one page.

    .venv\\Scripts\\python.exe -m clab.research.e42_paired [--pool-sample N]

`--pool-sample` bounds P3/P5, which have to recompute the candidate pools from the cached
filings and so cost real disk on a box whose C: spinner is failing. P1/P2/P4 read only the
lane JSON and are always run over the whole overlap.
"""
from __future__ import annotations

import collections
import json
import math
import sys
from pathlib import Path

from .. import config
from ..external import schema as S

QWEN_DIR = Path(r"D:\company_lab_data\external\phase_b_local")
LFM_DIR = Path(r"D:\company_lab_data\external\phase_b_lfm25")
OUT = config.JOURNAL_DIR / "experiments" / "E42_results.json"

#: Fields that are NOT model output. `market_share_direction` is computed by
#: `revenue_share` and `industry_structural_growth` is inherited from the industry object,
#: so both arms carry identical values for them by construction. Including them would
#: manufacture agreement out of arithmetic.
INHERITED = ("market_share_direction", "industry_structural_growth")

JUDGED = tuple(f for f in S.COMPANY_ORDINALS if f not in INHERITED)


def _load(d: Path) -> dict[str, dict]:
    out = {}
    for f in d.glob("*.json"):
        if f.name.startswith("_status"):
            continue
        try:
            out[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue                      # a row written into an unclean shutdown
    return out


def _answered(row: dict, field: str) -> str | None:
    """The model's answer for one field, or None if it abstained or never ran."""
    v = str((row.get("categoricals") or {}).get(field) or S.UNKNOWN).upper()
    return None if v == S.UNKNOWN else v


def _norm_entropy(counts: collections.Counter) -> float | None:
    """Shannon entropy over answered values, normalised by the vocabulary size.

    Normalised so fields with different vocabulary sizes can be averaged. Returns None
    rather than 0.0 when nothing was answered: an unanswered field has no distribution,
    and calling that "zero information" would score an abstention as a constant.
    """
    n = sum(counts.values())
    if n == 0:
        return None
    k = len(counts)
    if k <= 1:
        return 0.0
    h = -sum((c / n) * math.log(c / n) for c in counts.values() if c)
    return h / math.log(k)


def _kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa on the companies where BOTH models answered this field."""
    n = len(pairs)
    if n == 0:
        return None
    labels = sorted({x for p in pairs for x in p})
    if len(labels) <= 1:
        return None                       # both arms constant: kappa is undefined, not 1.0
    obs = sum(1 for a, b in pairs if a == b) / n
    ca = collections.Counter(a for a, _ in pairs)
    cb = collections.Counter(b for _, b in pairs)
    exp = sum((ca[l] / n) * (cb[l] / n) for l in labels)
    if exp >= 1.0:
        return None
    return (obs - exp) / (1 - exp)


def _pool_stats(tickers: list[str], rows: dict[str, dict]) -> dict:
    """P3/P5: index-0 share, and abstention rate against pool size.

    Recomputes the candidate pools from the cached filings. The pools are deterministic
    and model-independent, so this reconstructs exactly what both models were shown.
    """
    import pandas as pd
    from ..external import local_phase_b as PB

    book = {str(r["ticker"]): r for r in
            pd.read_parquet(config.SCORES_PARQUET).to_dict("records")}
    idx0 = 0
    cited = 0
    # abstention rate bucketed by how many sentences the model was offered
    by_pool: dict[int, list[int]] = collections.defaultdict(list)
    unlocatable = 0
    for t in tickers:
        row = rows.get(t)
        meta = book.get(t)
        if not row or not meta:
            continue
        filing = (PB.load_filing(t, meta.get("cik"))
                  or PB.load_filing(t, meta.get("cik"), form="10-Q"))
        if not filing:
            continue
        pools = PB.candidates(filing.text)
        quotes = {c["field"]: c.get("quote") for c in (row.get("claims") or [])}
        for field in JUDGED:
            pool = pools.get(field) or []
            if not pool:
                continue              # no pool means no judgement was ever asked for
            answered = _answered(row, field) is not None
            by_pool[len(pool)].append(0 if answered else 1)
            q = quotes.get(field)
            if q is None:
                continue
            if q in pool:
                cited += 1
                if pool.index(q) == 0:
                    idx0 += 1
            else:
                # The filing text is re-read here, so a pool can legitimately differ from
                # the one used at scoring time if the cache was refreshed since. Counted
                # and reported rather than silently dropped.
                unlocatable += 1
    slope = None
    thin = [v for k, vs in by_pool.items() if k <= 2 for v in vs]
    thick = [v for k, vs in by_pool.items() if k >= 5 for v in vs]
    if thin and thick:
        slope = (sum(thin) / len(thin)) - (sum(thick) / len(thick))
    return {
        "claims_located_in_pool": cited,
        "claims_not_locatable": unlocatable,
        "index0_share": (idx0 / cited) if cited else None,
        "abstain_rate_thin_pool_1_2": (sum(thin) / len(thin)) if thin else None,
        "abstain_rate_thick_pool_5plus": (sum(thick) / len(thick)) if thick else None,
        "abstain_slope_thin_minus_thick": slope,
        "n_field_observations": sum(len(v) for v in by_pool.values()),
    }


def compute(pool_sample: int = 0) -> dict:
    qwen, lfm = _load(QWEN_DIR), _load(LFM_DIR)
    both = sorted(set(qwen) & set(lfm))
    res: dict = {"n_paired": len(both), "n_qwen_book": len(qwen), "n_lfm_book": len(lfm),
                 "judged_fields": list(JUDGED), "inherited_excluded": list(INHERITED)}
    if not both:
        res["error"] = "no overlap yet"
        return res

    # ---- P1: fields answered per company, paired, judged fields only
    fa = {"qwen": [], "lfm": []}
    for t in both:
        for k, src in (("qwen", qwen), ("lfm", lfm)):
            fa[k].append(sum(1 for f in JUDGED if _answered(src[t], f)))
    res["P1_fields_answered_per_company"] = {
        k: round(sum(v) / len(v), 3) for k, v in fa.items()}
    res["P1_of_possible"] = len(JUDGED)
    res["P1_lfm_minus_qwen"] = round(
        res["P1_fields_answered_per_company"]["lfm"]
        - res["P1_fields_answered_per_company"]["qwen"], 3)
    res["P1_won_by_lfm_on_n_companies"] = sum(
        1 for a, b in zip(fa["qwen"], fa["lfm"]) if b > a)
    res["P1_tied"] = sum(1 for a, b in zip(fa["qwen"], fa["lfm"]) if b == a)

    # ---- P2: per-field spread. Fill is worthless if it lands on one value.
    per_field = {}
    ents = {"qwen": [], "lfm": []}
    for f in JUDGED:
        entry = {}
        for k, src in (("qwen", qwen), ("lfm", lfm)):
            c = collections.Counter(v for t in both if (v := _answered(src[t], f)))
            e = _norm_entropy(c)
            entry[k] = {"answered": sum(c.values()), "distinct": len(c),
                        "norm_entropy": None if e is None else round(e, 4),
                        "modal_share": round(max(c.values()) / sum(c.values()), 3) if c else None,
                        "spread": dict(c.most_common())}
            if e is not None:
                ents[k].append(e)
        # ---- P4: agreement where BOTH answered
        pairs = [(a, b) for t in both
                 if (a := _answered(qwen[t], f)) and (b := _answered(lfm[t], f))]
        kap = _kappa(pairs)
        entry["both_answered"] = len(pairs)
        entry["raw_agreement"] = (round(sum(1 for a, b in pairs if a == b) / len(pairs), 3)
                                  if pairs else None)
        entry["kappa"] = None if kap is None else round(kap, 4)
        per_field[f] = entry
    res["per_field"] = per_field
    res["P2_mean_norm_entropy"] = {k: round(sum(v) / len(v), 4) if v else None
                                   for k, v in ents.items()}
    res["P2_lfm_minus_qwen"] = (
        round(res["P2_mean_norm_entropy"]["lfm"] - res["P2_mean_norm_entropy"]["qwen"], 4)
        if all(res["P2_mean_norm_entropy"].values()) else None)
    kaps = [e["kappa"] for e in per_field.values() if e["kappa"] is not None]
    res["P4_mean_kappa"] = round(sum(kaps) / len(kaps), 4) if kaps else None
    res["P4_fields_with_kappa"] = len(kaps)

    # ---- P3/P5: need the pools rebuilt from the filings, so bound the cost
    if pool_sample:
        sample = both[:pool_sample]
        res["P3_P5_sample_n"] = len(sample)
        res["P3_P5"] = {"qwen": _pool_stats(sample, qwen),
                        "lfm": _pool_stats(sample, lfm)}
    return res


def main(argv: list[str]) -> int:
    n = int(argv[argv.index("--pool-sample") + 1]) if "--pool-sample" in argv else 0
    res = compute(pool_sample=n)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    print(f"\nwritten to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
