// Put the version into package-lock.json as well (npm does this on install,
// but the release build must not need an install).
const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, '..')
const lockPath = path.join(root, 'package-lock.json')
const lock = JSON.parse(fs.readFileSync(lockPath, 'utf8'))
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'))

lock.version = pkg.version
if (lock.packages && lock.packages['']) {
  lock.packages[''].version = pkg.version
}
fs.writeFileSync(lockPath, JSON.stringify(lock, null, 2) + '\n')
console.log('package-lock.json ->', lock.version)
