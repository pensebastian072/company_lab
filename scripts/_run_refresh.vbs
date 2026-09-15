' Hidden launcher for the weekend external-refresh SELECTOR.
' It decides what research is due. It never researches anything - that needs a Codex
' session and cannot be driven from a Scheduled Task.
' NOT pythonw.exe - blocked as a filename in a venv on this box (see _run_crawl.vbs).
Set sh = CreateObject("WScript.Shell")
dir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
ps1 = dir & "run_clab.ps1"
sh.Run "powershell -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """ -Task refresh", 0, False
