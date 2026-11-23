param(
    [Parameter(Mandatory = $true)][string]$RainmeterPath,
    [Parameter(Mandatory = $true)][string]$VariablesPath,
    [Parameter(Mandatory = $true)][string]$MonitorIdsPath,
    [switch]$Once
)

$source = @"
using System;
using System.Runtime.InteropServices;

public static class GoldenGateWindowState
{
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    [StructLayout(LayoutKind.Sequential)]
    public struct MONITORINFO
    {
        public int Size;
        public RECT Monitor;
        public RECT Work;
        public uint Flags;
    }

    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool IsZoomed(IntPtr window);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr window, out RECT rect);
    [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr window, uint flags);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr window, System.Text.StringBuilder className, int length);
    [DllImport("user32.dll")] public static extern bool GetMonitorInfo(IntPtr monitor, ref MONITORINFO info);
}
"@

Add-Type -TypeDefinition $source

function Read-IniNumber([string]$Path, [string]$Key, [int]$Default) {
    try {
        $match = [regex]::Match([IO.File]::ReadAllText($Path), "(?m)^" + [regex]::Escape($Key) + "=(\d+)\s*$")
        if ($match.Success) { return [int]$match.Groups[1].Value }
    } catch {}
    return $Default
}

function Invoke-Rainmeter([string[]]$Arguments) {
    & $RainmeterPath @Arguments | Out-Null
}

function Hide-Bars {
    Invoke-Rainmeter -Arguments @('!CommandMeasure', 'MeasureBarVisibility', 'Hide()', 'GoldenGate\Bar')
    foreach ($slot in 2..4) {
        if ((Read-IniNumber $MonitorIdsPath ("Monitor{0}Width" -f $slot) 0) -gt 0) {
            Invoke-Rainmeter -Arguments @('!CommandMeasure', 'MeasureBarVisibility', 'Hide()', ("GoldenGate\Bar{0}" -f $slot))
        }
    }
}

function Show-Bars {
    Invoke-Rainmeter -Arguments @('!CommandMeasure', 'MeasureBarVisibility', 'Show()', 'GoldenGate\Bar')
    foreach ($slot in 2..4) {
        if ((Read-IniNumber $MonitorIdsPath ("Monitor{0}Width" -f $slot) 0) -gt 0) {
            Invoke-Rainmeter -Arguments @('!CommandMeasure', 'MeasureBarVisibility', 'Show()', ("GoldenGate\Bar{0}" -f $slot))
        }
    }
}

function Reload-Bars([bool]$UseAutoHide) {
    Invoke-Rainmeter -Arguments @('!DeactivateConfig', 'GoldenGate\Bar')
    Invoke-Rainmeter -Arguments @('!DeactivateConfig', 'GoldenGate\Bar2')
    Invoke-Rainmeter -Arguments @('!DeactivateConfig', 'GoldenGate\Bar3')
    Invoke-Rainmeter -Arguments @('!DeactivateConfig', 'GoldenGate\Bar4')
    Start-Sleep -Milliseconds 350

    $variant = if ($UseAutoHide) { '' } else { 'Keep' }

    foreach ($slot in 2..4) {
        if ((Read-IniNumber $MonitorIdsPath ("Monitor{0}Width" -f $slot) 0) -gt 0) {
            Invoke-Rainmeter -Arguments @('!ActivateConfig', ("GoldenGate\Bar{0}" -f $slot), ("Bar{0}{1}.ini" -f $slot, $variant))
        }
    }
    Invoke-Rainmeter -Arguments @('!ActivateConfig', 'GoldenGate\Bar', ("Bar{0}.ini" -f $variant))
}

function Test-ForegroundExpanded {
    $window = [GoldenGateWindowState]::GetForegroundWindow()
    if ($window -eq [IntPtr]::Zero) { return $null }

    $className = New-Object System.Text.StringBuilder 256
    [void][GoldenGateWindowState]::GetClassName($window, $className, $className.Capacity)
    if ($className.ToString() -eq 'RainmeterMeterWindow') { return $null }
    if ($className.ToString() -in @('Progman', 'WorkerW', 'Shell_TrayWnd')) { return $false }

    if ([GoldenGateWindowState]::IsZoomed($window)) { return $true }

    $rect = New-Object GoldenGateWindowState+RECT
    if (-not [GoldenGateWindowState]::GetWindowRect($window, [ref]$rect)) { return $false }
    $monitor = [GoldenGateWindowState]::MonitorFromWindow($window, 2)
    $info = New-Object GoldenGateWindowState+MONITORINFO
    $info.Size = [Runtime.InteropServices.Marshal]::SizeOf($info)
    if (-not [GoldenGateWindowState]::GetMonitorInfo($monitor, [ref]$info)) { return $false }

    $tolerance = 2
    return $rect.Left -le ($info.Monitor.Left + $tolerance) -and
        $rect.Top -le ($info.Monitor.Top + $tolerance) -and
        $rect.Right -ge ($info.Monitor.Right - $tolerance) -and
        $rect.Bottom -ge ($info.Monitor.Bottom - $tolerance)
}

$lastHidden = $false
$candidateHidden = $false
$candidateCount = 0
$autoHide = (Read-IniNumber $VariablesPath 'WindowBehavior' 1) -eq 1
$lastAutoHide = $autoHide
$modeReadCounter = 0
while ($true) {
    if ($modeReadCounter -le 0) {
        $autoHide = (Read-IniNumber $VariablesPath 'WindowBehavior' 1) -eq 1
        $modeReadCounter = 1
    } else {
        $modeReadCounter--
    }

    if ($autoHide -ne $lastAutoHide) {
        try {
            Reload-Bars -UseAutoHide $autoHide
        } catch {
            [IO.File]::WriteAllText(($VariablesPath + '.controller-error.log'), $_.Exception.ToString())
        }
        $lastAutoHide = $autoHide
        $lastHidden = $false
        $candidateHidden = $false
        $candidateCount = 0
        Start-Sleep -Milliseconds 250
    }

    $expanded = Test-ForegroundExpanded
    if ($null -eq $expanded) {
        if ($Once) { break }
        Start-Sleep -Milliseconds 100
        continue
    }

    $shouldHide = $autoHide -and $expanded

    if ($shouldHide -eq $candidateHidden) {
        $candidateCount++
    } else {
        $candidateHidden = $shouldHide
        $candidateCount = 1
    }

    if ($candidateCount -ge 2 -and $shouldHide -ne $lastHidden) {
        if ($shouldHide) { Hide-Bars } else { Show-Bars }
        $lastHidden = $shouldHide
        $candidateCount = 0
        Start-Sleep -Milliseconds 150
    }

    if ($Once) { break }

    Start-Sleep -Milliseconds 100
}
