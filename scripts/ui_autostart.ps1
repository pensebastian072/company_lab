# Start the dashboard if it is not already up. ASCII-only. Idempotent.
#
# The port probe matters: login autostart and a manual launch must never both
# bind 8100, and the probe makes a double-run a no-op instead of a crash.

$ErrorActionPreference = "Continue"

$repo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $repo ".venv\Scripts\python.exe"
$port = 8100

$up = $false
try {
  $c = New-Object Net.Sockets.TcpClient
  $c.Connect("127.0.0.1", $port)
  $up = $c.Connected
  $c.Close()
} catch { $up = $false }

if ($up) {
  Write-Output ("UI already up on 127.0.0.1:" + $port)
  return
}

$runs = Join-Path $repo "journal\runs"
New-Item -ItemType Directory -Force -Path $runs | Out-Null

Set-Location $repo
$env:PYTHONPATH = $repo

Start-Process -FilePath $py `
  -ArgumentList "-m", "clab.ui.app" `
  -WorkingDirectory $repo `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $runs "ui.log") `
  -RedirectStandardError (Join-Path $runs "ui.err.log")

Write-Output ("started UI on http://127.0.0.1:" + $port)
