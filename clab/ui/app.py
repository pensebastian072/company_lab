"""company_lab dashboard - Flask, 127.0.0.1:8100 ONLY.

Strictly a reader of published artifacts. No route fetches data, triggers a crawl,
or calls an LLM; /api/refresh only drops the memo. clab.qual is deliberately never
imported here and a test asserts that.

Run:
  .venv\\Scripts\\python.exe -m clab.ui.app
  .venv\\Scripts\\python.exe -m clab.ui.app --port 8100
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from flask import Flask, jsonify, make_response, render_template, request
except ImportError:  # pragma: no cover
    print("flask is not installed: .venv\\Scripts\\python.exe -m pip install "
          "--use-feature=truststore flask")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from clab import config  # noqa: E402
from clab.export import csv_export, xlsx_export  # noqa: E402
from clab.net import read_json  # noqa: E402
from clab.scoring import rubric  # noqa: E402
from clab.ui import state as state_mod  # noqa: E402

UI_DIR = Path(__file__).resolve().parent
app = Flask(__name__,
            template_folder=str(UI_DIR / "templates"),
            static_folder=str(UI_DIR / "static"))

TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,10}$")


@app.context_processor
def _inject():
    return {
        "ADVISORY": config.ADVISORY_BANNER,
        # F4: the dashboard states the horizon it should be read on. Presentation only -
        # it changes no score. Defined once in the rubric so the UI, the workbook and any
        # future validation cannot disagree about it.
        "HORIZON_LABEL": rubric.HORIZON_LABEL,
        "HORIZON_NOTE": rubric.HORIZON_NOTE,
        "UI_PORT": config.UI_PORT,
        # E33: the framework's own arithmetic, so a label can never restate a total the
        # code has already changed. It went 100 -> 94 at E26 and the templates went on
        # saying "/100 full" and "/95 excluding Entry" - the second was wrong twice over,
        # since ex-entry is TOTAL minus EN and EN itself dropped 5 -> 2.
        "TOTAL_POINTS": rubric.TOTAL_POINTS,
        "JUDGED_POINTS": rubric.JUDGED_POINTS,
        "MEASURED_POINTS": rubric.MEASURED_POINTS,
        "EX_ENTRY_POINTS": rubric.TOTAL_POINTS - rubric.COMPONENTS["EN"][1],
        "COMPONENTS": [
            {"code": c, "label": rubric.COMPONENTS[c][0],
             "max": rubric.COMPONENTS[c][1],
             "is_llm": c in rubric.JUDGED_COMPONENTS}
            for c in rubric.COMPONENT_ORDER
        ],
    }


# ------------------------------------------------------------------ pages
@app.route("/")
def page_rank():
    return render_template("dashboard.html", page="rank")


@app.route("/c/<ticker>")
def page_company(ticker: str):
    if not TICKER_RE.match(ticker or ""):
        return render_template("company.html", page="company", ticker="", missing=True), 200
    card = state_mod.scorecard_for(ticker)
    return render_template("company.html", page="company", ticker=ticker.upper(),
                           missing=card is None)


@app.route("/health")
def page_health():
    return render_template("health.html", page="health")


# ------------------------------------------------------------------ api
@app.route("/api/state")
def api_state():
    return jsonify(state_mod.cached_state())


@app.route("/api/refresh")
def api_refresh():
    return jsonify(state_mod.cached_state(bust=True))


@app.route("/api/company/<ticker>")
def api_company(ticker: str):
    if not TICKER_RE.match(ticker or ""):
        return jsonify({"ok": False, "reason": "bad ticker"}), 200
    card = state_mod.scorecard_for(ticker)
    if card is None:
        return jsonify({"ok": False, "reason": f"{ticker.upper()} has not been scored yet"}), 200
    return jsonify({"ok": True, "scorecard": card,
                    "thesis": state_mod.thesis_for(ticker),
                    "advisory": config.ADVISORY_BANNER})


@app.route("/api/thesis/<ticker>")
def api_thesis(ticker: str):
    if not TICKER_RE.match(ticker or ""):
        return jsonify({"ok": False, "reason": "bad ticker"}), 200
    t = state_mod.thesis_for(ticker)
    return jsonify({"ok": t is not None, "thesis": t,
                    "reason": None if t else "no thesis written yet"})


@app.route("/api/health")
def api_health():
    flag = read_json(config.STATE_FLAG) or {}
    st = state_mod.cached_state()
    probes = sorted(config.PROBE_DIR.glob("probe_*.json"))
    manifest = read_json(config.CRAWL_MANIFEST) or {}
    syms = manifest.get("symbols") or {}
    return jsonify({
        "ok": True,
        "advisory": config.ADVISORY_BANNER,
        "flag": flag,
        "stale": _is_stale(flag.get("as_of")),
        "summary": st.get("summary", {}),
        "n_rows": st.get("n", 0),
        "reason": st.get("reason"),
        "manifest": {
            "tier": manifest.get("tier"),
            "updated_at": manifest.get("updated_at"),
            "batches_done": manifest.get("batches_done"),
            "batches_total": manifest.get("batches_total"),
            "n_ok": sum(1 for e in syms.values() if e.get("status") == "ok"),
            "n_failed": sum(1 for e in syms.values() if e.get("status") == "failed"),
            "failures": {s: e.get("error") for s, e in syms.items()
                         if e.get("status") == "failed"},
        },
        "latest_probe": (read_json(probes[-1]) or {}).get("projection") if probes else None,
        "freshness": (read_json(config.FRESHNESS_FILE) or {}).get("sources", {}),
    })


def _is_stale(as_of: str | None) -> bool:
    if not as_of:
        return True
    try:
        when = datetime.fromisoformat(as_of)
    except ValueError:
        return True
    from datetime import timezone
    now = datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (now - when).total_seconds() > config.STATE_STALE_HOURS * 3600


# ------------------------------------------------------------------ exports
def _attach(data: bytes, filename: str, mime: str):
    resp = make_response(data)
    resp.headers["Content-Type"] = mime
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return resp


@app.route("/export/scores.csv")
def export_csv():
    rows = state_mod.all_rows()
    day = datetime.now().strftime("%Y%m%d_%H%M")
    return _attach(csv_export.to_bytes(rows), f"company_lab_scores_{day}.csv",
                   "text/csv; charset=utf-8")


@app.route("/export/company_lab.xlsx")
def export_xlsx():
    rows = state_mod.all_rows()
    requested = (request.args.get("sheets") or "").strip()
    sheets = tuple(s.strip().lower() for s in requested.split(",") if s.strip()) \
        or xlsx_export.ALL_SHEETS
    sheets = tuple(s for s in sheets if s in xlsx_export.ALL_SHEETS) \
        or xlsx_export.ALL_SHEETS
    day = datetime.now().strftime("%Y%m%d_%H%M")
    try:
        data = xlsx_export.to_bytes(rows, sheets=sheets)
    except Exception as exc:  # noqa: BLE001 - never 500 the download
        return _attach(f"xlsx build failed: {type(exc).__name__}: {exc}".encode(),
                       "error.txt", "text/plain")
    return _attach(
        data, f"company_lab_{day}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/export/company/<ticker>.csv")
def export_company(ticker: str):
    if not TICKER_RE.match(ticker or ""):
        return _attach(b"bad ticker", "error.txt", "text/plain")
    card = state_mod.scorecard_for(ticker)
    if not card:
        return _attach(f"{ticker.upper()} has not been scored yet".encode(),
                       "error.txt", "text/plain")
    rows = csv_export.scorecard_long_rows(card)
    buf = io.StringIO(newline="")
    cols = ("ticker", "component", "component_label", "subtest", "label", "earned",
            "max_points", "status", "source", "tag_used", "threshold_note",
            "rationale", "evidence", "evidence_unverified")
    csv_export.write_csv(buf, rows, cols)
    return _attach(buf.getvalue().encode("utf-8-sig"),
                   f"{ticker.upper()}_scorecard.csv", "text/csv; charset=utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=config.UI_PORT)
    args = ap.parse_args(argv)
    print(f"company_lab dashboard: http://{config.UI_HOST}:{args.port}")
    print(f"  {config.ADVISORY_BANNER}")
    # threaded=True: the page fires several /api XHRs and single-threaded
    # Werkzeug starves page navigation behind them.
    app.run(host=config.UI_HOST, port=args.port, debug=False, threaded=True,
            use_reloader=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
