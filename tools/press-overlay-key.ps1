# Test helper: presses Ctrl+Shift+B once, the same as doing it on the keyboard (toggles the build overlay).
param([int]$Delay = 0)
Start-Sleep -Seconds $Delay
$ws = New-Object -ComObject WScript.Shell
$ws.SendKeys("^+b")
Write-Host "Sent Ctrl+Shift+B"
