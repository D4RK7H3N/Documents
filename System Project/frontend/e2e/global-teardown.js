// Runs after the whole suite: removes the students the import test brought
// in, so the roster is left exactly as the suite found it.
//
// Only the students that were NOT enrolled before the suite are removed -
// the school's own sheets may use LRNs that start with "00" as well, so the
// LRN rule cannot be used to tell them apart.
const fs = require('fs')
const path = require('path')
const { execFileSync } = require('child_process')

const API = process.env.E2E_API || 'https://sms.darkzhub.asia'
const BEFORE_FILE = path.join(__dirname, '.auth', 'students-before.json')
const NEW_FILE = path.join(__dirname, '.auth', 'students-added.json')

async function main() {
  const tokenFile = path.join(__dirname, '.auth', 'token.txt')
  if (!fs.existsSync(tokenFile)) {
    console.log('no API token - nothing to clean up')
    return
  }
  const token = fs.readFileSync(tokenFile, 'utf8').trim()
  const headers = { Authorization: `Token ${token}` }

  let rows = []
  try {
    const res = await fetch(`${API}/api/students/?page_size=2000`, { headers })
    if (!res.ok) {
      console.log('could not list the students:', res.status)
      return
    }
    const data = await res.json()
    rows = Array.isArray(data) ? data : data.results || []
  } catch (err) {
    console.log('could not list the students:', err.message)
    return
  }

  const before = fs.existsSync(BEFORE_FILE)
    ? JSON.parse(fs.readFileSync(BEFORE_FILE, 'utf8')).map(Number)
    : []
  const known = new Set(before)
  const added = rows.filter((s) => !known.has(Number(s.id))).map((s) => s.id)

  if (!added.length) {
    console.log('the suite added no students - the roster is untouched')
    return
  }
  fs.writeFileSync(NEW_FILE, JSON.stringify(added), 'utf8')

  // On the school's own machine the management command is the quickest way:
  // one call, no API rate limit.
  const managePy = path.resolve(__dirname, '..', '..', 'school_pos', 'manage.py')
  const python = path.resolve(__dirname, '..', '..', 'school_pos', '.venv', 'Scripts', 'python.exe')
  if (fs.existsSync(managePy) && fs.existsSync(python)) {
    try {
      execFileSync(python, [managePy, 'clear_sample_students', '--ids-file', NEW_FILE], {
        cwd: path.dirname(managePy),
        stdio: 'inherit',
      })
      return
    } catch (err) {
      console.log('the management command failed:', err.message)
    }
  }

  let removed = 0
  for (const id of added) {
    try {
      const res = await fetch(`${API}/api/students/${id}/`, { method: 'DELETE', headers })
      if (res.ok || res.status === 404) removed += 1
    } catch (err) {
      console.log('could not delete', id, err.message)
    }
  }
  console.log(`cleaned up ${removed} students`)
}

module.exports = async () => {
  await main()
}
