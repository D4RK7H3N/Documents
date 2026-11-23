// Bump the version in package.json (and in the files that carry it).
const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, '..')
const pkgPath = path.join(root, 'package.json')
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'))
const next = process.argv[2]
if (!next) {
  console.log('current version:', pkg.version)
  process.exit(0)
}
pkg.version = next
fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n')
console.log('version:', pkg.version, '->', next)
