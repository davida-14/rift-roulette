# Test helper: holds Ctrl+Shift+B for a moment, like pressing it on the keyboard (toggles the build overlay).
param([int]$Delay = 0, [int]$HoldMs = 200, [int]$Times = 1, [int]$GapMs = 3000)
Start-Sleep -Seconds $Delay
Add-Type -Namespace RR -Name Keys -MemberDefinition '[DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, System.UIntPtr extra);'
$UP = 2
for ($i = 1; $i -le $Times; $i++) {
    foreach ($vk in 0x11, 0x10) { [RR.Keys]::keybd_event($vk, 0, 0, [UIntPtr]::Zero) }        # Ctrl, Shift down
    Start-Sleep -Milliseconds 120
    [RR.Keys]::keybd_event(0x42, 0, 0, [UIntPtr]::Zero)                                      # B tapped
    Start-Sleep -Milliseconds $HoldMs
    [RR.Keys]::keybd_event(0x42, 0, $UP, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 120
    foreach ($vk in 0x10, 0x11) { [RR.Keys]::keybd_event($vk, 0, $UP, [UIntPtr]::Zero) }     # and let go
    Write-Host "Pressed Ctrl+Shift+B ($i)"
    if ($i -lt $Times) { Start-Sleep -Milliseconds $GapMs }
}
