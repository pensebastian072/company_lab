"""One-off: re-download the whole price store split-adjusted, then audit it.

Kept in the repo rather than run as an inline snippet because it is the remedy for a
real defect (the store was built with auto_adjust=False) and may be needed again if
the store is ever rebuilt from an older revision.

  .venv\\Scripts\\python.exe scripts\\readjust_prices.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clab.net import trust_windows_certs          # noqa: E402
from clab.runner import batch                     # noqa: E402
from clab.sources import yf_prices                # noqa: E402


def main() -> int:
    trust_windows_certs()
    rows = batch.load_universe("sp500")
    syms = [r["ticker"] for r in rows] + ["SPY"]
    print(f"re-downloading {len(syms)} symbols with auto_adjust=True", flush=True)
    yf_prices.fetch_prices(syms, force=True, group_size=10)

    print("auditing the store for implausible single-day moves", flush=True)
    bad = yf_prices.audit_store()
    print(f"symbols still flagged: {len(bad)}", flush=True)
    for b in bad[:25]:
        print(f"  {b['ticker']:6s} worst {b['worst_day']:+.1%} "
              f"best {b['best_day']:+.1%}  ({b['n_suspect_days']} days)", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
