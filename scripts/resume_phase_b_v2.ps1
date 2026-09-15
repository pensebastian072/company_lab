# Run ONE block of the Phase B v2 local-GPU lane, then exit.
#
# Registered as a Scheduled Task with an at-logon trigger and a 30-minute repeat, so the
# lane advances in blocks that survive reboots and the unclean shutdowns this box takes
# most days (five on 2026-08-31). CLAUDE.md's rule: anything that must live longer than an
# hour belongs in a repeat-triggered Scheduled Task, not a process tree.
#
# ASCII only - PowerShell 5.1 mis-decodes a UTF-8 no-BOM script as cp1252 and a single
# em-dash turns into "string missing terminator".
#
# Safe to run twice: the lane skips any company whose JSON already exists, and the task is
# registered with MultipleInstances=IgnoreNew so an overrunning block is never doubled.

$ErrorActionPreference = 'Stop'

$repo   = 'C:\Users\<your-user>\company_lab'
$py     = Join-Path $repo '.venv\Scripts\python.exe'
$runner = Join-Path $repo 'scripts\run_phase_b_local.py'
$outDir = 'D:\company_lab_data\external\phase_b_lfm25'
# LFM2.5 writes to its OWN directory. The 317 files in ..\phase_b_local were scored by
# qwen2.5:7b and E38 settled that the gap between two scorers is ~92% MODEL, so one
# directory holding both would be a book whose rows are not comparable to each other.
$model  = 'hf.co/mradermacher/LFM2.5-2.6B-Finance-GGUF:Q4_K_M'
$logDir = Join-Path $repo 'journal\runs'
$log    = Join-Path $logDir ('phase_b_lfm25_{0}.log' -f (Get-Date -Format 'yyyyMMdd'))

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Log([string]$msg) {
    $line = ('{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg)
    Add-Content -Path $log -Value $line          # append-only; never Get-Content|Set-Content
    Write-Output $line
}

# D: holds the filings and the output. If it is not mounted, do nothing at all rather than
# writing a partial lane onto the failing C: spinner.
if (-not (Test-Path 'D:\company_lab_data')) {
    Write-Log 'D: not available - skipping this block'
    exit 0
}

# Done? Disable the task so it stops waking the box every half hour. The lane is finished
# when every company in the book has an output file.
$done = (Get-ChildItem -Path $outDir -Filter '*.json' -ErrorAction SilentlyContinue |
         Where-Object { $_.Name -notlike '_status*' }).Count
if ($done -ge 1500) {
    Write-Log ('lane COMPLETE at {0} companies - disabling the task' -f $done)
    try { Disable-ScheduledTask -TaskName 'CompanyLabPhaseBv2' -ErrorAction Stop | Out-Null }
    catch { Write-Log ('could not disable the task: {0}' -f $_.Exception.Message) }
    exit 0
}

# Ollama must be up AND on the GPU. The runner asserts size_vram > 0 itself and exits
# non-zero if the model landed on CPU, which on this box is 660-702 s/company against ~50.
$ollama = Get-Process -Name 'ollama' -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Log 'ollama is not running - starting it detached'
    # Detached on purpose: started as a child of this task it dies when the task is torn
    # down. Redirect both streams to files so the handles are not inherited.
    $olog = Join-Path $logDir 'ollama_serve.log'
    Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden `
        -RedirectStandardOutput $olog -RedirectStandardError (Join-Path $logDir 'ollama_serve.err')
    Start-Sleep -Seconds 20
}

Write-Log ('block starting: {0} of 1500 companies already done' -f $done)

$env:PYTHONPATH = $repo
Push-Location $repo
try {
    # No 2>&1 on a native exe: PS 5.1 wraps native stderr in ErrorRecords and flips $? to
    # false even on exit 0. Let stdout through and capture it.
    # stderr to its own file rather than 2>&1: PS 5.1 wraps native stderr in ErrorRecords
    # and flips $? to false even on exit 0, but the traceback still has to land SOMEWHERE.
    # The first run of this lane exited 1 after one company and the traceback went nowhere,
    # which is why the errfile exists.
    $errFile = Join-Path $logDir ('phase_b_lfm25_{0}.err' -f (Get-Date -Format 'yyyyMMdd'))
    # Block of 24, not 55. LFM2.5 probed at 67.4 s/company against qwen's 30.6, so 55
    # companies would run 62 minutes and overrun the 30-minute repeat window every time.
    # 24 x 67.4s = ~27 min, which finishes before its successor is due.
    $out = & $py $runner --block 24 --model $model --out $outDir 2>> $errFile
    $code = $LASTEXITCODE
    foreach ($line in $out) { Add-Content -Path $log -Value ('    ' + $line) }
    Write-Log ('block finished with exit code {0}' -f $code)
} finally {
    Pop-Location
}

# Propagate the failure. The first version exited 0 unconditionally, so Task Scheduler
# recorded lastResult=0 on a block that had crashed - a green light over a red failure,
# which is the recurring bug on this box (an except/default that covers a WIRING error
# must be loud). A non-zero exit here shows up in Get-ScheduledTaskInfo.
if ($code -ne 0) {
    Write-Log ('BLOCK FAILED - see {0}' -f $errFile)
    exit $code
}

$after = (Get-ChildItem -Path $outDir -Filter '*.json' -ErrorAction SilentlyContinue |
          Where-Object { $_.Name -notlike '_status*' }).Count
Write-Log ('now {0} of 1500 done ({1:N1} percent)' -f $after, (100.0 * $after / 1500))
exit 0
