' SeekVault Silent Background Launcher
' Runs SeekVault in background without keeping a visible console window open.

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
BatPath = ScriptDir & "\SeekVault Prototype\run_seekvault.bat"

WshShell.Run """" & BatPath & """ --silent", 0, False
