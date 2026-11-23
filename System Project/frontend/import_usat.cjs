// Import every student file in the USAT folder through the real API.
const https = require('https')
const fs = require('fs')
const path = require('path')

const token = fs.readFileSync(path.join(__dirname, 'e2e', '.auth', 'token.txt'), 'utf8').trim()
const USAT = path.resolve('..', 'USAT')

function walk(dir) {
  const out = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) out.push(...walk(full))
    else if (/\.(csv|xlsx|xls)$/i.test(entry.name)) out.push(full)
  }
  return out
}

function upload(file) {
  return new Promise((resolve) => {
    const boundary = '----sms' + Date.now() + Math.random().toString(16).slice(2)
    const body = Buffer.concat([
      Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${path.basename(file)}"\r\n` +
          'Content-Type: application/octet-stream\r\n\r\n',
      ),
      fs.readFileSync(file),
      Buffer.from(`\r\n--${boundary}--\r\n`),
    ])
    const req = https.request(
      {
        host: 'sms.darkzhub.asia',
        path: '/api/students/bulk_upload/',
        method: 'POST',
        headers: {
          Authorization: 'Token ' + token,
          'Content-Type': 'multipart/form-data; boundary=' + boundary,
          'Content-Length': body.length,
        },
      },
      (r) => {
        let b = ''
        r.on('data', (c) => (b += c))
        r.on('end', () => {
          let d = {}
          try {
            d = JSON.parse(b)
          } catch {
            d = { raw: b.slice(0, 300) }
          }
          resolve({ status: r.statusCode, data: d })
        })
      },
    )
    req.write(body)
    req.end()
  })
}

;(async () => {
  const files = walk(USAT).sort()
  console.log('files to import:', files.length)
  let ok = 0
  for (const file of files) {
    const rel = path.relative(USAT, file)
    const { status, data } = await upload(file)
    const line =
      `${status === 200 ? 'OK ' : 'ERR'} ${rel.padEnd(46)} ` +
      `created=${data.created_count ?? 0} updated=${data.updated_count ?? 0} ` +
      `skipped=${data.skipped_count ?? 0} errors=${(data.errors || []).length} ` +
      `placedByFile=${data.rows_placed_by_file ?? 0} ` +
      `placedByStrand=${data.rows_placed_by_strand ?? 0} ` +
      `withSection=${data.rows_with_section ?? 0} without=${(data.rows_without_section || []).length} ` +
      `placeholder=${data.rows_with_placeholder_lrn ?? 0} ` +
      `namedInFile=${JSON.stringify(data.sections_named_in_file || [])} ` +
      `unmapped=${JSON.stringify(data.unmapped_strands || {})}`
    console.log(line)
    if (status === 200) ok += 1
    if ((data.errors || []).length) {
      data.errors.slice(0, 3).forEach((e) => console.log('      ! ' + e))
    }
    if ((data.unmapped_strands || {}) && Object.keys(data.unmapped_strands).length) {
      console.log('      ! unmapped strands: ' + JSON.stringify(data.unmapped_strands))
    }
  }
  console.log('\nimported:', ok, 'of', files.length)
})()
