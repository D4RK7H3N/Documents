# Releasing a new version (auto-update)

The installed app checks GitHub for a newer build on start and offers to
install it. The feed is the rolling **"Releases"** release of
`D4RK7H3N/Management-System-for-Private-School`:

```
https://github.com/D4RK7H3N/Management-System-for-Private-School/releases/tag/Releases
```

It must always contain three assets:

| Asset | Purpose |
|---|---|
| `latest.yml` | the manifest electron-updater reads (version + download URL + sha512) |
| `School Management System Setup <version>.exe` | the installer |
| `School Management System Setup <version>.exe.blockmap` | enables the fast differential download |

## 1. Bump the version

The updater compares the version in `latest.yml` with the running app, so a
build with the **same** version is never offered. Every release needs a new
one:

```powershell
cd "C:\Users\DarkZhen\Documents\System Project\frontend"
npm version patch        # 1.1.1 -> 1.1.2 (or minor / major)
```

## 2. Build it (signed)

```powershell
npm run build:win:signed:selfsigned
```

This signs the installer with the self-signed certificate. See `SIGNING.md` for
the CA-certificate route and for how staff PCs trust the certificate.

## 3. Publish the assets

```powershell
npm run release:publish
```

The script:
- reads the GitHub token from `GH_TOKEN`/`GITHUB_TOKEN`, or from the git
  credential manager (it never prints or writes the token),
- deletes the previous `latest.yml`, the previous installer and any stale
  blockmap from the release,
- uploads the new `latest.yml`, the new installer and its blockmap,
- makes sure the release is not marked as a prerelease.

`npm run release:publish:dry` shows what it would do without uploading.

## 4. What staff see

On the next start of the installed app:

1. The app checks GitHub ~8 seconds after launch (in the background; a broken
   feed never blocks startup).
2. If a newer version exists, a dialog appears:
   **Install and restart** or **Later**. "Later" still installs it the next
   time the app is closed (`autoInstallOnAppQuit`).
3. Settings → **Check for updates** checks on demand and reports the version
   that is available.

The download is signed and verified against the sha512 in `latest.yml`.

## Notes and gotchas

- **Signing matters**: the updater runs the new installer, so it must be
  signed with the same certificate the staff PCs trust. An unsigned installer
  would bring back the SmartScreen warning.
- **Version bumps are mandatory** — same version = "no update available".
- The `blockmap` makes updates a few MB instead of ~200 MB. Without it the
  updater falls back to a full download.
- Only one build can be live on the rolling release: publishing replaces the
  assets, so keep a copy of any installer you still need to distribute.
- Auto-update is disabled in development (`app.isPackaged` check), so the
  dev server never talks to GitHub.
