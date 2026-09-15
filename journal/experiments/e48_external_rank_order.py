"""Execute the pre-registered E48 rank-order and neutral-peer diagnostics."""
from __future__ import annotations

import bisect
import hashlib
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

from clab import config
from clab.external import contradiction as C
from clab.external import gates as G
from clab.external import score as SC
from clab.external.store import ExternalStore


CUTOFF = "2026-09-04"
EXPECTED = 71
HERE = Path(__file__).resolve().parent
JSON_OUT = HERE / "E48_external_rank_order_results.json"
MD_OUT = HERE / "E48_external_rank_order_results.md"

LOCAL_KEYS = ("framework_band", "financial_engine", "survivability", "framework_coverage")
EVIDENCE_KEYS = (
    "external_coverage",
    "external_confidence",
    "research_depth",
    "core_fields_known",
)


def ranked(values: dict[str, float]) -> dict[str, int]:
    ordered = sorted(values, key=lambda ticker: (-values[ticker], ticker))
    return {ticker: idx for idx, ticker in enumerate(ordered, 1)}


def pearson(x: list[int], y: list[int]) -> float:
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y))
    denominator = math.sqrt(
        sum((a - x_mean) ** 2 for a in x) * sum((b - y_mean) ** 2 for b in y)
    )
    return numerator / denominator


def kendall_tau_b(x: list[int], y: list[int]) -> float:
    concordant = discordant = ties_x = ties_y = 0
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif dx * dy > 0:
                concordant += 1
            else:
                discordant += 1
    denominator = math.sqrt(
        (concordant + discordant + ties_x) * (concordant + discordant + ties_y)
    )
    return (concordant - discordant) / denominator


def transition(name: str, before: dict[str, int], after: dict[str, int]) -> dict:
    tickers = sorted(before)
    x = [before[t] for t in tickers]
    y = [after[t] for t in tickers]
    # Ranks are unique after the pre-registered alphabetical tie-break, so
    # Spearman is Pearson over the rank vectors. Kendall is tau-b for completeness.
    rho = pearson(x, y)
    tau = kendall_tau_b(x, y)
    moves = [abs(before[t] - after[t]) for t in tickers]
    ordered_moves = sorted(moves)
    p90_idx = max(0, math.ceil(0.90 * len(ordered_moves)) - 1)
    top_n = math.ceil(0.10 * len(tickers))
    top_before = {t for t in tickers if before[t] <= top_n}
    top_after = {t for t in tickers if after[t] <= top_n}
    overlap = len(top_before & top_after) / top_n
    median = float(pd.Series(moves).median())
    order_changing = rho < 0.90 or (
        median >= 0.05 * len(tickers) and overlap < 0.80
    )
    material = []
    for ticker in tickers:
        delta = before[ticker] - after[ticker]
        if abs(delta) >= 5:
            material.append(
                {
                    "ticker": ticker,
                    "from_rank": before[ticker],
                    "to_rank": after[ticker],
                    "places_up": delta,
                }
            )
    material.sort(key=lambda row: (-abs(row["places_up"]), row["ticker"]))
    return {
        "name": name,
        "spearman_rho": round(rho, 4),
        "kendall_tau": round(tau, 4),
        "median_absolute_rank_move": median,
        "p90_absolute_rank_move": ordered_moves[p90_idx],
        "top_decile_n": top_n,
        "top_decile_overlap": round(overlap, 4),
        "moves_at_least_5": material,
        "decision": "ORDER_CHANGING" if order_changing else "ORDER_PRESERVING",
    }


def latest_records(store: ExternalStore) -> tuple[list[dict], list[str]]:
    with store.connect() as con:
        rows = con.execute(
            "SELECT ticker, research_version FROM company_external "
            "WHERE sector_id = 'energy' AND research_depth = 3"
        ).fetchall()
    eligible: dict[str, str] = {}
    for ticker, version in rows:
        if str(version)[:10] <= CUTOFF and (
            ticker not in eligible or str(version) > eligible[ticker]
        ):
            eligible[ticker] = str(version)
    records = [store.company(ticker, version) for ticker, version in sorted(eligible.items())]
    records = [record for record in records if record is not None]

    score_df = pd.read_parquet(config.SCORES_PARQUET)
    energy = score_df[score_df["sector"].str.lower() == "energy"]
    missing = sorted(set(energy["ticker"]) - {record["ticker"] for record in records})
    return records, missing


