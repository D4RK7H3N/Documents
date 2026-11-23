/*
Downloads the Inter webfont (latin + latin-ext subsets) from Google Fonts and
writes local @font-face rules, so the app no longer needs an external request
to fonts.googleapis.com. That matters for two reasons:

  - the packaged Electron app runs a strict Content-Security-Policy that
    blocks the Google stylesheet, and the console complained about it
  - a school with an unreliable connection should still get the real font

Inter is served as a variable font, so one file per subset covers every
weight. The font files are Inter (SIL Open Font License 1.1), so they may be
redistributed with the app.
*/
import { mkdirSync, writeFileSync, readFileSync, readdirSync, unlinkSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')
const outDir = path.join(root, 'src', 'assets', 'fonts')
const UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
const WANTED = new Set(['latin', 'latin-ext'])

const css = await (
  await fetch(
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
    { headers: { 'User-Agent': UA } },
  )
).text()

mkdirSync(outDir, { recursive: true })

const blocks = css.split('/*').slice(1)
const faces = new Map()

for (const block of blocks) {
  const subset = block.slice(0, block.indexOf('*/')).trim()
  if (!WANTED.has(subset)) continue
  const weight = (block.match(/font-weight:\s*(\d+)/) || [])[1]
  const url = (block.match(/src:\s*url\((https:[^)]+)\)/) || [])[1]
  const range = (block.match(/unicode-range:\s*([^;]+);/) || [])[1]
  if (!weight || !url || !range) continue

  if (!faces.has(subset)) faces.set(subset, { weight, url, range })
}

const rules = []
for (const [subset, face] of faces) {
  const name = `Inter-${subset}.woff2`
  const bytes = Buffer.from(await (await fetch(face.url)).arrayBuffer())
  writeFileSync(path.join(outDir, name), bytes)
  console.log(`${name}  ${(bytes.length / 1024).toFixed(1)} KB`)
  rules.push(
    [
      '@font-face {',
      "  font-family: 'Inter';",
      '  font-style: normal;',
      '  font-weight: 300 700;',
      '  font-display: swap;',
      `  src: url('./assets/fonts/${name}') format('woff2');`,
      `  unicode-range: ${face.range};`,
      '}',
    ].join('\n'),
  )
}

// Drop the per-weight copies the first run left behind.
for (const f of readdirSync(outDir)) {
  if (/Inter-(latin|latin-ext)-\d+\.woff2$/.test(f)) unlinkSync(path.join(outDir, f))
}

writeFileSync(
  path.join(root, 'src', 'fonts.css'),
  `/* Inter (SIL Open Font License 1.1), served from the app itself. */\n${rules.join('\n\n')}\n`,
  'utf8',
)
console.log(`\n${rules.length} @font-face rules written to src/fonts.css`)
