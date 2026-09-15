# company_lab task worker. ASCII-only (PowerShell 5.1 is cp1252 on this box).
#
# Called by the _run_*.vbs launchers, never directly by Task Scheduler.
#   powershell -NoProfile -ExecutionPolicy Bypass -File run_clab.ps1 -Task crawl
#
# Tasks:
#   crawl     weekly full refresh (quant half; the LLM half is a separate job)
#   queue     re-score whatever filed recently
#   snapshot  immutable point-in-time snapshot - cannot be backfilled, runs weekly
#   watchdog  did the crawl happen, and is the output sane
#   refresh   what external research is DUE this weekend (selects, never researches)
#
# Logs: journal\runs\<task>_<yyyyMMdd>.log

param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("crawl", "queue", "snapshot", "watchdog", "probe", "qual", "refresh")]
  [string]$Task,
  [string]$Extra = ""
)

# Continue, not Stop: a worker must finish its logging even if a step complains.
$ErrorActionPreference = "Continue"

$repo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $repo ".venv\Scripts\python.exe"   # never bare python (Store stub, exit 49)
if (-not (Test-Path $py)) { throw "missing interpreter: $py" }

$runs = Join-Path $repo "journal\runs"
New-Item -ItemType Directory -Force -Path $runs | Out-Null
$log = Join-Path $runs ($Task + "_" + (Get-Date -Format "yyyyMMdd") + ".log")

switch ($Task) {
  "crawl"    { $module = "clab.runner.batch";    $argline = "--tier sp500 --skip-qual --no-resume" }
  "queue"    { $module = "clab.runner.batch";    $argline = "--queue --skip-qual" }
  "snapshot" { $module = "clab.runner.snapshot"; $argline = "" }
  "watchdog" { $module = "clab.runner.watchdog"; $argline = "" }
  "probe"    { $module = "clab.runner.probe";    $argline = "--n 10" }
  # The LLM half, 100 companies a day. At the measured 78 s/company that is ~2.2 h,
  # so the ~1,000 companies the universe expansion added take about ten days. Chunking
  # is the user's call and a sound one: a 22-hour single run has nothing to show if it
  # dies at hour 21, whereas each of these ends with 100 more companies banked in the
  # cache. --max-minutes is a hard stop so a slow day cannot bleed into the evening.
  # --only-missing and --tier all are both load-bearing: without them the limit is
  # spent on the largest, already-cached names and the job scores nobody, every day.
  "qual"     { $module = "clab.qual.scorer";     $argline = "--tier all --only-missing --limit 100 --max-minutes 200 --wait-for-gpu" }
  "refresh"  { $module = "clab.external.refresh"; $argline = "" }
}
if ($Extra -ne "") { $argline = ($argline + " " + $Extra).Trim() }

Set-Location $repo
$env:PYTHONPATH = $repo

