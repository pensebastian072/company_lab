# Run ONE block of the Phase B CPU lane, then exit.
#
# This is the SECOND lane. It runs the same model over the same book into the same output
# directory as resume_phase_b_v2.ps1, but on the CPU against a second ollama server on
# :11435, so the two add up instead of queueing behind one another.
#
# Measured 2026-09-13 on this box, paired on PTC/NVDA/INTU/FSLR:
#
#     GPU lane alone                67.4 s/company   = 53 companies/hour
#     CPU lane (contended)          59.6 s/company
#     GPU lane while CPU lane ran  102.8 s/company
#     both together                              ~= 95 companies/hour
#
# So the second lane is worth roughly +79%, NOT +100%: it takes cores the GPU lane needs
# for tokenisation, sampling and the D: reads. CLAB_NUM_THREAD caps it for that reason.
#
# ASCII only - PowerShell 5.1 mis-decodes a UTF-8 no-BOM script as cp1252 and a single
# em-dash turns into "string missing terminator".

$ErrorActionPreference = 'Stop'

$repo   = 'C:\Users\<your-user>\company_lab'
$py     = Join-Path $repo '.venv\Scripts\python.exe'
$runner = Join-Path $repo 'scripts\run_phase_b_local.py'
$outDir = 'D:\company_lab_data\external\phase_b_lfm25'
$model  = 'hf.co/mradermacher/LFM2.5-2.6B-Finance-GGUF:Q4_K_M'
$cpuUrl = 'http://127.0.0.1:11435'
$logDir = Join-Path $repo 'journal\runs'
$log    = Join-Path $logDir ('phase_b_cpu_{0}.log' -f (Get-Date -Format 'yyyyMMdd'))

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Log([string]$msg) {
    $line = ('{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg)
    Add-Content -Path $log -Value $line          # append-only; never Get-Content|Set-Content
    Write-Output $line
}

if (-not (Test-Path 'D:\company_lab_data')) {
    Write-Log 'D: not available - skipping this block'
    exit 0
}

$done = (Get-ChildItem -Path $outDir -Filter '*.json' -ErrorAction SilentlyContinue |
         Where-Object { $_.Name -notlike '_status*' }).Count
if ($done -ge 1500) {
    Write-Log ('lane COMPLETE at {0} companies - disabling the task' -f $done)
    try { Disable-ScheduledTask -TaskName 'CompanyLabPhaseBCpu' -ErrorAction Stop | Out-Null }
    catch { Write-Log ('could not disable the task: {0}' -f $_.Exception.Message) }
    exit 0
}

# Check the PORT, not the process name. Get-Process finds the GPU server on :11434 and
# would report a CPU server that is not there as healthy - the "a running ollama is not a
# working ollama" rule in CLAUDE.md, one level up.
$listening = $null -ne (Get-NetTCPConnection -LocalPort 11435 -State Listen -ErrorAction SilentlyContinue)
if (-not $listening) {
    Write-Log 'no ollama listening on 11435 - starting a second server detached'
    $exe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    # Detached on purpose: started as a child of this task it dies when the task is torn
    # down. OLLAMA_HOST is what puts it on its own port.
    $env:OLLAMA_HOST = '127.0.0.1:11435'
    Start-Process -FilePath $exe -ArgumentList 'serve' -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir 'ollama_cpu.log') `
        -RedirectStandardError  (Join-Path $logDir 'ollama_cpu.err')
    Start-Sleep -Seconds 25
}

Write-Log ('block starting: {0} of 1500 companies already done' -f $done)

$env:PYTHONPATH      = $repo
$env:OLLAMA_URL      = $cpuUrl
# 0 = no GPU layers at all. CUDA_VISIBLE_DEVICES does NOT hold ollama off the card here:
# a server started with CUDA_VISIBLE_DEVICES=-1 on 2026-09-13 reported size_vram=1.79GB
# and was competing with the GPU lane. The runner's --cpu asserts size_vram == 0 and
# refuses to run otherwise, so a regression here stops the lane instead of stealing the card.
$env:CLAB_NUM_GPU    = '0'
# 5 of 8 cores. Uncapped, this lane pushed the GPU lane from 67.4 to 102.8 s/company.
$env:CLAB_NUM_THREAD = '5'

Push-Location $repo
try {
    $errFile = Join-Path $logDir ('phase_b_cpu_{0}.err' -f (Get-Date -Format 'yyyyMMdd'))
    # --reverse: this lane walks the book BACKWARDS so the two lanes start at opposite
    # ends and never pick the same company at the same moment. Worst case at the meeting
    # point is one company researched twice, which costs time and corrupts nothing.
    $out = & $py $runner --block 24 --cpu --reverse --model $model --out $outDir 2>> $errFile
    $code = $LASTEXITCODE
    foreach ($line in $out) { Add-Content -Path $log -Value ('    ' + $line) }
    Write-Log ('block finished with exit code {0}' -f $code)
} finally {
    Pop-Location
}

if ($code -ne 0) {
    Write-Log ('BLOCK FAILED - see {0}' -f $errFile)
    exit $code
}

$after = (Get-ChildItem -Path $outDir -Filter '*.json' -ErrorAction SilentlyContinue |
          Where-Object { $_.Name -notlike '_status*' }).Count
Write-Log ('now {0} of 1500 done ({1:N1} percent)' -f $after, (100.0 * $after / 1500))
exit 0