def run_rank_test(store: ExternalStore, score_df: pd.DataFrame) -> dict:
    records, missing = latest_records(store)
    complete = len(records) == EXPECTED and not missing
    if not complete:
        return {
            "status": "BLOCKED_PRIMARY",
            "expected": EXPECTED,
            "records": len(records),
            "missing": missing,
        }

    locals_by_ticker = score_df.set_index("ticker")
    peers_by_industry: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        peers_by_industry[record.get("industry_id") or ""].append(record)

    detail: dict[str, dict] = {}
    a_values: dict[str, float] = {}
    b_values: dict[str, float] = {}
    moat_values: dict[str, float] = {}
    c_values: dict[str, float] = {}

    for record in records:
        ticker = record["ticker"]
        local = locals_by_ticker.loc[ticker].to_dict()
        local["ticker"] = ticker
        claims = [
            claim
            for claim in store.claims_for(ticker)
            if claim.get("request_id") == record.get("request_id")
        ]
        scored = SC.score_company(record, claims, today=date.fromisoformat(CUTOFF))
        confidence, confidence_detail = SC.confidence(
            record,
            claims,
            coverage=scored["coverage"],
            today=date.fromisoformat(CUTOFF),
        )
        scored["external_confidence"] = confidence
        peers = [
            peer
            for peer in peers_by_industry[record.get("industry_id") or ""]
            if peer["ticker"] != ticker
        ]
        flags = C.flags_for(local, record, claims, peers=peers)
        parts = G.criteria(local, record, scored)
        a_earned = sum(parts[key]["earned"] for key in LOCAL_KEYS)
        a_max = sum(parts[key]["max"] for key in LOCAL_KEYS)
        b_keys = LOCAL_KEYS + EVIDENCE_KEYS
        b_earned = sum(parts[key]["earned"] for key in b_keys)
        b_max = sum(parts[key]["max"] for key in b_keys)
        evaluated = G.evaluate(local, record, scored, flags)

        a_values[ticker] = 100 * a_earned / a_max
        b_values[ticker] = 100 * b_earned / b_max
        moat_values[ticker] = evaluated["criteria_earned"]
        c_values[ticker] = evaluated["conviction_score"]
        detail[ticker] = {
            "research_version": record["research_version"],
            "request_id": record.get("request_id"),
            "industry_id": record.get("industry_id"),
            "A_local": round(a_values[ticker], 4),
            "B_evidence": round(b_values[ticker], 4),
            "C_moat_no_flags": round(moat_values[ticker], 4),
            "C_full": round(c_values[ticker], 4),
            "moat_trajectory": record.get("moat_trajectory"),
            "moat_trajectory_points": parts["moat_trajectory"]["earned"],
            "flags": flags,
            "flag_penalty": evaluated["flag_penalty"],
            "external_coverage": scored["coverage"],
            "external_confidence": confidence,
            "confidence_detail": confidence_detail,
        }

    ranks = {
        "A_local": ranked(a_values),
        "B_evidence": ranked(b_values),
        "C_moat_no_flags": ranked(moat_values),
        "C_full": ranked(c_values),
    }
    for ticker, row in detail.items():
        row["ranks"] = {name: values[ticker] for name, values in ranks.items()}

    transitions = {
        "A_to_B": transition("A_local to B_evidence", ranks["A_local"], ranks["B_evidence"]),
        "B_to_C": transition("B_evidence to C_full", ranks["B_evidence"], ranks["C_full"]),
        "moat_only": transition(
            "B_evidence to C_moat_no_flags", ranks["B_evidence"], ranks["C_moat_no_flags"]
        ),
        "flags_only": transition(
            "C_moat_no_flags to C_full", ranks["C_moat_no_flags"], ranks["C_full"]
        ),
    }
    ab = transitions["A_to_B"]["decision"] == "ORDER_CHANGING"
    bc = transitions["B_to_C"]["decision"] == "ORDER_CHANGING"
    if bc:
        headline = "SUBSTANTIVE_ORDER_CHANGE"
    elif ab:
        headline = "EVIDENCE_AVAILABILITY_ORDER_CHANGE"
    else:
        headline = "DOCUMENTS_WITHOUT_MATERIAL_REORDERING"

    return {
        "status": "COMPLETE_PRIMARY",
        "universe": len(records),
        "cutoff": CUTOFF,
        "scores_snapshot": str(config.SCORES_PARQUET),
        "headline": headline,
        "transitions": transitions,
        "companies": detail,
    }


def pctile(values: list[float], value: float) -> float:
    return round(100 * bisect.bisect_right(sorted(values), value) / len(values), 1)


