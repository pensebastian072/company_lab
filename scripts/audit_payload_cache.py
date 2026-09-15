"""Scan a qual payload cache for files an unclean shutdown left unflushed.

Windows sizes a file on NTFS before it flushes the bytes, so a payload written at
the moment of a crash is a run of NUL, not a truncation. It still satisfies the
resume check, so the company is silently skipped. Run this after ANY hard stop.

It also checks COMPONENT COMPLETENESS. A company is resumed on "has 3 payloads and an
SG", so a company holding 3 files where one is degraded would be counted done and enter
the study with a missing component. A company holding fewer than 3 is safe - it is simply
re-scored - which is what happens when a kill lands mid-company.

  python scripts/audit_payload_cache.py <cache_dir> [--quarantine <dir>]
"""
import argparse, collections, json, pathlib, shutil, sys


def classify(path: pathlib.Path) -> str | None:
    raw = path.read_bytes()
    if not raw:
        return "empty"
    if raw[0] == 0:
        return "nul"
    if raw.count(0):
        return "embedded_nul"
    try:
        json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return f"unparseable: {type(exc).__name__}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cache_dir", type=pathlib.Path)
    ap.add_argument("--quarantine", type=pathlib.Path, default=None)
    args = ap.parse_args()

    files = sorted(args.cache_dir.glob("*.json"))
    bad = []
    by_cik = collections.defaultdict(dict)
    for f in files:
        verdict = classify(f)
        if verdict:
            bad.append((f, verdict))
            continue
        parts = f.name.split("_")
        if len(parts) >= 2:
            payload = json.loads(f.read_text(encoding="utf-8"))
            by_cik[parts[0]][parts[1]] = payload
            if payload.get("parse_ok") is False:
                bad.append((f, f"parse_ok=False ticker={payload.get('ticker')}"))

    complete = {c: v for c, v in by_cik.items() if len(v) >= 3}
    partial = {c: v for c, v in by_cik.items() if len(v) < 3}
    no_sg = [c for c, v in complete.items() if "SG" not in v]

    print(f"{len(files)} payloads scanned in {args.cache_dir}")
    print(f"  {len(complete)} companies complete, {len(partial)} partial (will be re-scored)")
    for c, v in sorted(partial.items()):
        ticker = next((x.get("ticker") for x in v.values() if x.get("ticker")), "?")
        print(f"    {ticker} cik={c} has={sorted(v)}")
    if no_sg:
        print(f"  DANGER: {len(no_sg)} companies have 3 payloads but no SG - resume would")
        print("    count these done with a component missing:", ", ".join(sorted(no_sg)))
    for f, verdict in bad:
        print(f"  CORRUPT  {f.name}  ({f.stat().st_size} bytes, {verdict})")
    if not bad and not no_sg:
        print("  clean - no unflushed, unparseable, or silently incomplete payload")
        return 0
    if not bad:
        return 1

    if args.quarantine:
        args.quarantine.mkdir(parents=True, exist_ok=True)
        for f, _ in bad:
            shutil.move(str(f), str(args.quarantine / f.name))
        print(f"quarantined {len(bad)} to {args.quarantine}")
        print("the next resume regenerates them normally")
    else:
        print("re-run with --quarantine <dir> to move these aside")
    return 1


if __name__ == "__main__":
    sys.exit(main())
