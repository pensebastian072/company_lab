"""One version-selection rule for industry objects and every export surface."""
from __future__ import annotations

from collections.abc import Iterable, Mapping


def version_key(version) -> tuple[str, int]:
    """Sortable key for versions such as ``2026-09-02`` and ``2026-09-02.10``."""
    date, _, revision = str(version or "").partition(".")
    try:
        return date, int(revision) if revision else 0
    except ValueError:
        return date, 0


def active_industry_rows(rows: Iterable[Mapping], *,
                         include_superseded: bool = False) -> list[dict]:
    """Return each industry's newest parsed version, omitting retired objects.

    Retirement is decided only after choosing the newest version. Otherwise a retired
    newest row would make an older active row appear current again.
    """
    latest_by_industry: dict[str, dict] = {}
    for source in rows:
        row = dict(source)
        industry_id = str(row.get("industry_id") or "")
        current = latest_by_industry.get(industry_id)
        if current is None or version_key(row.get("version")) > version_key(
                current.get("version")):
            latest_by_industry[industry_id] = row

    selected = []
    for industry_id in sorted(latest_by_industry):
        row = latest_by_industry[industry_id]
        retired = str(row.get("status") or "").upper() == "SUPERSEDED"
        if include_superseded or not retired:
            selected.append(row)
    return selected
