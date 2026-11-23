<#
Creates a self-signed code-signing certificate for the school app and
exports it OUTSIDE the repository:

  C:\certs\sms-signing.pfx          private key - keep secret, never commit
  C:\certs\sms-signing.cer          public only - safe to give to staff
  C:\certs\sms-signing-credentials.txt   the pfx password - keep secret

Usage (PowerShell, no admin needed for the CurrentUser store):
  powershell -ExecutionPolicy Bypass -File scripts\create-signing-cert.ps1
#>

$ErrorActionPreference = 'Stop'

$certDir = 'C:\certs'
$pfxPath = Join-Path $certDir 'sms-signing.pfx'
$cerPath = Join-Path $certDir 'sms-signing.cer'
$credPath = Join-Path $certDir 'sms-signing-credentials.txt'

# The Subject MUST be built with the O value QUOTED. Without the quotes the
# X.509 name parser chokes on the comma inside "Sagay City, Inc." and folds
# the whole string into ONE quoted CN. electron-updater compares the
# certificate's CN with the publisherName, so a folded CN never matches and
# every update is rejected with "not signed by the application owner".
$commonName = 'Dan Aldrin Espa' + [char]0xF1 + 'ol'
$organization = 'USAT College Sagay City, Inc.'
$country = 'PH'
$subject = 'CN=' + $commonName + ', O="' + $organization + '", C=' + $country

if (-not (Test-Path $certDir)) {
    New-Item -ItemType Directory -Path $certDir -Force | Out-Null
    Write-Host "Created $certDir"
}

# A strong random password for the exported .pfx.
$bytes = New-Object byte[] 24
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$password = [Convert]::ToBase64String($bytes).Replace('+','A').Replace('/','B').Replace('=','')

Write-Host 'Creating the code-signing certificate...'
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject $subject `
    -CertStoreLocation 'Cert:\CurrentUser\My' `
    -KeyExportPolicy Exportable `
    -KeyUsage DigitalSignature `
    -KeyAlgorithm RSA `
    -KeyLength 3072 `
    -HashAlgorithm SHA256 `
    -NotAfter (Get-Date).AddYears(3)

Write-Host ("Subject: " + $cert.Subject)
if ($cert.Subject -notmatch 'CN="' ) {
    Write-Host 'Subject has separate CN / O / C components.'
} else {
    Write-Warning 'The Subject looks folded into one CN - electron-updater would reject every update.'
}

$secure = ConvertTo-SecureString -String $password -AsPlainText -Force
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $secure | Out-Null
Export-Certificate -Cert $cert -FilePath $cerPath | Out-Null

@(
    "pfx=$pfxPath",
    "cer=$cerPath",
    "password=$password",
    "thumbprint=$($cert.Thumbprint)",
    "expires=$($cert.NotAfter.ToString('yyyy-MM-dd'))",
    "",
    'CSC_LINK=file:///C:/certs/sms-signing.pfx',
    "CSC_KEY_PASSWORD=$password"
) | Set-Content -Path $credPath -Encoding UTF8

Write-Host ''
Write-Host 'Done:'
Write-Host "  private key (secret) : $pfxPath"
Write-Host "  public cert (share)   : $cerPath"
Write-Host "  credentials (secret)  : $credPath"
Write-Host ''
Write-Host 'Next: npm run build:win:signed:selfsigned'
Write-Host 'Staff machines: run scripts\install-trusted-cert.ps1 with the .cer as admin.'
