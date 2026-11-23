import { forwardRef } from 'react'

export const receiptPeso = (n) =>
  `₱${Number(n || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

/** 80mm thermal paper styles. Shared so every receipt prints identically. */
export const RECEIPT_PAGE_STYLE = `
  @page { size: 80mm auto; margin: 4mm; }
  html, body { background: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .receipt-paper { box-shadow: none !important; border: none !important; margin: 0 !important; width: 100% !important; max-width: none !important; }
`

function Row({ label, value, mono, small }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-gray-500 shrink-0">{label}</span>
      <span className={`text-gray-900 text-right ${mono ? 'font-mono' : ''} ${small ? 'text-[10px]' : 'text-[11px] font-medium'}`}>
        {value}
      </span>
    </div>
  )
}

/**
 * The printable 80mm receipt. Attach the ref to whatever container should be
 * handed to useReactToPrint.
 *
 * receipt: {
 *   receiptNumber, timestamp, cashierName, terminalId,
 *   student: { first_name, last_name, lrn } | null,
 *   payerName, lines: [{ name, size, qty, unit, amount }],
 *   total, method, reference, tendered, change
 * }
 */
const ReceiptPaper = forwardRef(function ReceiptPaper(
  { receipt, config, printLogo },
  ref
) {
  if (!receipt) return null

  return (
    <div
      ref={ref}
      className="p-6 receipt-paper"
      style={{ width: '80mm', maxWidth: '100%', margin: '0 auto' }}
    >
      <div className="text-center mb-4 pb-3 border-b border-dashed border-gray-300">
        {printLogo && (
          <img src={printLogo} alt="" className="w-12 h-12 object-contain mx-auto mb-2" />
        )}
        <p className="font-bold text-xs uppercase leading-tight">
          {config?.school_name || 'School Management System'}
        </p>
        <p className="text-[9px] text-gray-600">{config?.full_address || ''}</p>
        {config?.contact_info && (
          <p className="text-[9px] text-gray-600">{config.contact_info}</p>
        )}
        <p className="font-bold text-xs mt-2 whitespace-pre-line">
          {config?.receipt_header_text?.trim() || 'OFFICIAL RECEIPT'}
        </p>
      </div>

      <div className="space-y-1 text-[11px] mb-3">
        <Row label="Receipt No." value={receipt.receiptNumber} mono />
        <Row label="Date" value={new Date(receipt.timestamp).toLocaleString('en-PH')} />
        {receipt.cashierName && (
          <Row
            label="Cashier"
            value={receipt.terminalId ? `${receipt.cashierName} (${receipt.terminalId})` : receipt.cashierName}
          />
        )}
        {receipt.student ? (
          <Row label="Student" value={`${receipt.student.first_name} ${receipt.student.last_name}`} />
        ) : (
          <Row label="Payer" value={receipt.payerName || 'Walk-in Customer'} />
        )}
        {receipt.student?.lrn && <Row label="LRN" value={receipt.student.lrn} mono />}
      </div>

      <div className="border-t border-dashed border-gray-300 pt-2 mb-2">
        <p className="text-[10px] font-bold uppercase text-gray-500 mb-1">Items</p>
        {(receipt.lines || []).map((l, i) => (
          <div key={i} className="flex justify-between gap-2 py-1 text-[11px]">
            <span className="min-w-0">
              {l.name}
              {l.size && <span className="text-gray-500"> ({l.size})</span>}{' '}
              <span className="text-gray-400">x{l.qty}</span>
            </span>
            <span className="font-mono shrink-0">{receiptPeso(l.amount)}</span>
          </div>
        ))}
      </div>

      <div className="border-t border-dashed border-gray-300 pt-2 space-y-1">
        <div className="flex justify-between text-[12px] font-bold">
          <span>TOTAL</span>
          <span className="font-mono">{receiptPeso(receipt.total)}</span>
        </div>
        <Row
          label="Method"
          value={receipt.method + (receipt.reference ? ` (${receipt.reference})` : '')}
          small
        />
        {receipt.method === 'Cash' && (
          <>
            <Row label="Tendered" value={receiptPeso(receipt.tendered)} small />
            <Row label="Change" value={receiptPeso(receipt.change)} small />
          </>
        )}
      </div>

      {config?.receipt_footer_text?.trim() ? (
        <p className="text-center text-[9px] text-gray-600 mt-4 pt-3 border-t border-dashed border-gray-300 whitespace-pre-line">
          {config.receipt_footer_text}
        </p>
      ) : (
        <p className="text-center text-[9px] text-gray-500 mt-4 pt-3 border-t border-dashed border-gray-300">
          Thank you for your payment!
          <br />
          This is a computer-generated receipt.
        </p>
      )}
    </div>
  )
})

export default ReceiptPaper