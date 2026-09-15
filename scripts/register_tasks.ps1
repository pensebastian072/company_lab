# Register the company_lab scheduled tasks. ASCII-only.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register_tasks.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register_tasks.ps1 -Unregister
#
# Registered (never elevated - these run as the logged-in user at Limited level):
#   CompanyLabSnapshot   Sat 12:00   immutable point-in-time snapshot. Registered
#                                    FIRST and on purpose: a snapshot of a past
#                                    date cannot be reconstructed later.
#   CompanyLabCrawl      Sat 03:00   full S&P 500 quant refresh (~30 min measured)
#   CompanyLabWatchdog   daily 12:00 did the crawl happen, is the output sane
#
# Test a task by hand:
#   Start-ScheduledTask -TaskName CompanyLabSnapshot
# Logs: journal\runs\<task>_<yyyyMMdd>.log

param([switch]$Unregister)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$scripts = Join-Path $repo "scripts"

$tasks = @(
  @{ Name = "CompanyLabSnapshot"; Vbs = "_run_snapshot.vbs"; Weekly = "Saturday"; At = "12:00"; Minutes = 10 },
  @{ Name = "CompanyLabCrawl";    Vbs = "_run_crawl.vbs";    Weekly = "Saturday"; At = "03:00"; Minutes = 480 },
  @{ Name = "CompanyLabWatchdog"; Vbs = "_run_watchdog.vbs"; Weekly = "";         At = "12:00"; Minutes = 10 },
  # The LLM half, 100 companies a day after midday (user's cadence). ~2.2 h at the
  # measured 78 s/company, so the ~1,000 companies the S&P 400/600 expansion added take
  # about ten days. Runs after noon so it never collides with the 03:00 Saturday crawl,
  # and the 240-minute limit stops a slow day bleeding into the evening.
  @{ Name = "CompanyLabQual";     Vbs = "_run_qual.vbs";     Weekly = "";         At = "12:15"; Minutes = 240 },
  # The weekend external-refresh SELECTOR. Runs after the crawl (03:00, up to 8h)
  # and the snapshot (12:00), so the book it reads is the one just built. It only
  # decides what is DUE - external research needs a Codex session, so a task can
  # never do the research itself, and this one does not pretend to.
  # Run it by hand any time with:  Start-ScheduledTask -TaskName CompanyLabExternalRefresh
  # or directly:  powershell -File scriptsun_clab.ps1 -Task refresh
  @{ Name = "CompanyLabExternalRefresh"; Vbs = "_run_refresh.vbs"; Weekly = "Saturday"; At = "13:00"; Minutes = 30 }
)

if ($Unregister) {
  foreach ($t in $tasks) {
    Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output ("unregistered " + $t.Name)
  }
  return
}

foreach ($t in $tasks) {
  $vbs = Join-Path $scripts $t.Vbs
  if (-not (Test-Path $vbs)) { throw "missing $vbs" }

  $action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument ('"' + $vbs + '"')

  if ($t.Weekly -ne "") {
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $t.Weekly -At $t.At
  } else {
    $trigger = New-ScheduledTaskTrigger -Daily -At $t.At
  }

  $settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes $t.Minutes)

  $principal = New-ScheduledTaskPrincipal `
    -UserId ($env:USERDOMAIN + "\" + $env:USERNAME) `
    -LogonType Interactive `
    -RunLevel Limited

  Register-ScheduledTask -TaskName $t.Name -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

  Write-Output ("registered " + $t.Name + " at " + $t.At + " " + $t.Weekly)
}

Write-Output ""
Write-Output "test:  Start-ScheduledTask -TaskName CompanyLabSnapshot"
Write-Output ("logs:  " + (Join-Path $repo "journal\runs"))