# The qual batch needs a HEALTHY Ollama server, and nothing else guarantees one. The
# 2026-08-14 run proved the failure mode: the server was alive enough to pass the
# availability check, then degraded, and per-company time went from ~30s to 215-679s
# with component timeouts - 16 companies scored in a 200-minute window instead of 100.
# The tray "ollama app" process being present is NOT the same as the server answering.
if ($Task -eq "qual") {
  function Test-Ollama {
    try { Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5 | Out-Null; return $true }
    catch { return $false }
  }
  if (-not (Test-Ollama)) {
    "[{0}] qual: ollama not answering, restarting it" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz") |
      Out-File -FilePath $log -Append -Encoding utf8
    Get-Process ollama* -ErrorAction SilentlyContinue |
      Where-Object { $_.ProcessName -ne "ollama app" } |
      Stop-Process -Force -ErrorAction SilentlyContinue
    $env:OLLAMA_MODELS = "D:\ollama\models"
    $exe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $exe) { Start-Process $exe -ArgumentList "serve" -WindowStyle Hidden }
    # It takes ~100s to answer on this box after a cold start.
    for ($i = 1; $i -le 30; $i++) { Start-Sleep -Seconds 6; if (Test-Ollama) { break } }
  }
  if (-not (Test-Ollama)) {
    # Loud, and stop. Running anyway would spend the window producing timeouts and
    # half-scored companies, then report success.
    "[{0}] qual: ERROR ollama never came up - skipping the batch" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz") |
      Out-File -FilePath $log -Append -Encoding utf8
    exit 1
  }
  # /api/tags answering is not the same as generation being fast - that is precisely
  # what failed on 2026-08-14. Time a trivial generation; a healthy box does this in a
  # couple of seconds, a degraded one takes tens.
  function Measure-Generate {
    $body = @{ model = "qwen2.5:7b"; prompt = "Reply with the single word: ok"
               stream = $false; options = @{ num_predict = 4 } } | ConvertTo-Json
    $t = Get-Date
    try {
      Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post `
        -Body $body -ContentType "application/json" -TimeoutSec 120 | Out-Null
      return ((Get-Date) - $t).TotalSeconds
    } catch { return 9999 }
  }
  $gen = Measure-Generate
  if ($gen -gt 45) {
    "[{0}] qual: generation probe took {1:N1}s - restarting ollama" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $gen |
      Out-File -FilePath $log -Append -Encoding utf8
    Get-Process ollama* -ErrorAction SilentlyContinue |
      Where-Object { $_.ProcessName -ne "ollama app" } |
      Stop-Process -Force -ErrorAction SilentlyContinue
    $env:OLLAMA_MODELS = "D:\ollama\models"
    $exe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $exe) { Start-Process $exe -ArgumentList "serve" -WindowStyle Hidden }
    for ($i = 1; $i -le 30; $i++) { Start-Sleep -Seconds 6; if (Test-Ollama) { break } }
    $gen = Measure-Generate
  }
  "[{0}] qual: ollama healthy (generation probe {1:N1}s)" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $gen |
    Out-File -FilePath $log -Append -Encoding utf8
}

"[{0}] {1} start ({2} {3})" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $Task, $module, $argline |
  Out-File -FilePath $log -Append -Encoding utf8

# Redirection is delegated to cmd.exe on purpose: PowerShell 5.1 wraps a native
# command's stderr in ErrorRecords and flips $? to false even on a clean exit 0.
& cmd.exe /c "`"$py`" -m $module $argline >> `"$log`" 2>&1"
$code = $LASTEXITCODE

# A qual batch only fills the CACHE. Until the scorecards are rebuilt the new judgement
# scores are invisible, and the workbook is a rebuild after that - so the whole chain
# runs here rather than leaving two manual steps nobody remembers at 12:15.
if ($Task -eq "qual" -and $code -eq 0) {
  # Re-score by SYMBOL, not by tier. `batch --tier X` honours the resume manifest and
  # skips companies already marked done, so freshly cached judgement scores would sit
  # in the cache invisible - which is exactly what happened on the first manual run:
  # 698 companies cached, only 407 reflected in the scorecards. --symbols bypasses
  # resume, and the scorer writes the list it just touched.
  # Fold by asking which scorecards are BEHIND their cache, not by replaying the batch
  # manifest. The manifest strands anything scored outside the last run - a 215-company
  # catch-up finishing overnight would be overwritten by the next day's manifest and
  # never folded. This self-heals whatever the cause.
  "[{0}] qual: folding every scorecard that is behind its cache" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz") |
    Out-File -FilePath $log -Append -Encoding utf8
  & cmd.exe /c "`"$py`" -m clab.runner.fold_qual >> `"$log`" 2>&1"
  # The fold's exit code used to be dropped on the floor here - $LASTEXITCODE was read
  # only after the export that follows. On 2026-08-16 the fold was refused by the probe
  # gate, 99 scorecards stayed behind their cache, and the task still reported exit=0.
  # A fold failure now surfaces in the task's own exit code.
  $foldRc = $LASTEXITCODE
  if ($foldRc -ne 0) {
    "[{0}] qual: ERROR fold_qual exit={1} - scorecards are behind their cache, the new judgement scores are NOT visible" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $foldRc |
      Out-File -FilePath $log -Append -Encoding utf8
    $code = $foldRc
  }
  # exit 3 = fresh data written but Excel held the stable filename open. Not a failure.
  & cmd.exe /c "`"$py`" -m clab.export.refresh >> `"$log`" 2>&1"
  # Captured IMMEDIATELY, and every later test reads $rc rather than $LASTEXITCODE.
  # Reading $LASTEXITCODE after a command that is not the one you mean is precisely the
  # bug that let the 2026-08-16 fold failure report exit=0.
  $rc = $LASTEXITCODE
  if ($rc -eq 3) {
    "[{0}] qual: workbook was open in Excel, refreshed to the _PENDING copy" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz") |
      Out-File -FilePath $log -Append -Encoding utf8
  } elseif ($rc -ne 0) {
    "[{0}] qual: WARN export refresh exit={1}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $rc |
      Out-File -FilePath $log -Append -Encoding utf8
  }

  # The non-S&P-500 leaderboard moves every time the judgement half fills further, so it
  # is regenerated here rather than sitting stale for someone to read months later.
  # Seconds, CPU only, and deliberately LAST so it cannot affect the task's exit code.
  & cmd.exe /c "`"$py`" -m clab.research.outside_sp500 --top 25 --md `"$repo\docs\outside_sp500.md`" >> `"$log`" 2>&1"
  if ($LASTEXITCODE -ne 0) {
    "[{0}] qual: WARN outside_sp500 report failed exit={1}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $LASTEXITCODE |
      Out-File -FilePath $log -Append -Encoding utf8
  }
}

"[{0}] {1} done exit={2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $Task, $code |
  Out-File -FilePath $log -Append -Encoding utf8

exit $code
