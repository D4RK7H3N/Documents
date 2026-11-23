# Signing the Windows installer (Authenticode)

The school app ships as an NSIS installer built by electron-builder:

```
frontend\release\School Management System Setup 1.1.0.exe
```

Unsigned, Windows shows *"Windows protected your PC"* and an unknown
publisher. Signed, it shows **Published by: Dan Aldrin Español**.

The publisher name comes from `win.signtoolOptions.publisherName` in
`package.json`; the certificate itself is issued to that name.

---

## Route 1 — self-signed (free, for the school's own PCs)

Already set up on the build machine. One command:

```powershell
cd "C:\Users\DarkZhen\Documents\System Project\frontend"
npm run build:win:signed:selfsigned
```

The script:

1. reads the certificate + password from `C:\certs\sms-signing-credentials.txt`
   (**outside the repository** — never committed),
2. sets `CSC_LINK` / `CSC_KEY_PASSWORD`,
3. builds the frontend and the installers,
4. **verifies** every produced installer with `Get-AuthenticodeSignature` and
   fails loudly if one is unsigned.

electron-builder signs the app inside the installer, the NSIS uninstaller and
the installer itself, and adds a timestamp.

### On each staff PC (one time, Administrator PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-trusted-cert.ps1 -CertPath "<share>\sms-signing.cer"
```

This puts the **public** certificate into `LocalMachine\Root` and
`LocalMachine\TrustedPublisher`. The private key never leaves the build
machine — only `C:\certs\sms-signing.cer` is shared.

After that the installer installs with **"Published by: Dan Aldrin Español"**
and no SmartScreen warning.

### Re-creating the certificate (e.g. it expires)

```powershell
npm run cert:create
```

It writes a fresh 3-year certificate to `C:\certs\` and prints where
everything is. Staff PCs must trust the new `.cer` as well.

---

## Route 2 — a real CA certificate (for PCs you don't control)

Get an OV/EV code-signing certificate (DigiCert, Sectigo, GlobalSign,
SSL.com, or Azure Trusted Signing), then:

```powershell
$env:CSC_LINK = "C:\certs\your-cert.pfx"     # plain path, or base64 of the pfx
$env:CSC_KEY_PASSWORD = "your-pfx-password"
cd "C:\Users\DarkZhen\Documents\System Project\frontend"
npm run build:win:signed
```

The same script runs, it just uses the certificate already in the environment.
Staff PCs then trust it automatically — no `install-trusted-cert.ps1` needed.

Note: a valid signature does not remove the SmartScreen warning immediately
for a brand-new publisher. Submit the installer to Microsoft's SmartScreen
submission portal, or distribute through winget / the Microsoft Store.

---

## Checking a signature any time

```powershell
npm run verify:signature
```

Uses `Get-AuthenticodeSignature`, so it works **without the Windows SDK**
(`signtool.exe` is not installed on every machine).

To sign an installer that was already built (not recommended — the app inside
stays unsigned), install the Windows SDK and run:

```powershell
signtool sign /fd SHA256 /tr https://timestamp.digicert.com /td SHA256 `
  /f C:\certs\sms-signing.pfx /p "%PWD%" `
  "release\School Management System Setup 1.1.0.exe"
```

---

## Files

| File | Purpose |
|---|---|
| `scripts/create-signing-cert.ps1` | Creates the self-signed certificate (`C:\certs\`) |
| `scripts/build-signed.ps1` | Builds with signing and verifies the result |
| `scripts/install-trusted-cert.ps1` | Trusts the public cert on a staff PC |
| `scripts/verify-signature.ps1` | Reports the signature state of the installers |

Secrets live in `C:\certs\` (outside the repo). `.gitignore` also blocks
`*.pfx`, `*.p12`, `*.cer`, `*.pem`, `*.key` and `signing-credentials*.txt`.
