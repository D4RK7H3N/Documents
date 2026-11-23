<#
Checks that the installers in release\ really carry a code signature.

Uses Get-AuthenticodeSignature, so it works without the Windows SDK
(signtool.exe is not installed on every machine).

  powershell -ExecutionPolicy Bypass -File scripts/verify-signature.ps1
#>

$ErrorActionPreference = 'Stop'

$release = Join-Path (Split-Path -Parent $PSScriptRoot) 'release'
$installers = Get-ChildItem $release -Filter '*.exe' -File -ErrorAction SilentlyContinue

if (-not $installers) {
    Write-Error "No installer found in $release"
}

$failed = $false
foreach ($exe in $installers) {
    $sig = Get-AuthenticodeSignature $exe.FullName
    if ($sig.SignerCertificate) {
        $stamp = if ($sig.TimeStamperCertificate) { 'timestamped' } else { 'NO TIMESTAMP' }
        Write-Host ("OK   {0}" -f $exe.Name)
        Write-Host ("     signed by : {0}" -f $sig.SignerCertificate.Subject)
        Write-Host ("     status    : {0} ({1})" -f $sig.Status, $stamp)
    } else {
        $failed = $true
        Write-Host ("FAIL {0} is not signed" -f $exe.Name)
    }
}

if ($failed) { exit 1 }
Write-Host ''
Write-Host 'All installers carry a code signature.'
