/*
Copy the built release files onto this machine so the school serves its own
update feed, and keep GitHub Releases as a mirror.

  node scripts/publish-local.mjs            -> copy the files
  node scripts/publish-local.mjs --list     -> what is stored locally

Files are copied under a temporary name and renamed into place, so a client
that checks the feed mid-copy never sees a half-written installer.
*/
import { copyFileSync, existsSync, mkdirSync, readdirSync, renameSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')
const pkg = JSON.parse(
  await import('node:fs').then(m => m.readFileSync(path.join(root, 'package.json'), 'utf8'))
)

const target = process.env.SMS_RELEASES_DIR || path.join(root, '..', 'school_pos', 'releases')
const version = pkg.version
const releaseDir = path.join(root, 'release')
const installer = `School Management System Setup ${version}.exe`

if (process.argv.includes('--list')) {
  if (!existsSync(target)) {
    console.log(`${target} does not exist yet`)
    process.exit(0)
  }
  for (const f of readdirSync(target)) {
    const s = statSync(path.join(target, f))
    console.log(`  ${f}  ${(s.size / 1048576).toFixed(1)} MB`)
  }
  process.exit(0)
}

mkdirSync(target, { recursive: true })

const files = [
  { name: installer, file: path.join(releaseDir, installer) },
  { name: `${installer}.blockmap`, file: path.join(releaseDir, `${installer}.blockmap`) },
  { name: 'latest.yml', file: path.join(releaseDir, 'latest.yml') },
]

for (const f of files) {
  if (!existsSync(f.file)) {
    console.error(`Missing ${f.file} - run "npm run build:win:signed:selfsigned" first.`)
    process.exit(1)
  }
}

for (const f of files) {
  const dest = path.join(target, f.name)
  const tmp = `${dest}.part`
  copyFileSync(f.file, tmp)
  renameSync(tmp, dest)
  const size = (statSync(dest).size / 1048576).toFixed(1)
  console.log(`  stored ${f.name} (${size} MB)`)
}

// The previous version is kept so a rollback is possible.
console.log(`\nRelease feed ready on this machine: ${target}`)
console.log(`  ${installer}`)
console.log(`  latest.yml`)
