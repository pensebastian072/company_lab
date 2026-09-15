# Start the dashboard at login. ASCII-only. Per-user Startup shortcut, no UAC.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install_autostart.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install_autostart.ps1 -Uninstall
#
# A Startup .lnk is used rather than a scheduled task so no elevation is needed.
# It targets wscript.exe so no console window ever flashes.

param([switch]$Uninstall)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$vbs = Join-Path $repo "scripts\_ui.vbs"
$startup = [Environment]::GetFolderPath("Startup")
$lnk = Join-Path $startup "company_lab UI.lnk"

if ($Uninstall) {
  if (Test-Path $lnk) {
    Remove-Item $lnk -Force
    Write-Output ("removed " + $lnk)
  } else {
    Write-Output "nothing to remove"
  }
  return
}

if (-not (Test-Path $vbs)) { throw "missing $vbs" }

$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($lnk)
$s.TargetPath = "wscript.exe"
$s.Arguments = '"' + $vbs + '"'
$s.WorkingDirectory = $repo
$s.WindowStyle = 7
$s.Description = "company_lab dashboard on 127.0.0.1:8100"
$s.Save()

Write-Output ("installed " + $lnk)
Write-Output "dashboard: http://127.0.0.1:8100"
