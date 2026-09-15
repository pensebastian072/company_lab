"""Rebuild the CSV and the workbook from the scores already on disk.

Separate from `runner.batch` on purpose: rebuilding the OUTPUT should not require
re-crawling the INPUT. The Findings sheet reads the study results, so after a study runs
the workbook is stale until this is called - and re-crawling 500 companies to pick up a
changed journal file would be absurd.

Handles the case that actually happens every week: Excel holds `company_lab_latest.xlsx`
open, so the atomic replace fails. Leaving last week's file in place silently is the worst
outcome - the numbers would be read as fresh - so the refresh goes to a `_PENDING` name
beside it and says so, loudly, on stdout and in the return code.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .. import config
from ..net import utc_today
from . import csv_export, xlsx_export

EXIT_OK = 0
EXIT_NO_SCORES = 2
EXIT_LOCKED = 3          # data is fresh but the stable name could not be replaced


def load_rows() -> list[dict]:
    import pandas as pd

    if not config.SCORES_PARQUET.exists():
        return []
    return pd.read_parquet(config.SCORES_PARQUET).to_dict("records")


def _place(dated: Path, stable: Path) -> tuple[bool, Path]:
    """Copy `dated` onto `stable`; on a lock, write a _PENDING sibling instead."""
    pending = stable.with_name(stable.stem + "_PENDING" + stable.suffix)
    try:
        shutil.copyfile(dated, stable)
        # A _PENDING file left over from a run when Excel HAD the file open is now stale
        # and sits next to a fresh one with an almost identical name. Someone will open
        # the wrong one. Remove it once the real file is current again.
        if pending.exists():
            try:
                pending.unlink()
                print(f"removed stale {pending.name}")
            except OSError:
                pass
        return True, stable
    except PermissionError:
        pending = stable.with_name(stable.stem + "_PENDING" + stable.suffix)
        shutil.copyfile(dated, pending)
        return False, pending


def refresh(*, day: str | None = None) -> int:
    rows = load_rows()
    if not rows:
        print(f"no scores at {config.SCORES_PARQUET}; run clab.runner.batch first")
        return EXIT_NO_SCORES

    day = day or utc_today()
    config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    xlsx_dated = config.EXPORT_DIR / f"company_lab_{day}.xlsx"
    csv_dated = config.EXPORT_DIR / f"scores_{day}.csv"
    xlsx_export.write_workbook_file(xlsx_dated, rows)
    csv_export.write_csv_file(csv_dated, rows)
    print(f"written: {xlsx_dated}")
    print(f"written: {csv_dated}")

    locked = []
    for dated, stable in ((xlsx_dated, config.LATEST_XLSX),
                          (csv_dated, config.LATEST_CSV)):
        ok, where = _place(dated, stable)
        if ok:
            print(f"written: {where} (latest)")
        else:
            locked.append(stable.name)
            print(f"WARNING: {stable.name} is open in another program, so it still holds "
                  f"the PREVIOUS run's numbers. Fresh copy written to {where.name}. "
                  f"Close the file and re-run to refresh it in place.")

    print(f"companies: {len(rows)}")
    return EXIT_LOCKED if locked else EXIT_OK


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--day", default=None, help="date stamp for the dated files")
    args = ap.parse_args(argv)
    return refresh(day=args.day)


if __name__ == "__main__":
    sys.exit(main())
