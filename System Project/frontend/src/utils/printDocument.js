import { receiptPeso } from '../components/ReceiptPaper'

/** True when the app runs inside the Electron shell. */
export const isElectron = () =>
  typeof window !== 'undefined' && !!window.electronAPI?.printHtml

const esc = (s) =>
  String(s ?? '')
    .replace(/&/g, '\u0026amp;')
    .replace(/</g, '\u0026lt;')
    .replace(/>/g, '\u0026gt;')
    .replace(/"/g, '\u0026quot;')

export async function printHtml(html, { pageSize = 'A4', landscape = false, title = 'Document' } = {}) {
  if (isElectron()) {
    try {
      const res = await window.electronAPI.printHtml({ html, pageSize, landscape, title })
      if (res?.ok) return true
      throw new Error(res?.error || 'Print failed')
    } catch (e) {
      throw e
    }
  }

  return new Promise((resolve, reject) => {
    const iframe = document.createElement('iframe')
    iframe.style.position = 'fixed'
    iframe.style.right = '0'
    iframe.style.bottom = '0'
    iframe.style.width = '0'
    iframe.style.height = '0'
    iframe.style.border = '0'
    document.body.appendChild(iframe)
    try {
      const doc = iframe.contentWindow.document
      doc.open()
      doc.write(html)
      doc.close()
      const doPrint = () => {
        try {
          iframe.contentWindow.focus()
          iframe.contentWindow.print()
          resolve(true)
        } catch (e) {
          reject(e)
        } finally {
          setTimeout(() => iframe.remove(), 2000)
        }
      }
      if (doc.readyState === 'complete' || doc.readyState === 'interactive') {
        setTimeout(doPrint, 100)
      } else {
        iframe.onload = doPrint
      }
    } catch (e) {
      iframe.remove()
      reject(e)
    }
  })
}

/* ---------------------------------------------------------------------------
 * DOM-node printing — serialize an existing rendered element together with
 * the app's compiled stylesheet, so ANY printable document (SOA, statements,
 * section rosters, enrollment form) prints Electron-safe without rewriting
 * its markup.
 * ------------------------------------------------------------------------- */

async function loadSheetText(href) {
  // Packaged Electron serves the app from file:// where <link> sheet rules
  // are unreadable from the renderer — fetch the text through main instead.
  if (isElectron() && window.electronAPI?.readAppCss) {
    try {
      const text = await window.electronAPI.readAppCss(href)
      if (text) return text
    } catch { /* fall through */ }
  }
  try {
    const res = await fetch(href, { mode: 'same-origin' })
    if (res.ok) return await res.text()
  } catch { /* ignore */ }
  return null
}

async function collectAppCss() {
  const chunks = []
  document.querySelectorAll('style').forEach((s) => chunks.push(s.textContent))
  const pending = []
  for (const sheet of Array.from(document.styleSheets)) {
    try {
      for (const rule of sheet.cssRules) chunks.push(rule.cssText)
    } catch {
      // Cross-origin or file:// sheet: recover its text asynchronously.
      if (sheet.href) {
        pending.push(
          loadSheetText(sheet.href).then((text) => { if (text) chunks.push(text) })
        )
      }
    }
  }
  if (pending.length) await Promise.all(pending)
  return chunks.join('\n')
}

/**
 * Print a rendered DOM node. The node's classes (Tailwind etc.) keep working
 * because the app's full compiled CSS is inlined into the print document;
 * @media print rules in it activate automatically in the print window.
 * extraCss carries the page-level @page/ resets that react-to-print used to
 * inject via its (removed) pageStyle option.
 */
export async function printNode(node, { pageSize = 'A4', landscape = false, title = 'Document', extraCss = '' } = {}) {
  if (!node) throw new Error('Nothing to print')
  const css = await collectAppCss()
  const html = `<!doctype html>
<html><head><meta charset="utf-8" /><title>${esc(title)}</title>
<style>${css}
${extraCss}
html, body { margin: 0 !important; padding: 0 !important; background: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
</style></head>
<body>${node.outerHTML}</body></html>`
  return printHtml(html, { pageSize, landscape, title })
}

/* ---------------------------------------------------------------------------
 * 80mm receipt (mirrors ReceiptPaper.jsx, but as standalone HTML+CSS so the
 * Electron print window needs no Tailwind.)
 * ------------------------------------------------------------------------- */

export function buildReceiptHtml(receipt, config, printLogo) {
  if (!receipt) return ''
  const peso = receiptPeso
  const row = (label, value, mono) =>
    `<tr><td class="l">${esc(label)}</td><td class="r ${mono ? 'mono' : ''}">${esc(value)}</td></tr>`

  const meta = [
    row('Receipt No.', receipt.receiptNumber, true),
    row('Date', new Date(receipt.timestamp).toLocaleString('en-PH')),
  ]
  if (receipt.cashierName) {
    meta.push(
      row(
        'Cashier',
        receipt.terminalId ? `${receipt.cashierName} (${receipt.terminalId})` : receipt.cashierName
      )
    )
  }
  if (receipt.student) {
    meta.push(row('Student', `${receipt.student.first_name} ${receipt.student.last_name}`))
    if (receipt.student.lrn) meta.push(row('LRN', receipt.student.lrn, true))
  } else if (receipt.studentName) {
    // Tuition receipts carry a pre-joined name + optional extra rows
    // (grade, school year, balances) instead of a student object.
    meta.push(row('Student', receipt.studentName))
    if (receipt.lrn) meta.push(row('LRN', receipt.lrn, true))
  } else {
    meta.push(row('Payer', receipt.payerName || 'Walk-in Customer'))
  }
  for (const [k, v] of receipt.extraRows || []) {
    meta.push(row(k, v))
  }

  const items = (receipt.lines || [])
    .map(
      (l) =>
        `<tr><td class="l">${esc(l.name)}${l.size ? ` <span class="dim">(${esc(l.size)})</span>` : ''} <span class="dim">x${esc(l.qty)}</span></td><td class="r mono">${esc(peso(l.amount))}</td></tr>`
    )
    .join('')

  const paymentRows = [
    row('Method', receipt.method + (receipt.reference ? ` (${receipt.reference})` : '')),
  ]
  if (receipt.method === 'Cash') {
    paymentRows.push(row('Tendered', peso(receipt.tendered)))
    paymentRows.push(row('Change', peso(receipt.change)))
  }

  const header =
    (printLogo ? `<img class="logo" src="${esc(printLogo)}" alt="" />` : '') +
    `<div class="school">${esc(config?.school_name || 'School Management System')}</div>` +
    (config?.full_address ? `<div class="sub">${esc(config.full_address)}</div>` : '') +
    (config?.contact_info ? `<div class="sub">${esc(config.contact_info)}</div>` : '') +
    `<div class="title">${esc(config?.receipt_header_text?.trim() || 'OFFICIAL RECEIPT')}</div>`

  const footer = config?.receipt_footer_text?.trim()
    ? esc(config.receipt_footer_text)
    : 'Thank you for your payment!<br />This is a computer-generated receipt.'

  return `<!doctype html>
<html><head><meta charset="utf-8" /><title>Official Receipt</title>
<style>
  @page { size: 80mm auto; margin: 4mm; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; color: #111; width: 72mm; }
  .receipt { width: 100%; }
  .head { text-align: center; border-bottom: 1px dashed #bbb; padding-bottom: 8px; margin-bottom: 8px; }
  .logo { width: 40px; height: 40px; object-fit: contain; margin-bottom: 4px; }
  .school { font-weight: 700; font-size: 11px; text-transform: uppercase; line-height: 1.25; }
  .sub { font-size: 9px; color: #444; }
  .title { font-weight: 700; font-size: 11px; margin-top: 6px; white-space: pre-line; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 1px 0; vertical-align: top; font-size: 11px; }
  td.l { color: #555; white-space: nowrap; padding-right: 6px; }
  td.r { text-align: right; font-weight: 500; }
  .mono { font-family: Consolas, 'Courier New', monospace; }
  .dim { color: #777; font-size: 10px; }
  .sep { border-top: 1px dashed #bbb; margin: 6px 0; }
  .items td { padding: 2px 0; }
  .total td { font-size: 12px; font-weight: 700; padding-top: 3px; }
  .foot { text-align: center; font-size: 9px; color: #555; margin-top: 10px; padding-top: 6px; border-top: 1px dashed #bbb; white-space: pre-line; }
</style></head>
<body><div class="receipt">
  <div class="head">${header}</div>
  <table>${meta.join('')}</table>
  <div class="sep"></div>
  <div class="items-label" style="font-size:10px;font-weight:700;text-transform:uppercase;color:#555;">Items</div>
  <table class="items">${items}</table>
  <div class="sep"></div>
  <table class="total"><tr><td class="l">TOTAL</td><td class="r mono">${esc(peso(receipt.total))}</td></tr></table>
  <table>${paymentRows.join('')}</table>
  <div class="foot">${footer}</div>
</div></body></html>`
}

/* ---------------------------------------------------------------------------
 * A4 revenue report — overall (totals + per-terminal table) or single
 * terminal (its totals + its transaction line items).
 * ------------------------------------------------------------------------- */

const peso = (n) =>
  `₱${Number(n || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

const REPORT_CSS = `
  @page { size: A4 portrait; margin: 14mm; }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { font-family: 'Segoe UI', Arial, sans-serif; color: #111827; font-size: 11px; }
  .head { display: flex; align-items: center; gap: 12px; border-bottom: 2px solid #1a3a5c; padding-bottom: 10px; margin-bottom: 14px; }
  .head img { width: 54px; height: 54px; object-fit: contain; }
  .school { font-size: 16px; font-weight: 700; color: #1a3a5c; }
  .addr { font-size: 10px; color: #4b5563; }
  h1 { font-size: 14px; margin: 0 0 2px; }
  .meta { color: #4b5563; font-size: 10px; margin-bottom: 12px; }
  h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.03em; color: #374151; border-bottom: 1px solid #d1d5db; padding-bottom: 3px; margin: 14px 0 6px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
  th, td { border: 1px solid #e5e7eb; padding: 5px 7px; text-align: left; }
  th { background: #f3f4f6; font-size: 10px; text-transform: uppercase; letter-spacing: 0.02em; color: #374151; }
  td.num, th.num { text-align: right; font-family: Consolas, 'Courier New', monospace; }
  tr.grand td { font-weight: 700; background: #f9fafb; }
  .cards { display: flex; gap: 8px; margin-bottom: 4px; }
  .card { flex: 1; border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px 10px; }
  .card .k { font-size: 9px; text-transform: uppercase; color: #6b7280; }
  .card .v { font-size: 14px; font-weight: 700; font-family: Consolas, monospace; }
  .foot { margin-top: 22px; padding-top: 8px; border-top: 1px solid #e5e7eb; font-size: 10px; color: #4b5563; display: flex; justify-content: space-between; }
  .badge { display: inline-block; background: #fef3c7; border: 1px solid #fcd34d; color: #92400e; font-size: 9px; padding: 1px 6px; border-radius: 99px; }
`

function reportHeader(config, title, subtitle, logo) {
  // Prefer the inlined data URI (printLogo): inside the Electron print
  // window a plain remote logo_url can fail to load and renders as a broken
  // image placeholder.
  const logoSrc = logo || config?.logo_url || config?.logo
  return `
    <div class="head">
      ${logoSrc ? `<img src="${esc(logoSrc)}" alt="" onerror="this.remove()" />` : ''}
      <div>
        <div class="school">${esc(config?.school_name || 'School Management System')}</div>
        <div class="addr">${esc(config?.full_address || '')}${config?.contact_info ? ` · ${esc(config.contact_info)}` : ''}</div>
      </div>
    </div>
    <h1>${esc(title)}</h1>
    <div class="meta">${esc(subtitle)}</div>`
}

function reportFooter(preparedBy, generatedAt) {
  return `<div class="foot">
    <div>Prepared by: <strong>${esc(preparedBy || 'Administrator')}</strong></div>
    <div>Generated ${esc(generatedAt)} · School Management System</div>
  </div>`
}

/**
 * Overall report: grand totals card row + (optionally) the Revenue by
 * Terminal table + (optionally) the full transaction line-items.
 * The terminal table lives on the Staff Revenue page; pass
 * includeTerminals: false for the plain revenue report.
 */
export function buildRevenueReportHtml({ config, logo, dateRangeText, totals, byTerminal = [], includeTerminals = true, rows = [], preparedBy, generatedAt, terminalCount }) {
  const cards = [
    ['Total Revenue', totals?.total_revenue],
    ['POS', totals?.total_pos],
    ['Tuition', totals?.total_tuition],
    ['Transactions', totals?.total_transactions],
  ]
    .map(([k, v]) => `<div class="card"><div class="k">${esc(k)}</div><div class="v">${esc(k === 'Transactions' ? Number(v || 0) : peso(v))}</div></div>`)
    .join('')

  const showTerminals = includeTerminals
  const terminalRows = byTerminal.length
    ? byTerminal
        .map(
          (t) => `<tr>
            <td>${esc(t.terminal_name)}</td>
            <td>${esc((t.staff_names || []).join(', ') || '—')}</td>
            <td class="num">${esc(peso(t.pos))}</td>
            <td class="num">${esc(peso(t.tuition))}</td>
            <td class="num">${esc(peso(t.total))}</td>
            <td class="num">${esc(Number(t.transactions || 0))}</td>
          </tr>`
        )
        .join('')
    : `<tr><td colspan="6" style="text-align:center;color:#6b7280;">No terminal-attributed transactions in this period.</td></tr>`

  const transactionRows = rows.length
    ? rows
        .map(
          (r) => `<tr>
            <td>${esc(r.reference || '—')}</td>
            <td>${esc(new Date(r.date).toLocaleString('en-PH'))}</td>
            <td>${esc(r.type || '')}</td>
            <td>${esc(r.customer || '')}</td>
            <td>${esc(r.terminal || 'Unassigned')}</td>
            <td>${esc((r.products || []).map((p) => `${p.name}${p.quantity > 1 ? ` x${p.quantity}` : ''}`).join('; '))}</td>
            <td class="num">${esc(peso(r.amount))}</td>
          </tr>`
        )
        .join('')
    : ''

  return `<!doctype html>
<html><head><meta charset="utf-8" /><title>Revenue Report</title><style>${REPORT_CSS}</style></head>
<body>
  ${reportHeader(config, 'Revenue Report', dateRangeText, logo)}
  <div class="cards">${cards}</div>
  ${showTerminals ? `
  <h2>Revenue by Terminal${terminalCount ? ` (${terminalCount})` : ''}</h2>
  <table>
    <thead><tr><th>Terminal</th><th>Staff</th><th class="num">POS</th><th class="num">Tuition</th><th class="num">Total</th><th class="num">Txns</th></tr></thead>
    <tbody>${terminalRows}</tbody>
  </table>` : ''}
  ${rows.length ? `
  <h2>Transactions (${rows.length})</h2>
  <table>
    <thead><tr><th>OR / Ref</th><th>Date</th><th>Type</th><th>Customer</th><th>Terminal</th><th>Items</th><th class="num">Amount</th></tr></thead>
    <tbody>${transactionRows}</tbody>
  </table>` : ''}
  ${reportFooter(preparedBy, generatedAt)}
</body></html>`
}

/**
 * Per-terminal report: that terminal's totals plus its full transaction
 * line-items (POS + tuition) for the filtered period.
 */
export function buildTerminalReportHtml({ config, logo, terminal, dateRangeText, rows = [], preparedBy, generatedAt }) {
  const cards = [
    ['POS', terminal?.pos],
    ['Tuition', terminal?.tuition],
    ['Total', terminal?.total],
    ['Transactions', terminal?.transactions],
  ]
    .map(([k, v]) => `<div class="card"><div class="k">${esc(k)}</div><div class="v">${esc(k === 'Transactions' ? Number(v || 0) : peso(v))}</div></div>`)
    .join('')

  const lineRows = rows.length
    ? rows
        .map(
          (r) => `<tr>
            <td>${esc(r.reference || '—')}</td>
            <td>${esc(new Date(r.date).toLocaleString('en-PH'))}</td>
            <td>${esc(r.type || '')}</td>
            <td>${esc(r.customer || '')}</td>
            <td>${esc((r.products || []).map((p) => `${p.name}${p.quantity > 1 ? ` x${p.quantity}` : ''}`).join('; '))}</td>
            <td class="num">${esc(peso(r.amount))}</td>
          </tr>`
        )
        .join('')
    : `<tr><td colspan="6" style="text-align:center;color:#6b7280;">No transactions recorded for this terminal in this period.</td></tr>`

  const staff = (terminal?.staff_names || []).join(', ')

  return `<!doctype html>
<html><head><meta charset="utf-8" /><title>Revenue Report — ${esc(terminal?.terminal_name || 'Terminal')}</title><style>${REPORT_CSS}</style></head>
<body>
  ${reportHeader(
    config,
    `Revenue Report — ${terminal?.terminal_name || 'Terminal'}`,
    `${dateRangeText}${staff ? ` · Staff: ${staff}` : ''}`,
    logo
  )}
  <div class="cards">${cards}</div>
  <h2>Transactions</h2>
  <table>
    <thead><tr><th>OR / Ref</th><th>Date</th><th>Type</th><th>Customer</th><th>Items</th><th class="num">Amount</th></tr></thead>
    <tbody>${lineRows}</tbody>
  </table>
  ${reportFooter(preparedBy, generatedAt)}
</body></html>`
}

/**
 * Daily Collection & Disbursement Report — the cashier's printed end-of-day
 * sheet. Mirrors the school's Excel original: collections table, LESS:
 * DISBURSEMENT block, NET AMOUNT, highlighted CASH ON HAND, denominations
 * box on the right, signature lines at the bottom.
 */
export function buildDailyCashReportHtml({ config, logo, report, preparedBy, checkedBy }) {
  const pesoPlain = (n) =>
    Number(n || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  const rows = report?.collections || []
  const disbs = report?.disbursements || []
  const denoms = report?.denominations || {}

  const collectRows = rows.length
    ? rows
        .map(
          (r) => `<tr>
            <td>${esc(r.description)}</td>
            <td class="num">${esc(r.count ?? 1)}</td>
            <td class="num">${esc(pesoPlain(r.amount))}</td>
          </tr>`
        )
        .join('')
    : `<tr><td colspan="3" style="text-align:center;color:#6b7280;">No collections in this period.</td></tr>`

  const disbRows = disbs.length
    ? disbs
        .map(
          (d) => `<tr>
            <td>${esc(d.description)}</td>
            <td class="num">${esc(d.count ?? 1)}</td>
            <td class="num">${esc(pesoPlain(d.amount))}</td>
          </tr>`
        )
        .join('')
    : `<tr><td colspan="3" style="text-align:center;color:#6b7280;">None</td></tr>`

  const denomDefs = [
    ['1000', '1000'], ['500', '500'], ['200', '200'],
    ['100', '100'], ['50', '50'], ['20', '20'], ['coins', 'coins'],
  ]
  const denomRows = denomDefs
    .map(([key, label]) => {
      const qty = denoms[key]
      const amount = key === 'coins'
        ? Number(qty || 0)
        : Number(qty || 0) * Number(key)
      const shown = qty ? pesoPlain(amount) : '—'
      return `<tr><td>${esc(label)}</td><td class="num">${esc(key === 'coins' ? '' : (qty || ''))}</td><td class="num">${esc(shown)}</td></tr>`
    })
    .join('')

  return `<!doctype html>
<html><head><meta charset="utf-8" /><title>Daily Collection & Disbursement Report</title><style>
  ${REPORT_CSS}
  .layout { display: flex; gap: 14px; align-items: flex-start; }
  .layout .left { flex: 1.6; }
  .layout .right { flex: 1; min-width: 190px; }
  .total-row td { font-weight: 700; background: #f9fafb; }
  .net-row td { font-weight: 700; }
  .coh td { font-weight: 800; background: #fef9c3; font-size: 12px; }
  .signatures { margin-top: 34px; display: flex; justify-content: space-between; gap: 24px; font-size: 11px; }
  .signatures .line { display: inline-block; min-width: 180px; border-bottom: 1px solid #111827; }
  .signatures .name { font-weight: 700; }
</style></head>
<body>
  ${reportHeader(config, 'DAILY COLLECTION & DISBURSEMENT REPORT', new Date(report?.date).toLocaleDateString('en-PH', { year: 'numeric', month: 'long', day: 'numeric' }), logo)}
  <div class="layout">
    <div class="left">
      <table>
        <thead><tr><th>COLLECTIONS:</th><th class="num" style="width:10%;">QTY</th><th class="num" style="width:26%;">AMOUNT</th></tr></thead>
        <tbody>${collectRows}</tbody>
        <tfoot><tr class="total-row"><td colspan="2">TOTAL COLLECTION</td><td class="num">${esc(pesoPlain(report?.total_collection))}</td></tr></tfoot>
      </table>
      <table style="margin-top:12px;">
        <thead><tr><th>LESS: DISBURSEMENT</th><th class="num" style="width:10%;">QTY</th><th class="num" style="width:26%;">AMOUNT</th></tr></thead>
        <tbody>${disbRows}</tbody>
        <tfoot>
          <tr class="net-row"><td colspan="2">NET AMOUNT</td><td class="num">${esc(pesoPlain(report?.net_amount))}</td></tr>
          <tr class="coh"><td colspan="2">CASH ON HAND</td><td class="num">Php&nbsp;&nbsp;${esc(pesoPlain(report?.net_amount))}</td></tr>
        </tfoot>
      </table>
    </div>
    <div class="right">
      <table>
        <thead><tr><th>Denominations</th><th>Qty</th><th class="num">Amount</th></tr></thead>
        <tbody>${denomRows}</tbody>
        <tfoot><tr class="total-row"><td colspan="2">Total</td><td class="num">${esc(pesoPlain(report?.counted_total))}</td></tr></tfoot>
      </table>
      ${Number(report?.difference || 0) !== 0
        ? `<div style="margin-top:6px;font-size:10px;color:#92400e;background:#fef3c7;border:1px solid #fcd34d;border-radius:6px;padding:5px 7px;">
             Difference vs NET: ${esc(pesoPlain(report?.difference))}
           </div>`
        : ''}
    </div>
  </div>
  <div class="signatures">
    <div>
      <div>Prepared by: <span class="name">${esc(preparedBy || '')}</span></div>
      <div style="margin-top:14px;">Checked by: <span class="name">${esc(checkedBy || '')}</span></div>
    </div>
    <div>
      <div>Received/Approved by: <span class="line">&nbsp;</span></div>
      <div style="margin-top:22px;">Date: <span class="line">&nbsp;</span></div>
    </div>
  </div>
</body></html>`
}
