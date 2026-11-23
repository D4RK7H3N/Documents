<#
Builds the Windows installer WITH a code signature and then verifies it.

Two ways to supply the certificate:

  1. Self-signed (free, for the school's own PCs):
       npm run build:win:signed:selfsigned
     The certificate + password are read from C:\certs\sms-signing-credentials.txt,
     which lives OUTSIDE the repository - nothing secret enters git.

  2. A real CA certificate:
       $env:CSC_LINK = "file:///C:/certs/your-cert.pfx"
       $env:CSC_KEY_PASSWORD = "..."
       npm run build:win:signed

electron-builder signs the app inside the installer AND the installer itself,
and adds a timestamp so the signature outlives the certificate's expiry.
After the build the installers are checked with Get-AuthenticodeSignature, so
a build that failed to sign is reported instead of shipping quietly.
#>

param(
    [switch]$SelfSigned
)

$ErrorActionPreference = 'Stop'

$credPath = 'C:\certs\sms-signing-credentials.txt'

if ($SelfSigned) {
    if (-not (Test-Path $credPath)) {
        throw "No signing credentials at $credPath. Run scripts\create-signing-cert.ps1 first."
    }
    $lines = Get-Content $credPath
    $pfx = ($lines | Where-Object { $_ -like 'pfx=*' }) -replace '^pfx=', ''
    $password = ($lines | Where-Object { $_ -like 'password=*' }) -replace '^password=', ''
    if (-not $pfx -or -not $password) {
        throw 'The credentials file is missing the pfx path or the password.'
    }
    # electron-builder wants a plain path (or base64) here - a "file:///" URL
    # gets resolved as C:\C:\... and the certificate is never found.
    $env:CSC_LINK = $pfx
    $env:CSC_KEY_PASSWORD = $password
    Write-Host "Signing with $pfx"
}

if (-not $env:CSC_LINK) {
    throw 'No certificate. Set CSC_LINK and CSC_KEY_PASSWORD, or run with -SelfSigned.'
}

Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'vite build failed' }

    npx electron-builder --win --x64 --ia32
    if ($LASTEXITCODE -ne 0) { throw 'electron-builder failed' }
}
finally {
    Pop-Location
}

# ---- verify the installers really are signed -------------------------------
$release = Join-Path (Split-Path -Parent $PSScriptRoot) 'release'
$installers = Get-ChildItem $release -Filter '*.exe' -File -ErrorAction SilentlyContinue
if (-not $installers) {
    throw 'No installer was produced in release\'
}

Write-Host ''
Write-Host 'Signature check:'
$unsigned = @()
foreach ($exe in $installers) {
    $sig = Get-AuthenticodeSignature $exe.FullName
    $subject = if ($sig.SignerCertificate) { $sig.SignerCertificate.Subject } else { $null }
    $stamp = if ($sig.TimeStamperCertificate) { 'timestamped' } else { 'NO TIMESTAMP' }
    if ($subject) {
        Write-Host ("  OK   {0}`n       signed by: {1}  ({2})" -f $exe.Name, $subject, $stamp)
    } else {
        Write-Host ("  FAIL {0} is NOT signed" -f $exe.Name)
        $unsigned += $exe.Name
    }
}

if ($unsigned.Count -gt 0) {
    throw ("These installers are not signed: " + ($unsigned -join ', '))
}

Write-Host ''
Write-Host 'All installers are signed.'
