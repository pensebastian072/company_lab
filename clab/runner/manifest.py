"""Crawl manifest - the resume checkpoint.

Modelled on options_desk/desk/livevol_archive.py: atomic .tmp write, per-item
status, and a `stage` field that makes resume granular. A kill mid-symbol resumes
at that symbol's stage rather than re-downloading its 3.8 MB companyfacts blob,
and because every stage writes its artifact to disk first, resume is nearly free.

Checkpointing happens at the BATCH boundary, not per symbol: 50 manifest writes
instead of 500 on a spinning C: disk. The cost is losing at most 10 symbols' worth
of bookkeeping, never their data, which is already on D:.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .. import config
from ..net import atomic_write_json, read_json, utc_now_iso

VERSION = 1

STAGES = ("pending", "edgar_facts", "yf_market", "yf_prices", "normalized",
          "quant_scored", "qual_scored", "scored")

OK = "ok"
FAILED = "failed"
PARTIAL = "partial"


@dataclass
class Manifest:
    path: Any = None
    data: dict = field(default_factory=dict)

    # ------------------------------------------------------------ lifecycle
    @classmethod
    def load(cls, path=None, *, tier: str = config.DEFAULT_TIER) -> "Manifest":
        path = path or config.CRAWL_MANIFEST
        raw = read_json(path)
        if not isinstance(raw, dict) or raw.get("version") != VERSION:
            raw = {
                "version": VERSION,
                "started_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "tier": tier,
                "symbols": {},
                "batches_done": 0,
                "batches_total": 0,
            }
        raw.setdefault("symbols", {})
        return cls(path=path, data=raw)

    def save(self) -> None:
        self.data["updated_at"] = utc_now_iso()
        atomic_write_json(self.path, self.data)

    # ------------------------------------------------------------ per symbol
    def entry(self, symbol: str) -> dict:
        return self.data["symbols"].setdefault(symbol, {"status": "pending",
                                                        "stage": "pending",
                                                        "attempts": 0})

    def record_stage(self, symbol: str, stage: str, **fields) -> None:
        e = self.entry(symbol)
        e["stage"] = stage
        e.update(fields)

    def record_success(self, symbol: str, **fields) -> None:
        e = self.entry(symbol)
        e.update({"status": OK, "stage": "scored", "scored_at": utc_now_iso(),
                  "error": None, **fields})

    def record_failure(self, symbol: str, stage: str, error: str,
                       *, transient: bool = False) -> None:
        e = self.entry(symbol)
        e["attempts"] = int(e.get("attempts", 0)) + 1
        e.update({
            "status": FAILED, "stage": stage, "error": error,
            "transient": transient, "last_attempt": utc_now_iso(),
        })

    def status_of(self, symbol: str) -> str:
        return self.data["symbols"].get(symbol, {}).get("status", "pending")

    def done_symbols(self) -> set[str]:
        return {s for s, e in self.data["symbols"].items() if e.get("status") == OK}

    def failed_symbols(self) -> set[str]:
        return {s for s, e in self.data["symbols"].items() if e.get("status") == FAILED}

    def latest_accn(self, symbol: str) -> str | None:
        return self.data["symbols"].get(symbol, {}).get("latest_accn")

    def pending(self, universe: list[str], *, resume: bool = True,
               retry_failed: bool = False) -> list[str]:
        """Symbols still to do, preserving universe order (market-cap descending)."""
        if not resume:
            return list(universe)
        done = self.done_symbols()
        failed = self.failed_symbols()
        out = []
        for s in universe:
            if s in done:
                continue
            if s in failed and not retry_failed:
                # permanent failures need --retry-failed or --force to come back
                if not self.data["symbols"][s].get("transient"):
                    continue
            out.append(s)
        return out

    def summary(self) -> dict:
        syms = self.data["symbols"]
        cov = [e.get("coverage") for e in syms.values()
               if isinstance(e.get("coverage"), (int, float))]
        elapsed = [e.get("elapsed_s") for e in syms.values()
                   if isinstance(e.get("elapsed_s"), (int, float))]
        return {
            "tier": self.data.get("tier"),
            "n_symbols": len(syms),
            "n_ok": sum(1 for e in syms.values() if e.get("status") == OK),
            "n_failed": sum(1 for e in syms.values() if e.get("status") == FAILED),
            "n_pending": sum(1 for e in syms.values() if e.get("status") == "pending"),
            "median_coverage": (sorted(cov)[len(cov) // 2] if cov else None),
            "mean_elapsed_s": (sum(elapsed) / len(elapsed)) if elapsed else None,
            "batches_done": self.data.get("batches_done", 0),
            "batches_total": self.data.get("batches_total", 0),
            "started_at": self.data.get("started_at"),
            "updated_at": self.data.get("updated_at"),
        }


def chunked(seq: list, size: int) -> list[list]:
    return [seq[i:i + size] for i in range(0, len(seq), size)]
