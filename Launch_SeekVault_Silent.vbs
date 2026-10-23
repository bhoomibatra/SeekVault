' SeekVault Silent Background Launcher
' Starts SeekVault and opens the browser interface without keeping a visible console window open.

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
BatPath = ScriptDir & "\Launch_SeekVault.bat"

' Run the batch file hidden (0 = hide window, false = do not wait for return)
WshShell.Run """" & BatPath & """", 0, False
