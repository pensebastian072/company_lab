"""One-shot repair: recompute the measured/judged ATTRIBUTION fields already on disk.

## Why this exists

`rubric.LLM_COMPONENTS` listed MG until 2026-09-01. It stopped being true at E25 (five
model-scored CEO attributes removed) and E26 (block 8 -> 2, component 15 -> 9), so MG's
9 measured points were counted as model judgement. The constants are fixed; the VALUES
WRITTEN WITH THEM are not. 1,501 scorecard JSONs and `data/scores.parquet` still carry
the old attribution, and `quant_band` is wrong for 297 of them.

## Why not just re-run the crawl

A crawl re-fetches EDGAR and yfinance, so prices move, `price_as_of` moves, `as_of`
moves, and the band hysteresis advances a day. The measured blast radius of the MG fix
would then be entangled with a day of market movement and there would be no way to
separate them. E33 already lost a measurement to exactly this: 100 band changes, of
which 85 were the calendar day rolling over.

So this recomputes and touches nothing else.

## Why it does not reimplement the arithmetic

It rebuilds `ComponentScore` / `Scorecard` objects from the stored sub-tests and reads
the canonical properties. `_subset()` in composite.py stays the ONE derivation. This
repo has already paid for a second code path for one quantity: `diluted_shares_ttm`
went through E28's outlier filter and `diluted_shares_ttm_prior` did not, and median
`dilution_yoy` read +32.5% across the whole universe as a result.

## What it will and will not change

WILL: quant_only_50, quant_normalized, quant_band, quant_coverage, qual_only_50,
      qual_available - in the scorecard JSONs and (the parquet subset of) scores.parquet.

WILL NOT: score, selection_score, band, coverage, composite_strict,
          composite_normalized, composite_ex_entry, points_earned, points_available,
          or any component's points. Asserted per company, not assumed - the run
          ABORTS on the first headline drift rather than writing a partial repair.

NOT BACKFILLED, deliberately: journal/snapshots/*.parquet and
D:\company_lab_frozen\v2_lfm25_20260901\. Hard rule 9 - snapshots cannot be
backfilled. They record what was computed at the time, wrong attribution included.

Idempotent. Running it twice changes nothing the second time.

    .venv\\Scripts\\python.exe -m clab.runner.repair_attribution --dry-run
    .venv\\Scripts\\python.exe -m clab.runner.repair_attribution --apply
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .. import config
from ..scoring import rubric
from ..scoring.composite import Scorecard
from ..scoring.types import ComponentScore, Status, SubTest

#: The only fields this repair is permitted to change.
ATTRIBUTION_FIELDS = (
    "quant_only_50", "quant_normalized", "quant_band", "quant_coverage",
    "qual_only_50", "qual_available",
)

#: Fields that must be byte-identical before and after. A change here is a bug in this
#: script, not a repair, and it stops the run.
HEADLINE_FIELDS = (
    "score", "selection_score", "band", "coverage", "composite_strict",
    "composite_normalized", "composite_ex_entry", "points_earned", "points_available",
    "applicable_points", "not_applicable_points", "no_data_points",
    "n_subtests_no_data",
)


def _subtest_from(d: dict) -> SubTest:
    """Rebuild a SubTest without re-triggering its constructor's coercion.

    `SubTest.__post_init__` forces `status = SCORED` whenever `earned is not None`,
    which is right when a scorer produces one and wrong when replaying a stored row:
    a DATA_QUALITY_FAIL row can carry a value, and letting the constructor promote it
    to SCORED would silently hand back points the original run withheld. So status is
    reapplied after construction from what is actually on disk.
    """
    st = SubTest(
        key=d.get("key", ""),
        label=d.get("label", ""),
        max_points=int(d.get("max_points", 0)),
        earned=d.get("earned"),
    )
    st.status = Status(d.get("status", Status.NO_DATA.value))
    return st


def scorecard_from_json(card: dict) -> Scorecard:
    """Reconstruct enough of a Scorecard for the aggregate properties to be exact.

    Only the component tree matters: every aggregate reads `components`, and nothing in
    the attribution path touches metrics, sources or hysteresis state.
    """
    comps: dict[str, ComponentScore] = {}
    for code, c in (card.get("components") or {}).items():
        comps[code] = ComponentScore(
            code=code,
            label=c.get("label", ""),
            max_points=int(c.get("max_points", 0)),
            subtests=[_subtest_from(s) for s in (c.get("subtests") or [])],
            note=c.get("note", ""),
        )
    return Scorecard(
        ticker=card.get("ticker", ""), cik=card.get("cik", ""),
        name=card.get("name", ""), as_of=card.get("as_of", ""),
        sector=card.get("sector", ""), sub_industry=card.get("sub_industry", ""),
        profile=card.get("profile", "STANDARD"), components=comps,
    )


def recompute(card: dict) -> tuple[dict, dict]:
    """Return (corrected_attribution, headline_check) for one stored scorecard."""
    sc = scorecard_from_json(card)
    fixed = {
        "quant_only_50": sc.quant_only_50,
        "quant_normalized": sc.quant_normalized,
        "quant_band": sc.quant_band,
        "quant_coverage": round(sc.quant_coverage, 4),
        "qual_only_50": sc.qual_only_50,
        "qual_available": sc.qual_available,
    }
    check = {
        "coverage": round(sc.coverage, 4),
        "composite_strict": sc.composite_strict,
        "composite_ex_entry": sc.composite_ex_entry,
        "points_earned": sc.points_earned,
        "points_available": sc.points_available,
        "selection_score": sc.selection_score,
    }
    return fixed, check


class HeadlineDrift(RuntimeError):
    """A field this repair must not touch came back different. Stop, do not write."""


def framework_total(card: dict) -> int:
    """Sum of the component maxima the card was WRITTEN under.

    Not the same as `rubric.TOTAL_POINTS`. A card scored before E26 carries MG at 15
    and sums to 100, and its `coverage` denominator is 100 while today's is 94. Such a
    card cannot be attribution-repaired, because its whole score is on a different
    scale - it needs a rescore, which needs a crawl.
    """
    return sum(int(c.get("max_points", 0)) for c in (card.get("components") or {}).values())


def is_current_framework(card: dict) -> bool:
    return framework_total(card) == rubric.TOTAL_POINTS


def _verify_headline(card: dict, check: dict) -> None:
    for key, got in check.items():
        had = card.get(key)
        if had is None:
            continue
        if isinstance(had, float) or isinstance(got, float):
            if abs(float(had) - float(got)) > 1e-6:
                raise HeadlineDrift(
                    f"{card.get('ticker')}: {key} {had} -> {got}. This repair may only "
                    f"change attribution. Nothing written.")
        elif had != got:
            raise HeadlineDrift(
                f"{card.get('ticker')}: {key} {had!r} -> {got!r}. This repair may only "
                f"change attribution. Nothing written.")


def _atomic_write_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=True), encoding="utf-8")
    tmp.replace(path)


def repair_scorecards(apply: bool = False) -> dict:
    """Walk data/scorecards, recompute attribution, report and optionally write."""
    paths = sorted(config.SCORECARD_DIR.glob("*.json"))
    changed: list[dict] = []
    skipped: list[dict] = []
    band_moves: dict[tuple[str, str], int] = {}
    for p in paths:
        card = json.loads(p.read_text(encoding="utf-8"))
        # A card written under a different framework is not repairable here. Rewriting
        # only its attribution would leave a 100-point coverage denominator beside a
        # 94-point one and hide the real problem, which is that it was never rescored.
        if not is_current_framework(card):
            skipped.append({"ticker": card.get("ticker"),
                            "framework_total": framework_total(card),
                            "as_of": card.get("as_of")})
            continue
        fixed, check = recompute(card)
        _verify_headline(card, check)

        diff = {k: (card.get(k), v) for k, v in fixed.items() if card.get(k) != v}
        if not diff:
            continue
        row = {"ticker": card.get("ticker"), "path": p.name, "diff": diff}
        changed.append(row)
        if "quant_band" in diff:
            band_moves[(diff["quant_band"][0], diff["quant_band"][1])] = \
                band_moves.get((diff["quant_band"][0], diff["quant_band"][1]), 0) + 1
        if apply:
            card.update(fixed)
            _atomic_write_json(p, card)
    return {"scanned": len(paths), "changed": len(changed), "skipped": skipped,
            "band_moves": band_moves, "rows": changed}


def repair_parquet(apply: bool = False) -> dict:
    """Rewrite the attribution columns in scores.parquet from the repaired scorecards.

    The parquet is a projection of the scorecards, so it is rebuilt FROM them rather
    than recomputed independently - otherwise the two could disagree, which is the
    exact failure mode that froze scores.parquet at 1,139 rows while the CSV had 1,497.
    """
    import pandas as pd

    if not config.SCORES_PARQUET.exists():
        return {"skipped": "no scores.parquet"}

    df = pd.read_parquet(config.SCORES_PARQUET)
    by_ticker: dict[str, dict] = {}
    for p in sorted(config.SCORECARD_DIR.glob("*.json")):
        card = json.loads(p.read_text(encoding="utf-8"))
        if not is_current_framework(card):
            continue                      # left exactly as it is; see repair_scorecards
        fixed, check = recompute(card)
        _verify_headline(card, check)
        if card.get("ticker"):
            by_ticker[card["ticker"]] = fixed

    cols = [c for c in ATTRIBUTION_FIELDS if c in df.columns]
    before = {c: df[c].copy() for c in cols}
    missing = 0
    for c in cols:
        vals = []
        for t, old in zip(df["ticker"], df[c]):
            fixed = by_ticker.get(t)
            if fixed is None:
                missing += 1
                vals.append(old)
            else:
                vals.append(fixed[c])
        df[c] = vals

    n_changed = {c: int((before[c].fillna("~") != df[c].fillna("~")).sum())
                 for c in cols}
    if apply:
        tmp = config.SCORES_PARQUET.with_suffix(".parquet.tmp")
        df.to_parquet(tmp, index=False)
        tmp.replace(config.SCORES_PARQUET)
    return {"rows": len(df), "columns": cols, "changed_per_column": n_changed,
            "rows_without_a_scorecard": missing // max(len(cols), 1)}


def find_ghosts() -> list[dict]:
    """CIKs carrying more than one live scorecard, i.e. a ticker change left an orphan.

    The book is deduped by CIK by construction, so this must be empty. It was not:
    CIK 0000906107 held both `0000906107_EQR.json` (as_of 2026-08-17, the 100-point
    framework, `score` NaN) and `0000906107_VMRK.json` (as_of 2026-08-29, current). The
    company re-tickered EQR -> VMRK, the new file was created beside the old one, and
    scores.parquet then carried the same company TWICE - 1,501 rows over 1,500 CIKs.

    Confirmed against the live index before acting: VMRK appears there with CIK
    0000906107, so this is a rename and not two companies.

    An ex-constituent with ONE card is not a ghost. AVB left the index with no rename
    and keeps its single card - dropping ex-constituents is precisely the survivorship
    bias E05 exists to measure.
    """
    groups: dict[str, list[dict]] = {}
    for path in sorted(config.SCORECARD_DIR.glob("*.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        cik = card.get("cik")
        if not cik:
            continue
        groups.setdefault(cik, []).append({
            "path": path, "ticker": card.get("ticker"),
            "as_of": card.get("as_of") or "", "framework": framework_total(card),
            "current": is_current_framework(card),
        })
    out = []
    for cik, cards in groups.items():
        if len(cards) < 2:
            continue
        # Keep the newest card on the current framework; if none is, keep the newest
        # outright rather than quarantining every copy of a company.
        current = [c for c in cards if c["current"]] or cards
        keep = max(current, key=lambda c: c["as_of"])
        out.append({"cik": cik, "keep": keep,
                    "drop": [c for c in cards if c["path"] != keep["path"]]})
    return out


def prune_ghosts(apply: bool = False) -> dict:
    """Quarantine orphaned duplicate scorecards and drop their parquet rows.

    Quarantined, never deleted: moved to data/scorecards/ghosts/ so the decision is
    reversible. Deleting a scored company on an inference is not a repair.
    """
    import pandas as pd

    ghosts = find_ghosts()
    dropped = [c["ticker"] for g in ghosts for c in g["drop"]]
    rows = "unchanged"
    if apply and ghosts:
        quarantine = config.SCORECARD_DIR / "ghosts"
        quarantine.mkdir(parents=True, exist_ok=True)
        for g in ghosts:
            for c in g["drop"]:
                c["path"].replace(quarantine / c["path"].name)
        if config.SCORES_PARQUET.exists() and dropped:
            df = pd.read_parquet(config.SCORES_PARQUET)
            before = len(df)
            df = df[~df["ticker"].isin(dropped)].reset_index(drop=True)
            tmp = config.SCORES_PARQUET.with_suffix(".parquet.tmp")
            df.to_parquet(tmp, index=False)
            tmp.replace(config.SCORES_PARQUET)
            rows = f"{before} -> {len(df)}"
    return {"ghosts": ghosts, "dropped": dropped, "parquet_rows": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true",
                    help="write the repair (default is a dry run)")
    ap.add_argument("--dry-run", action="store_true", help="explicit no-op default")
    ap.add_argument("--prune-ghosts", action="store_true",
                    help="also quarantine duplicate scorecards left by a ticker change")
    args = ap.parse_args(argv)
    apply = bool(args.apply) and not args.dry_run

    print(f"framework: judged {rubric.JUDGED_COMPONENTS} = {rubric.JUDGED_POINTS}, "
          f"measured {rubric.MEASURED_COMPONENTS} = {rubric.MEASURED_POINTS}")
    print(f"mode: {'APPLY' if apply else 'DRY RUN'}\n")

    try:
        cards = repair_scorecards(apply=apply)
    except HeadlineDrift as exc:
        print(f"ABORTED: {exc}")
        return 2

    print(f"scorecards scanned : {cards['scanned']}")
    print(f"scorecards changed : {cards['changed']}")
    if cards["skipped"]:
        print(f"SKIPPED (wrong framework, need a RESCORE not a repair): "
              f"{len(cards['skipped'])}")
        for row in cards["skipped"]:
            print(f"    {row['ticker']:<6} {row['framework_total']} points  "
                  f"as_of {row['as_of']}")
    if cards["band_moves"]:
        print("quant_band moves   :")
        for (a, b), n in sorted(cards["band_moves"].items(), key=lambda kv: -kv[1]):
            print(f"    {a:<18} -> {b:<18} {n}")

    try:
        pq = repair_parquet(apply=apply)
    except HeadlineDrift as exc:
        print(f"ABORTED on parquet: {exc}")
        return 2
    print(f"\nparquet            : {pq}")

    if args.prune_ghosts:
        g = prune_ghosts(apply=apply)
        print("\nghost scorecards (one CIK, several live cards):")
        if not g["ghosts"]:
            print("    none - the book's dedupe-by-CIK invariant holds")
        for row in g["ghosts"]:
            k = row["keep"]
            print(f"    CIK {row['cik']}  KEEP {k['ticker']:<6} "
                  f"({k['as_of'][:10]}, {k['framework']}pt)")
            for c in row["drop"]:
                print(f"                       DROP {c['ticker']:<6} "
                      f"({c['as_of'][:10]}, {c['framework']}pt)")
        print(f"    parquet rows: {g['parquet_rows']}")

    if not apply:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
    else:
        print("\nWritten. Snapshots and the frozen v2 book are NOT backfilled "
              "(hard rule 9).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
