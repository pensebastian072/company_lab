#!/usr/bin/env bash
# E38 control lane - qwen2.5:7b run with the v2 lane's SCHEMA and TOKEN BUDGET.
#
# This is the missing cell of the E36 design. Production's qwen payloads are
# unconstrained at 700 tokens; the v2 lane's LFM2.5 payloads are schema-constrained at
# 2,500. Two things changed at once, so E36 cannot say whether the candidate's missing
# abstention - or the extra +4.34 score points E37 found on commonly-scored sub-tests -
# is the model or the format. Change ONE thing and the difference becomes attributable:
#
#   (this lane - production)   = the FORMAT effect
#   (v2 lane   - this lane)    = the MODEL effect
#
# It writes to its OWN cache dir and folds NOTHING. There is no third workbook: the
# comparison is payload-level, like E36's. Production and the v2 lane are untouched.
#
# The GPU is single-tenant. Do not start this while the v2 lane is still generating -
# both would sit on `--wait-for-gpu` and each would take twice as long for no reason.
#
# Order comes from `clab.research.e38_draw_control`, stratified and shuffled, so stopping
# anywhere leaves a balanced sample. Resume is automatic and identical to the v2 lane's:
# the driver asks this cache what is already complete and scores only the remainder.
#
# Usage:  bash scripts/run_control_lane.sh [sample_json]
set -u

V2=/d/company_lab_v2
PY=/c/Users/<your-user>/company_lab/.venv/Scripts/python.exe
# WINDOWS path: read by the venv's Windows python, which cannot open a POSIX /c/... path.
SAMPLE="${1:-C:/Users/penas/company_lab/journal/experiments/E38_control_sample.json}"
LANE_CACHE='D:\company_lab_data\qual_qwen_struct'
LOG="$V2/journal/runs/control_lane_$(date +%Y%m%d).log"
BATCH=25

export CLAB_QUAL_MODEL="qwen2.5:7b"
export CLAB_QUAL_DIR="$LANE_CACHE"
export CLAB_QUAL_NUM_PREDICT=2500
export CLAB_QUAL_STRUCTURED=1

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# Checked by the SAME interpreter that will read it, on the same path string - a bash
# `-f` test on a Windows path is a different question than the one that matters.
if ! "$PY" -c "import json; json.load(open(r'$SAMPLE'))" >/dev/null 2>&1; then
  say "FATAL: no readable sample at ${SAMPLE}."
  say "  draw it first:  $PY -m clab.research.e38_draw_control"
  exit 2
fi

mapfile -t TODO < <("$PY" -c "
import json, glob, os, collections
order = json.load(open(r\"$SAMPLE\"))[\"order\"]
have = collections.Counter()
for p in glob.glob(os.path.join(r\"$LANE_CACHE\", \"*.json\")):
    have[os.path.basename(p).split(\"_\")[0]] += 1
done_tickers = set()
for p in glob.glob(os.path.join(r\"$LANE_CACHE\", \"*_SG_*.json\")):
    try:
        d = json.load(open(p, encoding=\"utf-8\"))
    except Exception:
        continue
    cik = os.path.basename(p).split(\"_\")[0]
    if have.get(cik, 0) >= 3 and d.get(\"ticker\"):
        done_tickers.add(d[\"ticker\"])
print(chr(10).join(t for t in order if t not in done_tickers))
")
TOTAL=${#TODO[@]}

# An empty order is a WIRING failure unless the cache really is complete - the same trap
# the v2 lane fell into once, reporting "COMPLETE: 0 companies" on an unreadable path.
if [ "$TOTAL" -eq 0 ]; then
  n_cached=$(ls "D:/company_lab_data/qual_qwen_struct" 2>/dev/null | wc -l)
  if [ "$n_cached" -lt 30 ]; then
    say "FATAL: 0 companies to run and only ${n_cached} cached payloads - refusing to report success. Check ${SAMPLE} is a WINDOWS path the venv python can open."
    exit 2
  fi
  say "nothing left to run: every company in the order is already complete"
  exit 0
fi

say "E38 control lane: ${TOTAL} companies to score with qwen2.5:7b, structured, 2500 tok"
say "  registered minimum for reporting is 100 companies"
i=0
while [ "$i" -lt "$TOTAL" ]; do
  chunk=$(IFS=,; echo "${TODO[*]:$i:$BATCH}")
  n_through=$(( i + BATCH )); [ "$n_through" -gt "$TOTAL" ] && n_through=$TOTAL
  say "batch $(( i/BATCH + 1 )): ${chunk}"
  ( cd "$V2" && "$PY" -m clab.qual.scorer --symbols "$chunk" --wait-for-gpu ) >> "$LOG" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    say "batch $(( i/BATCH + 1 )) exited ${rc} - STOPPING. Relaunch this script to resume."
    exit "$rc"
  fi
  cached=$(ls "D:/company_lab_data/qual_qwen_struct" 2>/dev/null | wc -l)
  say "  through ${n_through}/${TOTAL} of this run; ${cached} payloads cached ($(( cached / 3 )) companies)"
  i=$(( i + BATCH ))
done

say "E38 control lane COMPLETE: ${TOTAL} companies scored this run"
say "next: python -m clab.research.e36_compare --v2-dir D:\\company_lab_data\\qual_qwen_struct  (format effect)"
