/*
Publishes the built installers to the rolling GitHub release the app
auto-updates from:
  https://github.com/D4RK7H3N/Management-System-for-Private-School/releases/tag/Releases

It uploads (replacing the assets of the same name):
  latest.yml                              - the update manifest
  School Management System Setup <ver>.exe - the installer
  School Management System Setup <ver>.exe.blockmap - differential download

The token is read from the environment (GH_TOKEN / GITHUB_TOKEN) or from the
git credential manager - it is never written to disk or printed.

  node scripts/publish-release.mjs [--dry-run]
*/

import { execFileSync } from 'node:child_process'
import { createReadStream, statSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')
const pkg = JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8'))

// The mirror target. electron-builder's publish config only holds the
// self-hosted feed (the app updates from the school's own server), so the
// GitHub release this mirrors to is stated here.
const MIRROR = {
  owner: 'D4RK7H3N',
  repo: 'Management-System-for-Private-School',
  releaseTagName: 'Releases',
}
const argValue = (name) => {
  const i = process.argv.indexOf('--' + name)
  return i >= 0 ? process.argv[i + 1] : undefined
}
const owner = argValue('owner') || MIRROR.owner
const repo = argValue('repo') || MIRROR.repo
const tag = argValue('tag') || MIRROR.releaseTagName || process.env.RELEASE_TAG || 'Releases'
const dryRun = process.argv.includes('--dry-run')

const token =
  process.env.GH_TOKEN ||
  process.env.GITHUB_TOKEN ||
  readGitCredential()

function readGitCredential() {
  try {
    const out = execFileSync('git', ['credential', 'fill'], {
      input: `protocol=https\nhost=github.com\n\n`,
      encoding: 'utf8',
    })
    const match = out.match(/^password=(.*)$/m)
    return match ? match[1].trim() : ''
  } catch {
    return ''
  }
}

if (!token) {
  console.error(
    'No GitHub token. Set GH_TOKEN, or sign in with "git credential-manager" first.'
  )
  process.exit(1)
}

const api = (path, options = {}) =>
  fetch(path.startsWith('http') ? path : `https://api.github.com${path}`, {
    ...options,
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${token}`,
      'X-GitHub-Api-Version': '2022-11-28',
      ...(options.headers || {}),
    },
  })

const version = pkg.version
const installerName = `School Management System Setup ${version}.exe`
const releaseDir = path.join(root, 'release')
// The manifest is uploaded LAST on purpose: it is the file the app reads to
// find the new build, so it must never point at an installer that is not
// there yet.
const files = [
  { name: installerName, file: path.join(releaseDir, installerName) },
  { name: `${installerName}.blockmap`, file: path.join(releaseDir, `${installerName}.blockmap`) },
  { name: 'latest.yml', file: path.join(releaseDir, 'latest.yml') },
]

for (const f of files) {
  if (!f.file || !statSync(f.file, { throwIfNoEntry: false })) {
    console.error(`Missing ${f.file} - run "npm run build:win:signed" first.`)
    process.exit(1)
  }
}

let release = null
const releaseRes = await api(`/repos/${owner}/${repo}/releases/tags/${tag}`)
if (!releaseRes.ok) {
  console.log(`Creating the "${tag}" release in ${owner}/${repo} ...`)
  const created = await api(`/repos/${owner}/${repo}/releases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tag_name: tag,
      name: tag,
      body: 'Desktop installers for the School Management System.',
      prerelease: false,
      draft: false,
    }),
  })
  if (!created.ok) {
    console.error(`Could not create the "${tag}" release: ${created.status} ${await created.text()}`)
    process.exit(1)
  }
  release = await created.json()
} else {
  release = await releaseRes.json()
}
console.log(`Release: ${release.html_url}`)

if (dryRun) {
  console.log('Dry run - would upload:', files.map(f => f.name).join(', '))
  process.exit(0)
}

// Remove every updater-relevant asset first - the manifest and installer
// of the previous build would otherwise collide with the new upload (GitHub
// rejects a duplicate asset name).
const keep = new Set(files.map(f => f.name))
const toDelete = (release.assets || []).filter(
  a => keep.has(a.name) || /\.exe$/.test(a.name) || /\.blockmap$/.test(a.name) || /\.yml$/.test(a.name)
)
for (const asset of toDelete) {
  const del = await api(`/repos/${owner}/${repo}/releases/assets/${asset.id}`, { method: 'DELETE' })
  console.log(`  removed old asset ${asset.name} (${del.status === 204 ? 'ok' : del.status})`)
}

for (const f of files) {
  const size = statSync(f.file).size
  // The installer is ~200 MB and the link drops now and then, so an upload is
  // retried instead of leaving the release half-published.
  let uploaded = null
  for (let attempt = 1; attempt <= 4; attempt++) {
    try {
      console.log(`  uploading ${f.name} (${(size / 1048576).toFixed(1)} MB), attempt ${attempt} ...`)
      const upload = await api(
        `https://uploads.github.com/repos/${owner}/${repo}/releases/${release.id}/assets?name=${encodeURIComponent(f.name)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/octet-stream',
            'Content-Length': String(size),
          },
          body: createReadStream(f.file),
          duplex: 'half',
        }
      )
      if (!upload.ok) {
        throw new Error(`${upload.status} ${await upload.text()}`)
      }
      uploaded = await upload.json()
      console.log(`  uploaded ${uploaded.name} -> ${uploaded.browser_download_url}`)
      break
    } catch (err) {
      console.error(`  upload of ${f.name} failed: ${err.message}`)
      if (attempt === 4) {
        console.error('Giving up on this asset - the release was left as it was.')
        process.exit(1)
      }
      await new Promise(r => setTimeout(r, 5000 * attempt))
    }
  }
}

// Make sure this release is the one GitHub reports as "latest".
if (release.prerelease) {
  await api(`/repos/${owner}/${repo}/releases/${release.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prerelease: false, draft: false }),
  })
  console.log('  release is no longer a prerelease')
}

console.log('\nDone. Installed apps will find this build on their next start.')
