# Test helper: holds Ctrl+Shift+B for a moment, like pressing it on the keyboard (toggles the build overlay).
param([int]$Delay = 0)
Start-Sleep -Seconds $Delay
Add-Type -Namespace RR -Name Keys -MemberDefinition '[DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, System.UIntPtr extra);'
$UP = 2
foreach ($vk in 0x11, 0x10, 0x42) { [RR.Keys]::keybd_event($vk, 0, 0, [UIntPtr]::Zero) }     # Ctrl, Shift, B down
Start-Sleep -Milliseconds 200
foreach ($vk in 0x42, 0x10, 0x11) { [RR.Keys]::keybd_event($vk, 0, $UP, [UIntPtr]::Zero) }    # and up again
Write-Host "Pressed Ctrl+Shift+B"
