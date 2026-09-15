"""Apply the E43 contradiction gate to an already-scored book. No model, no GPU.

The gate reads `(field, value, quote)` and every one of those is already on disk, so a book
scored before the gate existed can be repaired in place rather than re-scored. E44 measured
the effect in production: 33.3% of competitive_position claims self-contradicted before the
gate and 0.0% after.

A refuted claim becomes an ABSTENTION, never a corrected answer - the cited sentence
establishes that the model misread, not what the right reading would have been.

    .venv\\Scripts\\python.exe scripts\\apply_contradiction_gate.py <dir> [--write]

Dry-run by default. `--write` edits the rows in place and records what it did in each row's
`notes`, so a repaired row is never mistaken for one that was clean to begin with.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\<your-user>\company_lab")

from clab.external import local_phase_b as PB
from clab.external import schema as S


def run(d: Path, write: bool) -> dict:
    files = [f for f in d.glob("*.json") if not f.name.startswith("_status")]
    hits: collections.Counter = collections.Counter()
    rows_changed = 0
    examples: list[str] = []
    for f in files:
        try:
            row = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if any(str(n).startswith("contradiction gate applied") for n in row.get("notes") or []):
            continue                      # already repaired; idempotent by construction
        kept, dropped = [], []
        for c in row.get("claims") or []:
            why = PB.contradicts(c.get("field", ""), c.get("value", ""), c.get("quote") or "")
            (dropped if why else kept).append((c, why))
        if not dropped:
            continue
        rows_changed += 1
        for c, why in dropped:
            hits[c["field"]] += 1
            # the field loses its answer entirely - an abstention, not a correction
            row.setdefault("categoricals", {})[c["field"]] = S.UNKNOWN
            row.setdefault("abstained", []).append(f"{c['field']}: {why}")
            if len(examples) < 6:
                examples.append(f"{row.get('ticker')} {c['field']}={c['value']} "
                                f"<- {(c.get('quote') or '')[:110]}")
        row["claims"] = [c for c, _ in kept]
        row.setdefault("notes", []).append(
            f"contradiction gate applied: dropped {len(dropped)} claim(s)")
        if write:
            f.write_text(json.dumps(row, indent=1), encoding="utf-8")
    return {"dir": str(d), "files": len(files), "rows_changed": rows_changed,
            "claims_dropped_by_field": dict(hits), "examples": examples,
            "written": write}


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    d = Path(argv[0])
    if not d.is_dir():
        raise SystemExit(f"not a directory: {d}")
    res = run(d, write="--write" in argv)
    print(json.dumps({k: v for k, v in res.items() if k != "examples"}, indent=1))
    for e in res["examples"]:
        print("  ", e)
    if not res["written"]:
        print("\nDRY RUN - nothing written. Pass --write to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
