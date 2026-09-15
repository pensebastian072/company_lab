# run_studies.ps1 - rebuild the panel and re-run every study, unattended.
#
# Everything here is DETERMINISTIC and needs no LLM and no network beyond the caches
# already on D:. It exists so the research half keeps moving without an interactive agent
# driving it - see HANDOFF.md.
#
# ASCII only (PowerShell 5.1 on this box mangles non-ASCII .ps1 files).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_studies.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_studies.ps1 -SkipPanel
#
# -SkipPanel reuses journal\experiments\E05_panel_*.parquet instead of paying ~50 minutes
# to rebuild them. Use it when only the study code changed.

[CmdletBinding()]
param(
    [switch]$SkipPanel,
    [switch]$SkipWorkbook
)

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$py = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { Write-Error "no venv python at $py"; exit 1 }

$env:PYTHONPATH = $repo
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmm'
$runs = Join-Path $repo 'journal\runs'
if (-not (Test-Path $runs)) { New-Item -ItemType Directory -Force -Path $runs | Out-Null }
$log = Join-Path $runs "studies_$stamp.log"

function Step {
    param([string]$Name, [string[]]$PyArgs)
    $t0 = Get-Date
    $header = "=== $Name ==="
    $header | Tee-Object -FilePath $log -Append | Out-Null
    Write-Host $header
    & $py @PyArgs *>> $log
    $code = $LASTEXITCODE
    $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    $verdict = if ($code -eq 0) { 'ok' } else { "FAILED exit $code" }
    $line = "    $Name : $verdict in $mins min"
    $line | Tee-Object -FilePath $log -Append | Out-Null
    Write-Host $line
    return $code
}

$start = "studies run $stamp"
$start | Tee-Object -FilePath $log | Out-Null
Write-Host $start
$failed = @()

if (-not $SkipPanel) {
    # One crawl, two panels: absolute and sector-relative. ~50 min for 705 symbols.
    $c = Step 'panel (survivorship-free, both scorings)' @(
        '-m', 'clab.research.panel', '--include-removed', '--both',
        '--out', 'journal\experiments\E05_panel.parquet')
    if ($c -ne 0) {
        # Without a panel nothing downstream means anything, so stop rather than
        # reporting studies computed on a stale or absent file.
        "    panel failed - skipping the studies that read it" | Tee-Object -FilePath $log -Append | Out-Null
        Write-Host "    panel failed - stopping" -ForegroundColor Red
        exit 1
    }
}

foreach ($s in @(
        @{ n = 'E02 battery';        a = @('-m', 'clab.research.battery',
                                           '--panel', 'journal\experiments\E05_panel_abs.parquet') },
        @{ n = 'E03 questions';      a = @('-m', 'clab.research.questions',
                                           '--panel', 'journal\experiments\E05_panel_abs.parquet') },
        @{ n = 'E05 four fixes';     a = @('-m', 'clab.research.e05_measure') },
        @{ n = 'E08 value trap';     a = @('-m', 'clab.research.e08_value_trap') }
    )) {
    if ((Step $s.n $s.a) -ne 0) { $failed += $s.n }
}

if (-not $SkipWorkbook) {
    # The Findings sheet reads E05_results.json / E08_results.json, so the workbook is
    # rebuilt last and picks up whatever the studies just concluded.
    # Exit 3 means the data is fresh but Excel held the stable filename open - that is a
    # warning, not a failed run, and the _PENDING file beside it has the new numbers.
    $c = Step 'workbook refresh' @('-m', 'clab.export.refresh')
    if ($c -eq 3) {
        Write-Host "    (workbook was open in Excel - see the _PENDING file)" -ForegroundColor Yellow
    } elseif ($c -ne 0) {
        $failed += 'workbook refresh'
    }
}

"" | Tee-Object -FilePath $log -Append | Out-Null
if ($failed.Count -gt 0) {
    $msg = "FAILED: " + ($failed -join ', ')
    $msg | Tee-Object -FilePath $log -Append | Out-Null
    Write-Host $msg -ForegroundColor Red
    Write-Host "log: $log"
    exit 1
}
"all studies ok" | Tee-Object -FilePath $log -Append | Out-Null
Write-Host "all studies ok"
Write-Host "log: $log"
exit 0
