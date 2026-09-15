#!/usr/bin/env bash
# E36 v2 lane driver - score the run order in checkpointed batches, resumably.
#
# BATCH is a checkpoint size, not cosmetics: the scorer caches per company, so a batch
# that dies costs at most the companies in flight, and it stays under the probe gate that
# refuses runs over 50 symbols.
#
# It is 25, not 10, and that is a MEASURED choice. Each invocation pays a fixed ~150 s of
# python startup plus `load_universe_multi` resolving 400 CIKs, before a single token is
# generated. Over 10 companies that overhead is ~15 s each and the lane ran at 43 s/company
# against the scorer's own 25 s median - roughly 40% of the wall clock spent on setup.
# Spread over 25 it is ~6 s each. Same checkpoint guarantee, ~4 hours less on a full
# universe.
#
# RESUME IS AUTOMATIC. The driver asks the lane's own cache which companies already have
# all three components and scores only the remainder, so it can be killed and relaunched
# at any point - after a reboot, a dead GPU, an overnight stop - with no index arithmetic
# and nothing scored twice. That is why it takes no start argument any more.
#
# The order is stratified AND shuffled, so stopping anywhere leaves a balanced sample
# rather than a skewed one. The full-universe order keeps the original 400 as its exact
# prefix, so work already done keeps its meaning.
#
# Usage:  bash scripts/run_v2_lane.sh [sample_json]
set -u

V2=/d/company_lab_v2
PY=/c/Users/<your-user>/company_lab/.venv/Scripts/python.exe
# WINDOWS path: read by the venv's Windows python, which cannot open a POSIX `/c/...`
# path. The first version passed one, python raised, the order came back empty, and the
# driver cheerfully logged "COMPLETE: 0 companies".
SAMPLE="${1:-C:/Users/penas/company_lab/journal/experiments/E36_sample_full.json}"
LANE_CACHE='D:\company_lab_data\qual_lfm25'
LOG="$V2/journal/runs/v2_lane_$(date +%Y%m%d).log"
BATCH=25

export CLAB_QUAL_MODEL="hf.co/mradermacher/LFM2.5-2.6B-Finance-GGUF:Q4_K_M"
export CLAB_QUAL_DIR="$LANE_CACHE"
export CLAB_QUAL_NUM_PREDICT=2500
export CLAB_QUAL_STRUCTURED=1

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# The remaining order: registered order minus anything already complete in the lane cache.
mapfile -t TODO < <("$PY" -c "
import json, glob, os, collections
order = json.load(open(r\"$SAMPLE\"))[\"order\"]
have = collections.Counter()
for p in glob.glob(os.path.join(r\"$LANE_CACHE\", \"*.json\")):
    parts = os.path.basename(p).split(\"_\")
    if len(parts) >= 2:
        have[parts[0]] += 1
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

# An empty order is a WIRING failure, never "nothing to do", UNLESS the cache really is
# complete. Without this the driver reports COMPLETE having scored nobody - exactly the
# graceful-degradation-hides-a-bug family CLAUDE.md is about, and it did happen once.
if [ "$TOTAL" -eq 0 ]; then
  n_cached=$(ls "D:/company_lab_data/qual_lfm25" 2>/dev/null | wc -l)
  if [ "$n_cached" -lt 30 ]; then
    say "FATAL: 0 companies to run and only ${n_cached} cached payloads - refusing to report success. Check ${SAMPLE} is a WINDOWS path the venv python can open."
    exit 2
  fi
  say "nothing left to run: every company in the order is already complete in the lane cache"
  exit 0
fi

say "v2 lane: ${TOTAL} companies still to score (order: $(basename "$SAMPLE"))"
i=0
while [ "$i" -lt "$TOTAL" ]; do
  chunk=$(IFS=,; echo "${TODO[*]:$i:$BATCH}")
  n_through=$(( i + BATCH )); [ "$n_through" -gt "$TOTAL" ] && n_through=$TOTAL
  say "batch $(( i/BATCH + 1 )): ${chunk}"
  ( cd "$V2" && "$PY" -m clab.qual.scorer --symbols "$chunk" --wait-for-gpu ) >> "$LOG" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    # A non-zero here is a RESULT, not a hiccup to paper over: the GPU lease was held too
    # long, ollama went away, or the model refused. Stop and let a human read it rather
    # than burning the rest of the universe against a broken generator. Relaunching the
    # driver resumes from exactly here.
    say "batch $(( i/BATCH + 1 )) exited ${rc} - STOPPING. Relaunch this script to resume."
    exit "$rc"
  fi
  cached=$(ls "D:/company_lab_data/qual_lfm25" 2>/dev/null | wc -l)
  say "  through ${n_through}/${TOTAL} of this run; ${cached} payloads cached ($(( cached / 3 )) companies)"
  i=$(( i + BATCH ))
done

say "v2 lane COMPLETE: ${TOTAL} companies scored this run"
say "next: from ${V2}, run clab.runner.batch --symbols ... to fold, then clab.export.refresh"
