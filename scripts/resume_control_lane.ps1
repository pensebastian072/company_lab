# Resume the E38 control lane after a reboot, and disable itself when the lane is done.
#
# The box took three unclean reboots on 2026-08-31 (15:51, 20:22, 22:08) and C: is
# asking for a full chkdsk, so a lane launched from a shell does not survive the night.
# This is registered as an at-logon Scheduled Task: every boot it restarts ollama
# DETACHED (a child of an agent task dies with that task) and resumes the lane, which
# is cache-resumable, so a crash costs one batch rather than the whole run.
#
# ASCII only - PowerShell 5.1 mis-decodes non-ASCII in a .ps1 as cp1252.

$ErrorActionPreference = 'Stop'

$Repo       = 'C:\Users\<your-user>\company_lab'
$RunsDir    = 'D:\company_lab_v2\journal\runs'
$CacheDir   = 'D:\company_lab_data\qual_qwen_struct'
$TargetCos  = 1471
$TaskName   = 'E38ControlLaneResume'
$Stamp      = Get-Date -Format 'yyyyMMdd'
$OllamaOut  = Join-Path $RunsDir 'ollama_serve_detached.log'
$OllamaErr  = Join-Path $RunsDir 'ollama_serve_detached.err.log'
$Ollama     = 'C:\Users\<your-user>\AppData\Local\Programs\Ollama\ollama.exe'

function Say([string]$m) {
  $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m
  Write-Output $line
  Add-Content -Path (Join-Path $RunsDir "control_resume_$Stamp.ps.log") -Value $line
}

# Already finished? Disable the task and get out of the way.
$cached = @(Get-ChildItem -Path $CacheDir -Filter *.json -ErrorAction SilentlyContinue).Count
$companies = [math]::Floor($cached / 3)
Say "cache holds $companies of $TargetCos companies"
if ($companies -ge $TargetCos) {
  Say "lane complete - disabling $TaskName"
  try { Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Out-Null } catch { Say "could not disable: $_" }
  exit 0
}

# ollama must be detached from whatever started it, or it dies with that process.
if (-not (Get-Process -Name ollama -ErrorAction SilentlyContinue)) {
  Say 'ollama not running - starting it detached'
  Start-Process -FilePath $Ollama -ArgumentList 'serve' -WindowStyle Hidden `
    -RedirectStandardOutput $OllamaOut -RedirectStandardError $OllamaErr
} else {
  Say 'ollama already running'
}

# Wait for the port, not the process - GPU discovery takes minutes on this box.
# 12 min, not 5: the 2026-09-01 08:21 run timed out at 5 while ollama was still probing
# backends during the morning startup storm.
function Wait-OllamaPort {
  foreach ($i in 1..144) {
    try {
      Invoke-WebRequest -Uri 'http://127.0.0.1:11434/api/tags' -UseBasicParsing -TimeoutSec 5 | Out-Null
      return $true
    } catch { Start-Sleep -Seconds 5 }
  }
  return $false
}

# The port answers just as happily on a CPU-only ollama, and that is not a slower run,
# it is a different one: 2026-09-01 measured 660-702 s/company on CPU against ~50 s on
# the GPU - 13x, or 67 hours for what was left. GPU discovery runs ONCE at startup with
# a 90 s per-backend watchdog, and during the morning storm (boot + Defender QuickScan +
# the task launches, all on the C: spinner) every backend blew it and ollama fell back to
# CPU for the life of the process. So ASSERT the GPU and restart until it appears.
function Test-OllamaOnGpu {
  try {
    $body = @{ model = 'qwen2.5:7b'; prompt = 'hi'; stream = $false;
               options = @{ num_predict = 1 } } | ConvertTo-Json
    Invoke-WebRequest -Uri 'http://127.0.0.1:11434/api/generate' -Method Post -Body $body `
      -ContentType 'application/json' -UseBasicParsing -TimeoutSec 600 | Out-Null
    $ps = Invoke-WebRequest -Uri 'http://127.0.0.1:11434/api/ps' -UseBasicParsing -TimeoutSec 30
    $loaded = ($ps.Content | ConvertFrom-Json).models
    foreach ($m in $loaded) {
      if ($m.name -like 'qwen2.5:7b*') {
        Say ("  qwen2.5:7b size=" + $m.size + " size_vram=" + $m.size_vram)
        return ($m.size_vram -gt 0)
      }
    }
    Say '  qwen2.5:7b not in /api/ps after a generate'
    return $false
  } catch { Say "  GPU probe failed: $_"; return $false }
}

$onGpu = $false
foreach ($attempt in 1..3) {
  if (-not (Wait-OllamaPort)) { Say 'ollama did not answer on 11434 within 12 min'; }
  else {
    Say "ollama answering on 11434 (attempt $attempt)"
    if (Test-OllamaOnGpu) { $onGpu = $true; break }
    Say '  ollama came up CPU-ONLY - discovery lost the GPU; restarting it'
  }
  Get-Process -Name ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 10
  Start-Process -FilePath $Ollama -ArgumentList 'serve' -WindowStyle Hidden `
    -RedirectStandardOutput $OllamaOut -RedirectStandardError $OllamaErr
}
if (-not $onGpu) {
  Say 'FATAL: ollama is CPU-only after 3 attempts - refusing to score at 13x cost.'
  Say '  the 30-minute repeat will try again; a quiet box usually finds the GPU in ~10 s.'
  exit 1
}
Say 'ollama is on the GPU'

$bash = 'C:\Program Files\Git\bin\bash.exe'
if (-not (Test-Path $bash)) { Say "FATAL: no bash at $bash"; exit 1 }

# Let bash own the redirection: PS 5.1 wraps a native exe's stderr in ErrorRecords
# and flips $? even on a clean exit. cd inside the -lc so cwd does not matter.
Say 'starting lane (blocking; resumes from cache)'
$laneOutPosix = '/d/company_lab_v2/journal/runs/control_resume_' + $Stamp + '.out'
& $bash -lc "cd /c/Users/<your-user>/company_lab && bash scripts/run_control_lane.sh >> $laneOutPosix 2>&1"
$rc = $LASTEXITCODE
Say "lane exited $rc"

$cached = @(Get-ChildItem -Path $CacheDir -Filter *.json -ErrorAction SilentlyContinue).Count
$companies = [math]::Floor($cached / 3)
Say "cache now holds $companies of $TargetCos companies"
if ($companies -ge $TargetCos) {
  Say "lane complete - disabling $TaskName"
  try { Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Out-Null } catch { Say "could not disable: $_" }
}
exit $rc