def run_neutral_test(store: ExternalStore, score_df: pd.DataFrame) -> dict:
    utilities = score_df[score_df["sector"].str.lower() == "utilities"].copy()
    records = store.companies("2026-09-05+E47-utilities")
    industries = {record["ticker"]: record.get("industry_id") for record in records}
    utilities = utilities[utilities["ticker"].isin(industries)].copy()
    utilities["industry_id"] = utilities["ticker"].map(industries)

    by_industry = {
        key: group for key, group in utilities.groupby("industry_id", dropna=False)
    }
    by_sub = {key: group for key, group in utilities.groupby("sub_industry", dropna=False)}
    sector_values = [float(value) for value in utilities["composite_strict"].dropna()]

    rows = []
    for _, row in utilities.sort_values("ticker").iterrows():
        ticker = row["ticker"]
        value = float(row["composite_strict"])
        industry = row["industry_id"]
        sub = row["sub_industry"]
        industry_group = by_industry[industry]
        sub_group = by_sub[sub]
        if len(industry_group) >= 4:
            basis = "industry_id"
            key = str(industry)
            group = industry_group
        elif len(sub_group) >= 5:
            basis = "sub_industry"
            key = str(sub)
            group = sub_group
        else:
            basis = "sector"
            key = "Utilities"
            group = utilities
        new_values = [float(v) for v in group["composite_strict"].dropna()]
        old_basis = row.get("sector_neutral_basis")
        old_key = str(sub) if old_basis == "sub_industry" else "Utilities"
        old_score = row.get("sector_neutral_score")
        item = {
            "ticker": ticker,
            "composite_strict": value,
            "industry_id": industry,
            "old_basis": old_basis,
            "old_key": old_key,
            "old_n": int(row.get("sector_neutral_n") or 0),
            "old_percentile": None if pd.isna(old_score) else float(old_score),
            "new_basis": basis,
            "new_key": key,
            "new_n": len(new_values),
            "new_percentile": pctile(new_values, value),
        }
        item["percentile_change"] = (
            None
            if item["old_percentile"] is None
            else round(item["new_percentile"] - item["old_percentile"], 1)
        )
        item["peer_key_changed"] = (
            item["old_basis"] != item["new_basis"] or item["old_key"] != item["new_key"]
        )
        rows.append(item)

    changed = [row for row in rows if row["peer_key_changed"]]
    return {
        "decision": "ADOPT_INDUSTRY_ID_WITH_MINIMUM_SIZE_FALLBACK",
        "implemented_in_production": False,
        "score_column": "composite_strict",
        "hierarchy": [
            "industry_id if n >= 4",
            "sub_industry if n >= 5",
            "sector otherwise",
        ],
        "utilities_companies": len(rows),
        "peer_key_changes": len(changed),
        "rows": rows,
    }


def fmt_transition(item: dict) -> str:
    return (
        f"| {item['name']} | {item['spearman_rho']:.4f} | {item['kendall_tau']:.4f} | "
        f"{item['median_absolute_rank_move']:.1f} | {item['p90_absolute_rank_move']} | "
        f"{item['top_decile_overlap']:.1%} | {item['decision']} |"
    )


def write_markdown(result: dict) -> None:
    rank = result["rank_order"]
    neutral = result["neutral_basis"]
    lines = [
        "# E48 external rank-order result",
        "",
        "Pre-registered before the Energy deltas were computed. This is a rank-behavior diagnostic, not a return test.",
        "",
        f"Primary Energy universe: **{rank.get('universe', rank.get('records'))} of {EXPECTED}**. Status: **{rank['status']}**.",
        "",
    ]
    if rank["status"] == "COMPLETE_PRIMARY":
        lines += [
            f"Headline: **{rank['headline']}**.",
            "",
            "| transition | Spearman | Kendall | median move | p90 move | top-decile overlap | result |",
            "|---|---:|---:|---:|---:|---:|---|",
            fmt_transition(rank["transitions"]["A_to_B"]),
            fmt_transition(rank["transitions"]["B_to_C"]),
            fmt_transition(rank["transitions"]["moat_only"]),
            fmt_transition(rank["transitions"]["flags_only"]),
            "",
        ]
        for key, label in (("A_to_B", "Evidence-driven moves"), ("moat_only", "Moat-trajectory moves"), ("flags_only", "Flag-driven moves")):
            moves = rank["transitions"][key]["moves_at_least_5"]
            lines += [f"## {label}", ""]
            if not moves:
                lines.append("No moves of at least five places.")
            else:
                lines += ["| ticker | from | to | places up |", "|---|---:|---:|---:|"]
                for move in moves:
                    lines.append(
                        f"| {move['ticker']} | {move['from_rank']} | {move['to_rank']} | {move['places_up']:+d} |"
                    )
            lines.append("")

    lines += [
        "## Neutral peer basis",
        "",
        "Decision: **use `industry_id` when n >= 4, then GICS `sub_industry` when n >= 5, then sector**.",
        "This is not yet implemented in production. It changes the economic comparison set but does not establish better forward returns.",
        "",
        f"In Utilities, {neutral['peer_key_changes']} of {neutral['utilities_companies']} companies change peer key under that hierarchy.",
        "The full ticker-level old/new mapping is in the JSON result.",
        "",
        "## Guardrail",
        "",
        "`promoted` remains false. No portfolio or predictive claim follows from this diagnostic.",
        "",
    ]
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    store = ExternalStore()
    score_df = pd.read_parquet(config.SCORES_PARQUET)
    result = {
        "experiment": "E48_external_rank_order",
        "preregistered": True,
        "as_of": "2026-09-05",
        "promoted": False,
        "scores_snapshot_sha256": hashlib.sha256(Path(config.SCORES_PARQUET).read_bytes()).hexdigest(),
        "rank_order": run_rank_test(store, score_df),
        "neutral_basis": run_neutral_test(store, score_df),
    }
    JSON_OUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(result)
    print(json.dumps({
        "json": str(JSON_OUT),
        "markdown": str(MD_OUT),
        "rank_status": result["rank_order"]["status"],
        "headline": result["rank_order"].get("headline"),
        "neutral_changes": result["neutral_basis"]["peer_key_changes"],
    }, indent=2))


if __name__ == "__main__":
    main()
