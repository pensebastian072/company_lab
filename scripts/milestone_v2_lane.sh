#!/usr/bin/env bash
# Freeze a reviewable copy of the v2 workbook when the lane reaches N companies.
#
# WHY A FROZEN COPY: `fold_v2_lane.sh --loop` rewrites `company_lab_latest.xlsx` every 30
# minutes, which is what makes the lane crash-safe - but it also means the file you open
# at 22:00 is not the file you opened at 21:30. A milestone review needs a workbook that
# holds still while it is being read, so this copies the artifact to its own name and
# leaves the rolling one to keep rolling.
#
# The lane is NOT paused to do this. Generation continues throughout; the copy is taken
# from a fold, which only reads the cache.
#
# Usage:
#   bash scripts/milestone_v2_lane.sh 1000
set -u

TARGET="${1:?usage: milestone_v2_lane.sh <n_companies>}"
POLL=${POLL:-300}

V2=/d/company_lab_v2
PY=/c/Users/<your-user>/company_lab/.venv/Scripts/python.exe
EXPORTS="$V2/data/exports"
LOG="$V2/journal/runs/v2_milestone_$(date +%Y%m%d).log"

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

complete_count() {
  "$PY" -c "
import glob, os, collections
have = collections.Counter()
for p in glob.glob(r'D:\company_lab_data\qual_lfm25\*.json'):
    have[os.path.basename(p).split('_')[0]] += 1
print(sum(1 for v in have.values() if v >= 3))
" 2>/dev/null || echo 0
}

say "milestone watcher armed: will freeze a workbook copy at ${TARGET} companies (polling every ${POLL}s)"
while true; do
  n=$(complete_count)
  if [ "$n" -ge "$TARGET" ]; then
    say "reached ${n} companies - folding, then freezing a copy"
    bash /c/Users/<your-user>/company_lab/scripts/fold_v2_lane.sh >> "$LOG" 2>&1
    stamp=$(date +%H%M)
    dest="$EXPORTS/company_lab_v2_at${TARGET}.xlsx"
    csv="$EXPORTS/scores_v2_at${TARGET}.csv"
    if [ -f "$EXPORTS/company_lab_latest.xlsx" ]; then
      cp "$EXPORTS/company_lab_latest.xlsx" "$dest"
      cp "$EXPORTS/scores_latest.csv" "$csv" 2>/dev/null || true
      rows=$("$PY" -c "
import pandas as pd
print(len(pd.read_parquet(r'D:\company_lab_v2\data\scores.parquet')))
" 2>/dev/null || echo '?')
      say "FROZEN at ${stamp}: ${dest} (${rows} companies)"
      say "  the rolling workbook keeps updating; this copy does not."
    else
      say "ERROR: no workbook at ${EXPORTS}/company_lab_latest.xlsx - fold may have failed"
      exit 1
    fi
    exit 0
  fi
  sleep "$POLL"
done
