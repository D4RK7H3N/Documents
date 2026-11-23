<#
Installs the school's self-signed code-signing certificate on a staff PC so
Windows trusts the installer and stops showing the SmartScreen warning.

Run this ONCE per machine, from an Administrator PowerShell:

  powershell -ExecutionPolicy Bypass -File scripts\install-trusted-cert.ps1 -CertPath "\\server\share\sms-signing.cer"

Only the PUBLIC certificate (.cer) is needed - never distribute the .pfx.
#>

param(
    [string]$CertPath = 'C:\certs\sms-signing.cer'
)

$ErrorActionPreference = 'Stop'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error 'Run this from an Administrator PowerShell.'
}

if (-not (Test-Path $CertPath)) {
    Write-Error "Certificate not found: $CertPath"
}

Write-Host "Installing $CertPath ..."
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 $CertPath

# Trusted Root - so the self-signed chain validates
$rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store 'Root', 'LocalMachine'
$rootStore.Open('ReadWrite')
$rootStore.Add($cert)
$rootStore.Close()

# Trusted Publisher - so the publisher name shows instead of "Unknown"
$publisherStore = New-Object System.Security.Cryptography.X509Certificates.X509Store 'TrustedPublisher', 'LocalMachine'
$publisherStore.Open('ReadWrite')
$publisherStore.Add($cert)
$publisherStore.Close()

Write-Host ''
Write-Host 'Installed. The app will now install without the "Windows protected your PC" warning.'
Write-Host 'Only the public certificate was copied - the private key never left the build machine.'
