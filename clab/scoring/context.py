"""SymbolContext - the single pure input to every scoring component.

Pure in, pure out: a component reads the context and returns a ComponentScore.
No network, no clock, no filesystem, no RNG. That is what makes every component
unit-testable from a frozen fixture and makes the same inputs produce a
byte-identical scorecard.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..fundamentals.metrics import MetricBundle
from ..fundamentals.profile import PROFILES, STANDARD, SectorProfile
from . import rubric
from .types import (SubTest, data_quality_fail, no_data, not_applicable, scored)


@dataclass
class SymbolContext:
    ticker: str
    cik: str
    name: str = ""
    as_of: str = ""
    sector: str = ""
    sub_industry: str = ""
    profile: SectorProfile = field(default_factory=lambda: PROFILES[STANDARD])
    metrics: MetricBundle = field(default_factory=MetricBundle)
    market: dict = field(default_factory=dict)     # yf_market.market_metrics()
    prices: dict = field(default_factory=dict)     # yf_prices.price_features()
    peers: dict = field(default_factory=dict)      # sub-industry medians, own-history percentiles
    qual: dict = field(default_factory=dict)       # cached LLM output, component -> payload

    # ------------------------------------------------------------ accessors
    def m(self, key: str, default=None):
        """A fundamental metric. None means absent - callers must not coerce to 0."""
        v = self.metrics.values.get(key)
        return default if v is None else v

    def mk(self, key: str, default=None):
        v = self.market.get(key)
        return default if v is None else v

    def px(self, key: str, default=None):
        v = self.prices.get(key)
        return default if v is None else v

    def prov(self, *keys: str) -> dict:
        return self.metrics.prov(*keys)


def subtest(
    ctx: SymbolContext,
    key: str,
    label: str,
    max_points: int,
    *,
    value: Any,
    points: int | None,
    inputs: dict | None = None,
    prov_keys: tuple[str, ...] = (),
    provenance: dict | None = None,
    note: str = "",
    na_reason: str = "",
) -> SubTest:
    """Build one sub-test, routing absent data through the sector profile.

    NOT_APPLICABLE is only reached when the profile nominates this sub-test AND
    the value is genuinely absent. A profile never suppresses a number we
    actually have.
    """
    prov = dict(provenance or {})
    if prov_keys:
        prov = {**ctx.prov(*prov_keys), **prov}
    inputs = dict(inputs or {})

    # A metric that failed its plausibility bounds was NULLED at source, so without this
    # it would arrive here as `value is None` and be reported as NO_DATA - thin data,
    # indistinguishable from a filer that simply does not disclose. It is not thin data;
    # it is a broken derivation, and it must say so.
    failed = getattr(ctx.metrics, "quality_failures", None) or {}
    metric = rubric.QUALITY_METRIC_FOR_SUBTEST.get(key)
    if metric and metric in failed:
        return data_quality_fail(key, label, max_points, failed[metric],
                                 inputs=inputs, provenance=prov)

    # E31: an UNDEFINED quantity is decided before the value is looked at, because for
    # these sub-tests a number being computable is exactly the problem. The soft
    # `not_applicable` route below still requires the value to be absent, which is what
    # keeps the UNH precedent intact.
    if ctx.profile.is_undefined(key):
        return not_applicable(
            key, label, max_points,
            na_reason or f"not defined for a {ctx.profile.name} filer",
            inputs=inputs, provenance=prov,
        )

    if value is None or points is None:
        status = ctx.profile.resolve_status(key, value_present=False)
        if status == "not_applicable":
            return not_applicable(
                key, label, max_points,
                na_reason or f"not meaningful for a {ctx.profile.name} filer",
                inputs=inputs, provenance=prov,
            )
        return no_data(key, label, max_points,
                       na_reason or "input unavailable",
                       inputs=inputs, provenance=prov)
    return scored(key, label, max_points, int(points),
                  inputs=inputs, provenance=prov, threshold_note=note)


def pct(v: float | None, digits: int = 1) -> str:
    return "-" if v is None else f"{v * 100:.{digits}f}%"


def num(v: float | None, digits: int = 2) -> str:
    return "-" if v is None else f"{v:,.{digits}f}"
