// Import one of the school's own files and check where the students land.
const https = require('https')
const fs = require('fs')
const path = require('path')

const token = fs.readFileSync(path.join(__dirname, 'e2e', '.auth', 'token.txt'), 'utf8').trim()
const file = process.argv[2]

const boundary = '----sms' + Date.now()
const body = Buffer.concat([
  Buffer.from(
    `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${path.basename(file)}"\r\n` +
      'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n',
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
      console.log('status', r.statusCode)
      try {
        const d = JSON.parse(b)
        console.log('created/updated :', d.created ?? d.updated ?? d.count ?? '?')
        console.log('detected columns:', JSON.stringify(d.detected_columns || {}))
        console.log('rows with a section :', d.rows_with_section)
        console.log('rows without      :', d.rows_without_section)
        console.log('unmapped strands  :', JSON.stringify(d.unmapped_strands || {}))
        console.log('inherited strands :', JSON.stringify(d.strands_inherited_from_section || {}))
        console.log('errors            :', JSON.stringify((d.errors || []).slice(0, 5)))
      } catch {
        console.log(b.slice(0, 600))
      }
    })
  },
)
req.write(body)
req.end()
