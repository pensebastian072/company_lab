' Hidden launcher for the daily watchdog.
' NOT pythonw.exe - Norton 360 blocks that filename in a venv (see _run_crawl.vbs).
Set sh = CreateObject("WScript.Shell")
dir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
ps1 = dir & "run_clab.ps1"
sh.Run "powershell -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """ -Task watchdog", 0, False
