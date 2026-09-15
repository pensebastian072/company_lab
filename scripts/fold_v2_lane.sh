#!/usr/bin/env bash
# Fold every company the v2 lane has finished into scorecards, scores.parquet and the
# workbook - and keep doing it while the lane runs.
#
# WHY THIS EXISTS: the lane's generations are durable the moment they are written, but
# they are durable as CACHED JSON. The spreadsheet is only built when something folds
# them. Without this, a box that dies at midnight leaves ~1,000 scored companies and a
# workbook containing the 20 that happened to be folded by hand - all the work present,
# none of it usable.
#
# So the workbook is rebuilt on a cycle and is never more than one cycle stale. There is
# nothing to "save" at the end: the artifact on disk is always current.
#
# It never touches the GPU. `clab.runner.batch` takes the v2 write lease and the scorer
# takes only the GPU lease, so this runs safely beside the generator - and the two lanes
# have SEPARATE write leases, so production is untouched either way.
#
# Usage:
#   bash scripts/fold_v2_lane.sh          # fold once, now
#   bash scripts/fold_v2_lane.sh --loop   # fold every FOLD_EVERY seconds until stopped
set -u

V2=/d/company_lab_v2
PY=/c/Users/<your-user>/company_lab/.venv/Scripts/python.exe
LANE_CACHE='D:\company_lab_data\qual_lfm25'
LOG="$V2/journal/runs/v2_fold_$(date +%Y%m%d).log"
FOLD_EVERY=${FOLD_EVERY:-1800}       # 30 minutes

export CLAB_QUAL_MODEL="hf.co/mradermacher/LFM2.5-2.6B-Finance-GGUF:Q4_K_M"
export CLAB_QUAL_DIR="$LANE_CACHE"
export CLAB_QUAL_NUM_PREDICT=2500
export CLAB_QUAL_STRUCTURED=1

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

fold_once() {
  # Every ticker whose three components are all cached. Anything mid-flight is simply
  # not in this list yet and gets picked up next cycle.
  local syms
  syms=$("$PY" -c "
import json, glob, os, collections
have = collections.Counter()
for p in glob.glob(os.path.join(r'$LANE_CACHE', '*.json')):
    have[os.path.basename(p).split('_')[0]] += 1
out = []
for p in glob.glob(os.path.join(r'$LANE_CACHE', '*_SG_*.json')):
    cik = os.path.basename(p).split('_')[0]
    if have.get(cik, 0) < 3:
        continue
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception:
        continue
    if d.get('ticker'):
        out.append(d['ticker'])
print(','.join(sorted(set(out))))
")
  if [ -z "$syms" ]; then
    say "nothing complete to fold yet"
    return 0
  fi
  local n
  n=$(awk -F, '{print NF}' <<< "$syms")
  say "folding ${n} completed companies"
  # --i-know: the probe gate refuses >50 symbols without a probe under 7 days old. It is
  # calibrated for a COLD crawl at ~4 s/symbol; this is a re-score from disk at ~0.4 s.
  # That exact mis-fire silently refused a 99-company fold on 2026-08-16, so the bypass is
  # deliberate and stated rather than worked around.
  ( cd "$V2" && "$PY" -m clab.runner.batch --symbols "$syms" --i-know ) >> "$LOG" 2>&1
  local rc=$?
  if [ "$rc" -ne 0 ]; then
    say "fold exited ${rc} - workbook may be stale; the cached generations are unaffected"
    return "$rc"
  fi
  local rows
  rows=$("$PY" -c "
import pandas as pd
print(len(pd.read_parquet(r'D:\company_lab_v2\data\scores.parquet')))
" 2>/dev/null || echo '?')
  say "  folded: v2 scores.parquet now has ${rows} rows; workbook rewritten"
}

if [ "${1:-}" = "--loop" ]; then
  say "fold loop started, every ${FOLD_EVERY}s - the workbook will never be more than one cycle stale"
  while true; do
    fold_once
    sleep "$FOLD_EVERY"
  done
else
  fold_once
fi
