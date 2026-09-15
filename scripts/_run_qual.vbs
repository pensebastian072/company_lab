' Hidden launcher for the daily LLM (qual) batch.
'
' Deliberately NOT pythonw.exe: Norton 360 on this box refuses to create the
' filename pythonw.exe inside a venv Scripts directory, so a pythonw autostart
' dies silently. wscript -> .vbs -> powershell -> python.exe is the working path.
' Do not "simplify" this back to pythonw.
Set sh = CreateObject("WScript.Shell")
dir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
ps1 = dir & "run_clab.ps1"
sh.Run "powershell -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """ -Task qual", 0, False
