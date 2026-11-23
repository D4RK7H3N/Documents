import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useReactToPrint } from 'react-to-print'
import PageHeader from '../components/PageHeader'
import ActionButton from '../components/ActionButton'
import PesoSign from '../components/PesoSign'
import StatusBadge from '../components/StatusBadge'
import {
  Search, Receipt, CreditCard, Banknote, Loader2, Printer, X, AlertCircle,
  Check, User, Users, Plus, Minus, Wallet, RotateCcw, Download, Mail, Info,
} from 'lucide-react'
import apiClient, { financeAPI, studentsAPI, chargeAPI, productAPI, salesAPI } from '../services/api'
import ReceiptPaper, { RECEIPT_PAGE_STYLE } from '../components/ReceiptPaper'
import { useSchoolConfig } from '../contexts/SchoolConfigContext'
import { storage } from '../services/storage'
import { staffName } from '../utils/staffName'

const peso = (n) => `₱${Number(n || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const pesoShort = (n) => `₱${Number(n || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

const DENOMS = [50, 100, 200, 500, 1000, 5000]
const METHODS = [
  { id: 'Cash', label: 'Cash', icon: Wallet },
  { id: 'GCash', label: 'GCash', icon: CreditCard },
  { id: 'Bank Transfer', label: 'Bank Transfer', icon: Banknote },
]

const PAYMENT_TYPES = ['Tuition', 'Miscellaneous', 'Laboratory', 'Assessment', 'Dorm', 'Tour', 'Graduation']

const CATEGORIES = [
  { id: 'all', label: 'All Items' },
  { id: 'tuition', label: 'Tuition Payment' },
  { id: 'academic', label: 'Academic Fees' },
  { id: 'products', label: 'Products & Supplies' },
]

export default function CashierPage() {
  const { config, printLogo } = useSchoolConfig()

  // ---- terminal / mode -------------------------------------------------
  const [mode, setMode] = useState('student')       // student | walkin
  const [activeTab, setActiveTab] = useState('checkout') // checkout | tuition | history

  // ---- student context -------------------------------------------------
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [context, setContext] = useState(null)     // settlement_context payload
  const [ctxLoading, setCtxLoading] = useState(false)

  // ---- payable items ---------------------------------------------------
  const [products, setProducts] = useState([])
  const [category, setCategory] = useState('all')
  const [selected, setSelected] = useState({})     // key -> { kind, id, name, unit, qty }
  const [method, setMethod] = useState('Cash')
  const [reference, setReference] = useState('')

  // ---- modals ---------------------------------------------------------
  const [showPayModal, setShowPayModal] = useState(false)
  const [split, setSplit] = useState('full')        // full | half | other
  const [customAmount, setCustomAmount] = useState('')
  const [tendered, setTendered] = useState('')
  const [processing, setProcessing] = useState(false)
  const [showReceipt, setShowReceipt] = useState(false)
  const [receipt, setReceipt] = useState(null)
  const [toast, setToast] = useState(null)
  const [transactions, setTransactions] = useState([])

  const searchRef = useRef(null)
  const receiptRef = useRef(null)
  const [receiptCounter, setReceiptCounter] = useState(() => Number(storage.getSync('cashierReceiptCounter') || 1))

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  const printReceipt = useReactToPrint({
    contentRef: receiptRef,
    documentTitle: 'Official Receipt',
    pageStyle: RECEIPT_PAGE_STYLE,
  })

  // ---- data ------------------------------------------------------------
  const loadProducts = useCallback(async () => {
    try {
      const data = await productAPI.getAll()
      setProducts(Array.isArray(data) ? data : data.results || [])
    } catch {
      setProducts([])
    }
  }, [])

  // Scoped to one student. The ledger endpoint merges payments, product sales
// and tuition for that account, so a student's uniforms and tuition appear
// alongside their other payments instead of the tab listing every student in
// the school.
const loadTransactions = useCallback(async (forStudentId) => {
  const sid = forStudentId ?? context?.student?.id
  if (!sid) {
    setTransactions([])
    return
  }
  try {
    const data = await financeAPI.getLedger(sid)
    setTransactions(Array.isArray(data) ? data : data.transactions || [])
  } catch {
    setTransactions([])
  }
}, [context])

  useEffect(() => { loadProducts(); loadTransactions() }, [loadProducts, loadTransactions])

  // Student search: name OR 12-digit LRN
  useEffect(() => {
    const term = query.trim()
    if (term.length < 2) { setSearchResults([]); return }
    const t = setTimeout(async () => {
      setSearching(true)
      try {
        const data = await studentsAPI.getAll({ search: term, include_inactive: true })
        const list = Array.isArray(data) ? data : data.results || []
        setSearchResults(list.slice(0, 12))
        setShowResults(true)
      } catch {
        setSearchResults([])
      } finally {
        setSearching(false)
      }
    }, 250)
    return () => clearTimeout(t)
  }, [query])

  const selectStudent = async (student) => {
    setShowResults(false)
    setQuery(student.lrn || `${student.first_name} ${student.last_name}`)
    setCtxLoading(true)
    setSelected({})
    try {
      const ctx = await studentsAPI.settlementContext(student.id)
      setContext(ctx)
    } catch (err) {
      showToast('Failed to load student account', 'error')
    } finally {
      setCtxLoading(false)
    }
  }

  // ---- item selection --------------------------------------------------
  // Academic items come from the student's unpaid charges; supplies come from
  // inventory filtered on the Product category the admin sets.
  const charges = context?.unpaid_charges || []
  const supplies = useMemo(
    () => products.filter(p => (p.category || 'products') === 'products'),
    [products]
  )
  const academicProducts = useMemo(
    () => products.filter(p => p.category === 'academic'),
    [products]
  )

  const itemRows = useMemo(() => {
    const rows = []
    if (category === 'all' || category === 'academic' || category === 'tuition') {
      // Tuition is a payable item in its own right, not just a figure in the
      // summary. It is settled through the tuition endpoint rather than the
      // charge pay action, so it is flagged with kind 'tuition'.
      const tuition = Number(context?.totals?.tuition_balance || 0)
      const tuitionStudentId = context?.student?.id
      if (tuition > 0 && tuitionStudentId) {
        rows.push({
          key: 'tuition', kind: 'tuition', id: tuitionStudentId,
          name: 'Tuition', description: 'Outstanding tuition balance',
          unit: tuition, qty: 1, balance: tuition, locked: true,
        })
      }
      if (category !== 'tuition') {
        charges.forEach(c => rows.push({
          key: `charge-${c.id}`, kind: 'charge', id: c.id,
          name: c.item_name, description: c.description,
          unit: c.unit_price, qty: c.qty, balance: c.balance, locked: true,
        }))
                        academicProducts.forEach(p => rows.push({
          key: `product-${p.id}`, kind: 'product', id: p.id,
          name: p.name, description: '',
          unit: Number(p.price || 0), qty: 1, balance: Number(p.price || 0),
          stock: p.stock, locked: false, academic: true,
          is_sized: !!p.is_sized, variants: p.variants || [],
        }))
      }
    }
    if (category === 'all' || category === 'products') {
      supplies.forEach(p => rows.push({
        key: `product-${p.id}`, kind: 'product', id: p.id,
        name: p.name, description: '',
        unit: Number(p.price || 0), qty: 1, balance: Number(p.price || 0),
        stock: p.stock, locked: false,
        is_sized: !!p.is_sized, variants: p.variants || [],
      }))
    }
    return rows
  }, [category, charges, supplies, academicProducts, context])

  const toggleItem = (row) => {
    setSelected(prev => {
      const next = { ...prev }
      if (next[row.key]) delete next[row.key]
      // Sized items need a size chosen before they can be added.
      else if (row.is_sized) {
        const first = (row.variants || []).find(v => (v.stock == null || v.stock > 0))
        if (!first) return prev
        next[row.key] = { ...row, qty: 1, variantId: first.id, size: first.size, unit: Number(first.effective_price ?? row.unit) }
      } else {
        next[row.key] = { ...row, qty: row.qty || 1 }
      }
      return next
    })
  }

  const setSize = (key, variant) => {
    setSelected(prev => {
      const cur = prev[key]
      if (!cur) return prev
      return {
        ...prev,
        [key]: { ...cur, variantId: variant.id, size: variant.size, unit: Number(variant.effective_price ?? cur.unit) },
      }
    })
  }

  const setQty = (key, delta) => {
    setSelected(prev => {
      const cur = prev[key]
      if (!cur) return prev
      const qty = Math.max(1, (cur.qty || 1) + delta)
      return { ...prev, [key]: { ...cur, qty } }
    })
  }

  const selectedList = Object.values(selected)
  const totalSelected = selectedList.reduce((sum, it) => {
    if (it.kind === 'charge') {
      const cap = it.balance
      const want = Number(it.unit || 0) * (it.qty || 1)
      return sum + Math.min(cap, want)
    }
    return sum + Number(it.unit || 0) * (it.qty || 1)
  }, 0)

  const itemCount = selectedList.length

  // ---- payment details -------------------------------------------------
  const collectingNow = useMemo(() => {
    if (split === 'full') return totalSelected
    // Never collect more than the amount due - the backend rejects any
    // settlement above a charge's remaining balance with a 400.
    if (split === 'half') return Math.round(totalSelected / 2)
    return Math.min(Math.max(0, parseFloat(customAmount) || 0), totalSelected)
  }, [split, totalSelected, customAmount])

  const change = useMemo(() => {
    const t = parseFloat(tendered) || 0
    return Math.max(0, t - collectingNow)
  }, [tendered, collectingNow])

  const tenderedValid = method !== 'Cash' || (parseFloat(tendered) || 0) >= collectingNow
  const referenceRequired = method === 'GCash' || method === 'Bank Transfer'
  const canConfirm = collectingNow > 0 && tenderedValid && (!referenceRequired || reference.trim())

  const openPayModal = () => {
    if (!itemCount) return
    setSplit('full'); setCustomAmount(''); setTendered('')
    setShowPayModal(true)
  }

  // ---- commit ----------------------------------------------------------
  const nextReceiptNo = () => {
    const n = receiptCounter
    const next = n + 1
    setReceiptCounter(next)
    storage.set('cashierReceiptCounter', String(next))
    const d = new Date()
    const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
    return `OR-${stamp}-${String(n).padStart(5, '0')}`
  }

  const processPayment = async () => {
    if (!canConfirm || processing) return
    setProcessing(true)
    const receiptNo = nextReceiptNo()
    try {
      const studentId = mode === 'student' ? context?.student?.id : null
      const payerName = mode === 'walkin' ? (selectedList[0]?.payerName || 'Walk-in Customer') : null
      const lines = []

      // 1. Settle each selected charge
      for (const item of selectedList.filter(i => i.kind === 'charge' || i.kind === 'tuition')) {
        const cap = item.balance
        const want = Number(item.unit || 0) * (item.qty || 1)
        const amount = Math.min(cap, want)
        // Split the collection proportionally, but never above a charge's
        // own remaining balance (the API rejects that with a 400).
        const share = itemCount === 1
          ? Math.min(cap, collectingNow)
          : Math.min(cap, collectingNow * (amount / totalSelected))
        if (share <= 0) continue

        if (item.kind === 'tuition') {
          // Tuition lives on Student.tuition_balance, not on a charge row, so
          // it is settled through the tuition endpoint. That endpoint takes the
          // running total the account should be brought up to (not the amount
          // taken now) and works out the difference itself.
          const fee = Number(context?.totals?.tuition_fee || 0)
          const paidSoFar = Number(context?.totals?.tuition_paid || 0)
          await financeAPI.createTuition({
            student_id: studentId,
            school_year: config?.current_academic_year || '',
            total_tuition: fee,
            amount_paid: paidSoFar + share,
            payment_date: new Date().toISOString().split('T')[0],
            payment_method: method.toLowerCase().replace(' ', '_'),
            notes: `Cashier collection (${method})`,
          })
        } else {
          await chargeAPI.pay(item.id, {
            amount: Number(share.toFixed(2)),
            payment_method: method,
            reference_number: reference.trim() || undefined,
          })
        }
        lines.push({
          kind: item.kind, name: item.name, qty: item.qty || 1,
          unit: Number(item.unit || 0), amount: Number(share.toFixed(2)),
        })
      }

      // 2. Record products as a Sale so stock and revenue stay consistent
      const productLines = selectedList.filter(i => i.kind === 'product')
      let collected = lines.reduce((s, l) => s + l.amount, 0)
      if (productLines.length && collectingNow > collected) {
        const prodTotal = productLines.reduce((s, i) => s + Number(i.unit) * i.qty, 0)
        const factor = prodTotal > 0 ? (collectingNow - collected) / prodTotal : 0
        // Remember what each line actually collected, so the saved sale line
        // can record the price charged rather than the list price.
        const charged = []
        productLines.forEach(i => {
          const full = Number(i.unit) * i.qty
          const amt = Number((full * factor).toFixed(2))
          collected += amt
          charged.push(amt)
          lines.push({ kind: 'product', name: i.name, qty: i.qty, unit: Number(i.unit), amount: amt, size: i.size || null })
        })
        // Record the sale so stock/revenue stay in step. The charge payments
        // above already succeeded, so a failure here must not be silent -
        // otherwise stock quietly drifts and the cashier sees a clean receipt.
        try {
          await salesAPI.create({
            student: studentId,
            customer_name: mode === 'walkin' ? 'Walk-in Customer' : undefined,
            // The OR number is minted here in the browser, so it has to be
            // sent across or Revenue records the sale with no reference.
            receipt_number: receiptNo,
            items: productLines.map((i, idx) => ({
              product_id: i.id,
              quantity: i.qty,
              // A half payment must read as half at line level too. Sending
              // the list price left every partial sale looking like a full
              // one to anything that sums line subtotals, because the stored
              // subtotal (price x qty) ignored what was actually collected.
              price: i.qty > 0
                ? Number((charged[idx] / i.qty).toFixed(2))
                : Number(i.unit),
              variant: i.variantId || null,
              size: i.size || null,
            })),
            total: Number(collected.toFixed(2)),
            amount_paid: Number(collected.toFixed(2)),
            payment_method: method,
          })
        } catch (saleErr) {
          const msg = saleErr?.response?.data
          const detail = typeof msg === 'string' ? msg
            : Array.isArray(msg) ? msg.map(e => (typeof e === 'string' ? e : JSON.stringify(e))).join(' ')
            : (saleErr?.message || 'unknown error')
          showToast(`Payment recorded, but the product sale was not saved (stock not updated): ${detail}`, 'error')
        }

        // 3. Record what is still owed on any partly-paid product, so the
        // remainder reaches Pending Payments. Without this the unpaid half of
        // a uniform was simply gone: the Sale only ever held what was taken,
        // and no charge existed for the rest, so the student looked settled.
        // Walk-ins have no account to attach a balance to, so this is
        // students only.
        if (mode === 'student' && studentId) {
          for (let idx = 0; idx < productLines.length; idx++) {
            const i = productLines[idx]
            const full = Number(i.unit) * i.qty
            const owed = full - charged[idx]
            if (owed <= 0.009) continue
            try {
              await chargeAPI.create({
                student: studentId,
                item_name: i.size ? `${i.name} (${i.size})` : i.name,
                qty: i.qty,
                // Full list price; initial_paid is what this transaction
                // already took, so the charge opens part-settled rather than
                // double-counting the money.
                unit_price: Number(i.unit),
                initial_paid: charged[idx],
                source: 'item',
                notes: `Part-paid at cashier on ${new Date().toLocaleDateString('en-PH')}`,
              })
            } catch (chargeErr) {
              const cmsg = chargeErr?.response?.data
              const cdetail = typeof cmsg === 'string' ? cmsg
                : Array.isArray(cmsg) ? cmsg.map(e => (typeof e === 'string' ? e : JSON.stringify(e))).join(' ')
                : (chargeErr?.message || 'unknown error')
              showToast(`Payment recorded, but the remaining balance for ${i.name} was not saved and will not appear in Pending Payments: ${cdetail}`, 'error')
            }
          }
        }
      }

      const r = {
        receiptNumber: receiptNo,
        timestamp: new Date().toISOString(),
        // Printed documents carry the staff profile name, not the login username.
        cashierName: staffName(),
        terminalId: 'Terminal 01',
        student: context?.student || null,
        payerName,
        mode,
        lines,
        tendered: parseFloat(tendered) || 0,
        change,
        method,
        reference: reference.trim(),
        total: collected,
      }

      setReceipt(r)
      setShowPayModal(false)
      setShowReceipt(true)
      // refresh the account so balances move live behind the receipt
      if (studentId) {
        try { setContext(await studentsAPI.settlementContext(studentId)) } catch { /* non-fatal */ }
      }
      loadTransactions()
    } catch (err) {
      showToast(err?.response?.data?.error || err?.response?.data?.detail || 'Payment failed', 'error')
    } finally {
      setProcessing(false)
    }
  }

  // ---- terminal reset --------------------------------------------------
  const resetTerminal = useCallback(() => {
    setShowPayModal(false)
    setShowReceipt(false)
    setContext(null)
    setQuery('')
    setSearchResults([])
    setShowResults(false)
    setSelected({})
    setCategory('all')
    setMethod('Cash')
    setReference('')
    setSplit('full'); setCustomAmount(''); setTendered('')
    setMode('student')
    setTimeout(() => searchRef.current?.focus(), 60)
  }, [])

  // F1 = New Transaction, F12 = quick pay
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'F1') { e.preventDefault(); resetTerminal() }
      if (e.key === 'F12' && itemCount && !showPayModal) { e.preventDefault(); openPayModal() }
      if (e.key === 'Enter' && itemCount && !showPayModal && !showResults) { e.preventDefault(); openPayModal() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  // ---- receipt actions -------------------------------------------------
  const downloadReceipt = () => {
    if (!receipt) return
    const body = [
      'OFFICIAL RECEIPT', receipt.schoolName || config?.school_name || '',
      `Receipt No: ${receipt.receiptNumber}`,
      `Date: ${new Date(receipt.timestamp).toLocaleString()}`,
      `Cashier: ${receipt.cashierName} (${receipt.terminalId})`,
      receipt.student ? `Student: ${receipt.student.first_name} ${receipt.student.last_name}` : `Payer: ${receipt.payerName}`,
      '', 'ITEMS', ...receipt.lines.map(l => `${l.name}${l.size ? ` (${l.size})` : ''} x${l.qty}  ${peso(l.amount)}`),
      '', `TOTAL: ${peso(receipt.total)}`,
      `Method: ${receipt.method}${receipt.reference ? ` (${receipt.reference})` : ''}`,
      receipt.method === 'Cash' ? `Tendered: ${peso(receipt.tendered)}  Change: ${peso(receipt.change)}` : '',
    ].filter(Boolean).join('\n')
    const blob = new Blob([body], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${receipt.receiptNumber}.txt`; a.click()
    URL.revokeObjectURL(url)
  }

  const emailReceipt = () => {
    if (!receipt) return
    // A walk-in has no address on file - mailto: with an empty `to` just
    // opens a blank compose, so send it to the cashier instead.
    const to = receipt.student?.email || ''
    if (!to) {
      showToast('No email address on file for this receipt', 'error')
      return
    }
    const subject = `Official Receipt ${receipt.receiptNumber}`
    const itemText = receipt.lines
      .map(l => `- ${l.name}${l.size ? ` (${l.size})` : ''} x${l.qty}: ${peso(l.amount)}`)
      .join('\n')
    const body = [
      `Receipt No: ${receipt.receiptNumber}`,
      `Date: ${new Date(receipt.timestamp).toLocaleString('en-PH')}`,
      `Student: ${receipt.student ? `${receipt.student.first_name} ${receipt.student.last_name}` : receipt.payerName || 'Walk-in Customer'}`,
      '', 'Items:', itemText,
      '', `Total: ${peso(receipt.total)}`,
      `Method: ${receipt.method}${receipt.reference ? ` (${receipt.reference})` : ''}`,
      receipt.method === 'Cash' ? `Tendered: ${peso(receipt.tendered)}  Change: ${peso(receipt.change)}` : '',
      '', 'Thank you for your payment!',
    ].filter(Boolean).join('\n')
    window.location.href = `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
  }

  const st = context?.student
  const totals = context?.totals || {}
  // Outstanding, split so the cashier (and the student at the counter) can
  // see what the figure is made of. "Other" is everything that is not
  // tuition: products, uniforms and academic fees held as StudentCharge.
  const tuitionDue = Number(totals.tuition_balance || 0)
  const otherDue = Number(totals.item_total || 0)
  // Student.status is the real account state. enrollment_status is a legacy
  // string that bulk promotion leaves as 'Graduated' without any graduation
  // record, so showing it next to the status produced a contradictory
  // "Graduated (Active)" badge on students who were plainly still active.
  // Anyone owing must be settleable here, including Drop-out / Inactive /
  // Transferred students, so the search looks at the full roster. The
  // cashier only cares whether the account can transact, so every
  // non-Active status reads as "Inactive" rather than its raw label.
  const accountStatus = st?.status ? (st.status === 'Active' ? 'Active' : 'Inactive') : 'Active'
  const guardianLine = st?.guardian_name
    ? `${st.guardian_name}${st.guardian_relationship ? ` (${st.guardian_relationship})` : ''}`
    : '—'

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ---------------- top bar ---------------- */}
      <div className="bg-white border-b border-gray-200">
        <div className="px-6 py-4 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center">
              <CreditCard size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-gray-900">Quick Payment</h1>
                <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Terminal 01
                </span>
              </div>
              <p className="text-xs text-gray-500">
                Cashier Counter · Academic Year {config?.current_academic_year || '—'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="inline-flex rounded-xl border border-gray-200 bg-gray-50 p-1">
              <button onClick={() => setMode('student')}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors inline-flex items-center gap-2 ${mode === 'student' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}>
                <User size={14} /> Student
              </button>
              <button onClick={() => setMode('walkin')}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors inline-flex items-center gap-2 ${mode === 'walkin' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}>
                <Users size={14} /> Walk-in
              </button>
            </div>
            <ActionButton variant="secondary" size="sm" onClick={resetTerminal} icon={RotateCcw}>
              New Transaction
              <kbd className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded border border-gray-300 bg-gray-100 text-gray-500 font-mono">F1</kbd>
            </ActionButton>
          </div>
        </div>

        <div className="px-6 flex gap-1 border-t border-gray-100">
          {[['checkout', 'Checkout'], ['tuition', 'Tuition Payment'], ['history', 'Transaction History']].map(([id, label]) => (
            <button key={id} onClick={() => { setActiveTab(id); if (id === 'tuition') loadTransactions() }}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${activeTab === id ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'checkout' ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 divide-x divide-gray-200">
          {/* ---------------- left: student context ---------------- */}
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-2">Student / LRN</label>
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  id="student-search"
                  ref={searchRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onFocus={() => searchResults.length && setShowResults(true)}
                  placeholder="Search name or 12-digit LRN"
                  className="w-full pl-9 pr-9 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {query && (
                  <button onClick={() => { setQuery(''); setContext(null) }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                    <X size={15} />
                  </button>
                )}
                {searching && <Loader2 size={15} className="absolute right-9 top-1/2 -translate-y-1/2 animate-spin text-gray-400" />}
              </div>
              <p className="text-xs text-gray-400 mt-1.5 flex items-center gap-1.5">
                <Info size={12} /> Search by student full name or 12-digit Learner Reference Number (LRN)
              </p>

              {showResults && searchResults.length > 0 && (
                <div className="mt-2 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden max-h-64 overflow-y-auto">
                  {searchResults.map(s => (
                    <button key={s.id} onClick={() => selectStudent(s)}
                      className="w-full px-4 py-2.5 text-left hover:bg-blue-50 flex items-center justify-between gap-3 border-b border-gray-50 last:border-0">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">{s.first_name} {s.last_name}</p>
                        <p className="text-xs text-gray-400">{s.lrn} · {s.section || 'No section'}</p>
                      </div>
                      {/* Drop-out / Transferred read as "Inactive" in the
                          cashier - same normalization as the student card. */}
                      <StatusBadge status={(s.status === 'Active' ? 'active' : 'inactive')} />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {ctxLoading && (
              <div className="py-10 flex justify-center"><Loader2 className="animate-spin text-blue-600" /></div>
            )}

            {!ctxLoading && st && (
              <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-4">
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-blue-600 text-white flex items-center justify-center text-lg font-bold shrink-0">
                    {(st.first_name?.[0] || '')}{(st.last_name?.[0] || '')}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-bold text-gray-900 truncate">{st.first_name} {st.last_name}</p>
                      <span className={`inline-flex items-center gap-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 border ${
                        accountStatus === 'Active'
                          ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                          : accountStatus === 'Inactive'
                            ? 'text-gray-600 bg-gray-50 border-gray-200'
                            : 'text-amber-700 bg-amber-50 border-amber-200'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          accountStatus === 'Active' ? 'bg-emerald-500'
                            : accountStatus === 'Inactive' ? 'bg-gray-400' : 'bg-amber-500'
                        }`} />
                        {accountStatus}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">LRN: {st.lrn}</p>
                    {/* grade and section as SEPARATE tags, per spec */}
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200">{st.grade || st.current_grade_level || '—'}</span>
                      <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200">Section: {st.section || '—'}</span>
                      <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-gray-100 text-gray-700 border border-gray-200">
                        {st.track_name || st.strand_name || st.track_strand || '—'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-amber-800">Current Outstanding Balance</span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300">
                      {(totals.outstanding || 0) > 0 ? 'Pending Due' : 'Settled'}
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-amber-900 mt-1">{peso(totals.outstanding)}</p>

                  {/* Split so it is clear what the figure is made of:
                      tuition, and everything else (products + academic fees). */}
                  <dl className="mt-3 pt-3 border-t border-amber-200 space-y-1.5">
                    {[
                      ['Tuition', tuitionDue],
                      ['Other (products & academic fees)', otherDue],
                    ].map(([label, value]) => (
                      <div key={label} className="flex items-center justify-between text-xs">
                        <dt className="text-amber-700">{label}</dt>
                        <dd className={`font-semibold ${value > 0 ? 'text-amber-900' : 'text-amber-400'}`}>
                          {peso(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>

                  <button onClick={() => { setActiveTab('history'); loadTransactions() }}
                    className="text-[11px] text-amber-700 underline mt-3 hover:text-amber-900">
                    View ledger
                  </button>
                </div>

                <dl className="divide-y divide-gray-100 text-sm">
                  {[
                    ['Grade Level', st.grade || st.current_grade_level || '—'],
                    ['Section', st.section || '—'],
                    ['Track & Strand', st.track_name || st.strand_name || st.track_strand || '—'],
                    ['School Year & Term', `${config?.current_academic_year || '—'}`],
                    ['Class Adviser', st.adviser || '—'],
                    ['Guardian / Parent', guardianLine],
                    ['Contact Number', st.contact_number || '—'],
                    ['Billing / Category', st.billing_category_display || st.billing_category || 'Regular'],
                    ['Last Payment Made', st.last_payment_date ? new Date(st.last_payment_date).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' }) : '—'],
                  ].map(([label, value]) => (
                    <div key={label} className="flex items-center justify-between gap-4 py-2">
                      <dt className="text-gray-500 text-xs shrink-0">{label}</dt>
                      <dd className="text-gray-800 font-medium text-right truncate">{value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}

            {!ctxLoading && !st && mode === 'student' && (
              <div className="border border-dashed border-gray-300 rounded-xl p-6 text-center text-sm text-gray-500">
                Search for a student to begin. Their account, fees and balances load automatically.
              </div>
            )}

            <div className="border border-dashed border-gray-300 rounded-xl p-4 flex items-start gap-3 text-xs text-gray-500">
              <Receipt size={16} className="shrink-0 mt-0.5" />
              <span>Official receipts are generated automatically upon successful settlement and saved to the registry.</span>
            </div>
          </div>

          {/* ---------------- right: payable items ---------------- */}
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-gray-900">Select Payable Items / Fees</h2>
                <p className="text-xs text-gray-500">Check fees to include in the current transaction receipt</p>
              </div>
              <span className="text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200">
                {itemCount} item{itemCount === 1 ? '' : 's'} selected
              </span>
            </div>

            <div className="flex gap-2 flex-wrap">
              {CATEGORIES.map(c => {
                const tuitionCount = tuitionDue > 0 ? 1 : 0
                const counts = {
                  all: charges.length + supplies.length + academicProducts.length + tuitionCount,
                  tuition: tuitionCount,
                  academic: charges.length + academicProducts.length,
                  products: supplies.length,
                }[c.id]
                return (
                  <button key={c.id} onClick={() => setCategory(c.id)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${category === c.id ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}>
                    {c.label} ({counts})
                  </button>
                )
              })}
            </div>

            {/* Tuition breakdown - what the fee is made of, per quarter.
                Shown on the Tuition Payment chip so the cashier can answer
                "why is tuition this much" without leaving the page. */}
            {category === 'tuition' && context?.tuition_breakdown && (
              <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold text-blue-800">
                    Tuition Breakdown{context.tuition_breakdown.academic_year ? ` · SY ${context.tuition_breakdown.academic_year}` : ''}
                  </p>
                  <span className="text-xs font-bold text-blue-800">{peso(context.tuition_breakdown.total)}</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 mt-2">
                  {context.tuition_breakdown.quarters.map(q => (
                    <div key={q.label} className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">{q.label}</span>
                      <span className="font-semibold text-gray-800">{peso(q.amount)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
              {itemRows.length === 0 && (
                <div className="text-center py-10 text-sm text-gray-400 border border-dashed border-gray-200 rounded-xl">
                  {category === 'products'
                    ? supplies.length
                      ? 'No supplies match this tab.'
                      : 'No supplies in inventory. Add products in Django Admin > Products, set Category to "Product & Supplies".'
                    : mode === 'student' && !st
                      ? 'Select a student to see their payable fees.'
                      : category === 'tuition'
                        ? 'No outstanding tuition for this student.'
                        : 'No academic fees due for this student.'}
                </div>
              )}
              {itemRows.map(row => {
                const isSel = !!selected[row.key]
                const lineTotal = row.kind === 'charge'
                  ? Math.min(row.balance, Number(row.unit) * (row.qty || 1))
                  : Number(row.unit) * (row.qty || 1)
                return (
                  <div key={row.key}
                    className={`border rounded-xl p-3 flex items-start gap-3 transition-colors ${isSel ? 'border-blue-300 bg-blue-50/40' : 'border-gray-200 bg-white'}`}>
                    <input type="checkbox" checked={isSel} onChange={() => toggleItem(row)}
                      disabled={row.kind === 'charge' && row.balance <= 0}
                      className="mt-1 w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-gray-900">{row.name}</span>
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${row.kind === 'product' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-blue-50 text-blue-700 border border-blue-200'}`}>
                          {row.kind === 'product' ? 'Product' : 'Fee'}
                        </span>
                        {row.kind === 'charge' && row.balance < Number(row.unit) * (row.qty || 1) && (
                          <span className="text-[10px] text-gray-400">partially paid</span>
                        )}
                      </div>
                      {row.description && <p className="text-xs text-gray-500 mt-0.5">{row.description}</p>}
                      {row.kind === 'charge' ? (
                        <p className="text-xs text-gray-400 mt-1">Balance: {peso(row.balance)}</p>
                      ) : (
                        <div className="flex flex-wrap items-center gap-2 mt-1.5">
                          <span className="text-xs text-gray-500">Qty:</span>
                          <div className="inline-flex items-center rounded-lg border border-gray-200">
                            <button onClick={() => setQty(row.key, -1)} disabled={!isSel || (selected[row.key]?.qty || 1) <= 1}
                              className="px-1.5 py-0.5 text-gray-500 hover:bg-gray-50 disabled:opacity-40"><Minus size={12} /></button>
                            <span className="px-2 text-xs font-mono">{isSel ? (selected[row.key]?.qty || 1) : row.qty}</span>
                            <button onClick={() => setQty(row.key, 1)} disabled={!isSel}
                              className="px-1.5 py-0.5 text-gray-500 hover:bg-gray-50 disabled:opacity-40"><Plus size={12} /></button>
                          </div>
                          {row.stock != null && (
                            <span className="text-[10px] text-gray-400">
                              stock {isSel && row.is_sized
                                ? (selected[row.key] && (row.variants.find(v => v.id === selected[row.key].variantId)?.stock))
                                : row.stock}
                            </span>
                          )}
                        </div>
                      )}
                      {/* Size picker - sized items only */}
                      {row.kind === 'product' && row.is_sized && (
                        <div className="flex flex-wrap items-center gap-1.5 mt-2">
                          <span className="text-[11px] text-gray-500">Size:</span>
                          {(row.variants || []).length === 0 && (
                            <span className="text-[11px] text-amber-600">no sizes set in admin</span>
                          )}
                          {(row.variants || []).map(v => {
                            const out = v.stock != null && v.stock <= 0
                            const active = isSel && selected[row.key]?.variantId === v.id
                            return (
                              <button key={v.id} type="button" disabled={out}
                                onClick={() => setSize(row.key, v)}
                                className={`px-2 py-0.5 text-[11px] font-medium rounded-md border transition-colors ${
                                  active
                                    ? 'bg-blue-600 text-white border-blue-600'
                                    : out
                                      ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed line-through'
                                      : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                                }`}
                                title={v.stock != null ? `${v.stock} in stock` : 'stock not tracked'}>
                                {v.size}
                              </button>
                            )
                          })}
                        </div>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-bold text-gray-900">{peso(lineTotal)}</p>
                      {row.kind === 'product' && <p className="text-[10px] text-gray-400">{peso(row.unit)} each</p>}
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="rounded-xl bg-gray-50 border border-gray-200 p-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Total Payable Amount</p>
                <p className="text-xs text-gray-400">Based on {itemCount} selected line item{itemCount === 1 ? '' : 's'}</p>
              </div>
              <p className="text-2xl font-bold text-blue-600">{pesoShort(totalSelected)}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Payment Method</label>
              <div className="grid grid-cols-3 gap-2">
                {METHODS.map(m => (
                  <button key={m.id} onClick={() => setMethod(m.id)}
                    className={`py-3 rounded-xl border-2 transition-colors flex flex-col items-center gap-1.5 text-sm font-medium ${method === m.id ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'}`}>
                    <m.icon size={18} /> {m.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">
                Reference Number <span className="text-gray-400 font-normal">
                  ({method === 'Cash' ? 'optional for Cash' : 'required for GCash / Bank'})
                </span>
              </label>
              <input
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="e.g. GCASH-123456 or Bank Ref #"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              onClick={openPayModal}
              disabled={!itemCount}
              className="w-full py-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold transition-colors flex items-center justify-center gap-2">
              <Receipt size={18} /> Process Payment ({pesoShort(totalSelected)})
            </button>
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Press <kbd className="px-1.5 py-0.5 rounded border border-gray-300 bg-gray-100 font-mono text-[10px]">F12</kbd> or <kbd className="px-1.5 py-0.5 rounded border border-gray-300 bg-gray-100 font-mono text-[10px]">Enter</kbd> to quick pay</span>
              <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Printer Online</span>
            </div>
          </div>
        </div>
      ) : activeTab === 'tuition' ? (
        /* ---------------- tuition payment tab ---------------- */
        <div className="p-6">
          <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <PesoSign size={16} className="text-blue-600" /> Tuition Payment
                </h2>
                {context?.student && (
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    {context.student.first_name} {context.student.last_name}
                    {context.student.lrn ? ` · LRN ${context.student.lrn}` : ''}
                  </p>
                )}
              </div>
              <ActionButton variant="secondary" size="sm" onClick={() => loadTransactions()} icon={RotateCcw}>Refresh</ActionButton>
            </div>

            {!context?.student ? (
              <p className="text-sm text-gray-400 text-center py-10">
                Select a student to view their tuition payments.
              </p>
            ) : (
              <>
                {/* Fee / paid / balance straight from the settlement context,
                    so the tab answers "where does this student's tuition
                    stand" without opening another page. */}
                <div className="grid grid-cols-3 gap-3 p-5 pb-0">
                  {[
                    ['Tuition Fee', Number(context?.totals?.tuition_fee || 0), 'text-gray-900'],
                    ['Paid So Far', Number(context?.totals?.tuition_paid || 0), 'text-emerald-600'],
                    ['Outstanding Balance', Math.max(0, Number(context?.totals?.tuition_fee || 0) - Number(context?.totals?.tuition_paid || 0)), 'text-red-600'],
                  ].map(([label, value, color]) => (
                    <div key={label} className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                      <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">{label}</p>
                      <p className={`text-xl font-bold mt-1 ${color}`}>{peso(value)}</p>
                    </div>
                  ))}
                </div>

                {transactions.filter(t => t.kind === 'tuition').length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-10">No tuition payments recorded yet.</p>
                ) : (
                  <table className="w-full text-left text-sm mt-4">
                    <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                      <tr>
                        <th className="px-4 py-2.5 font-medium">Date</th>
                        <th className="px-4 py-2.5 font-medium">Receipt</th>
                        <th className="px-4 py-2.5 font-medium">Method</th>
                        <th className="px-4 py-2.5 font-medium">Notes</th>
                        <th className="px-4 py-2.5 font-medium text-right">Amount</th>
                        <th className="px-4 py-2.5 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {transactions.filter(t => t.kind === 'tuition').map(t => (
                        <tr key={t.id} className="hover:bg-gray-50">
                          <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">
                            {t.date ? new Date(t.date).toLocaleString('en-PH') : '—'}
                          </td>
                          <td className="px-4 py-2.5 font-mono text-xs">{t.reference}</td>
                          <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">{t.method || '—'}</td>
                          <td className="px-4 py-2.5 text-gray-500">
                            <span className="line-clamp-2">{t.description || 'Tuition Fee'}</span>
                          </td>
                          <td className="px-4 py-2.5 text-right font-semibold text-gray-800 whitespace-nowrap">{peso(t.amount)}</td>
                          <td className="px-4 py-2.5"><StatusBadge status={(t.status || 'paid').toLowerCase()} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </>
            )}
          </div>
        </div>
      ) : (
        /* ---------------- history tab ---------------- */
        <div className="p-6">
          <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Receipt size={16} className="text-blue-600" /> Transaction History
                </h2>
                {context?.student && (
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    {context.student.first_name} {context.student.last_name}
                    {context.student.lrn ? ` · LRN ${context.student.lrn}` : ''}
                  </p>
                )}
              </div>
              <ActionButton variant="secondary" size="sm" onClick={() => loadTransactions()} icon={RotateCcw}>Refresh</ActionButton>
            </div>
            {!context?.student ? (
              <p className="text-sm text-gray-400 text-center py-10">
                Select a student to view their ledger.
              </p>
            ) : transactions.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-10">No transactions yet.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Date</th>
                    <th className="px-4 py-2.5 font-medium">Receipt</th>
                    <th className="px-4 py-2.5 font-medium">Type</th>
                    <th className="px-4 py-2.5 font-medium">Description</th>
                    <th className="px-4 py-2.5 font-medium">Method</th>
                    <th className="px-4 py-2.5 font-medium text-right">Amount</th>
                    <th className="px-4 py-2.5 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {transactions.map(t => (
                    <tr key={t.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">
                        {t.date ? new Date(t.date).toLocaleString('en-PH') : '—'}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-xs">{t.reference}</td>
                      <td className="px-4 py-2.5 text-gray-800 whitespace-nowrap">{t.type || '—'}</td>
                      <td className="px-4 py-2.5 text-gray-500">
                        <span className="line-clamp-2">{t.description || '—'}</span>
                      </td>
                      <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">{t.method || '—'}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-gray-800 whitespace-nowrap">{peso(t.amount)}</td>
                      <td className="px-4 py-2.5"><StatusBadge status={(t.status || 'completed').toLowerCase()} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ---------------- payment details modal ---------------- */}
      {showPayModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => !processing && setShowPayModal(false)} />
          <div className="relative bg-white rounded-2xl shadow-2xl z-10 w-full max-w-lg">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <CreditCard size={18} className="text-blue-600" /> Payment Details
              </h2>
              <button onClick={() => setShowPayModal(false)} disabled={processing}
                className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-400">
                <X size={18} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="rounded-xl bg-gray-50 p-4">
                <p className="text-xs text-gray-500">Amount Due</p>
                <p className="text-2xl font-bold text-gray-900">{peso(totalSelected)}</p>
                <p className="text-xs text-gray-400 mt-1">{itemCount} line item{itemCount === 1 ? '' : 's'} · {method}</p>
              </div>

              {/* Itemised breakdown. Without it the Amount Due and the
                  "Collecting Now" figures look unrelated to the items
                  that produced them, which is confusing when a partial
                  payment is split across several lines. */}
              {itemCount > 0 && (
                <div className="rounded-xl border border-gray-200 divide-y divide-gray-100 max-h-40 overflow-y-auto">
                  {selectedList.map(it => {
                    const lineTotal = it.kind === 'charge'
                      ? Math.min(it.balance, Number(it.unit || 0) * (it.qty || 1))
                      : Number(it.unit || 0) * (it.qty || 1)
                    return (
                      <div key={it.key} className="flex items-center justify-between gap-3 px-3 py-2">
                        <span className="text-xs text-gray-700 min-w-0 truncate">
                          {it.name}
                          {it.size && <span className="text-gray-400"> ({it.size})</span>}
                          {it.qty > 1 && <span className="text-gray-400"> x{it.qty}</span>}
                          <span className="ml-1.5 text-[10px] uppercase text-gray-400">
                            {it.kind === 'charge' ? 'charge' : 'item'}
                          </span>
                        </span>
                        <span className="text-xs font-mono text-gray-800 shrink-0">{peso(lineTotal)}</span>
                      </div>
                    )
                  })}
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">How much is being paid?</label>
                <div className="grid grid-cols-3 gap-2">
                  {[['full', 'Full (100%)'], ['half', 'Half (50%)'], ['other', 'Other']].map(([id, label]) => (
                    <button key={id} onClick={() => { setSplit(id); if (id === 'half') setTendered('') }}
                      className={`py-2 rounded-lg border text-sm font-medium transition-colors ${split === id ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {split === 'other' && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Custom amount</label>
                  <div className="relative">
                    <PesoSign size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input type="number" min="0" step="0.01" value={customAmount}
                      onChange={(e) => setCustomAmount(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                </div>
              )}

              <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 flex items-center justify-between">
                <span className="text-sm font-medium text-blue-900">Collecting Now</span>
                <span className="text-xl font-bold text-blue-700">{peso(collectingNow)}</span>
              </div>

              {method === 'Cash' && (
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Cash Tendered</label>
                    <div className="relative">
                      <PesoSign size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      {/* A half payment collects a fixed amount, so tendered
                          (and the change it produces) does not apply. */}
                      <input type="number" min="0" step="0.01" value={tendered}
                        onChange={(e) => setTendered(e.target.value)}
                        disabled={split === 'half'}
                        className={`w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-lg font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 ${split === 'half' ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''}`} />
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {DENOMS.map(d => (
                      <button key={d} disabled={split === 'half'} onClick={() => setTendered(String((parseFloat(tendered) || 0) + d))}
                        className="px-2.5 py-1 text-xs font-medium rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed">
                        +{pesoShort(d)}
                      </button>
                    ))}
                    <button disabled={split === 'half'} onClick={() => setTendered(String(collectingNow))}
                      className="px-2.5 py-1 text-xs font-medium rounded-lg border border-emerald-300 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed">
                      Exact
                    </button>
                  </div>
                  <div className="flex items-center justify-between rounded-xl bg-gray-50 p-3">
                    <span className="text-sm text-gray-600">Change</span>
                    <span className={`text-lg font-bold ${change > 0 ? 'text-emerald-600' : 'text-gray-400'}`}>{peso(change)}</span>
                  </div>
                  {!tenderedValid && (
                    <p className="text-xs text-red-600 flex items-center gap-1.5">
                      <AlertCircle size={13} /> Tendered must be at least {peso(collectingNow)}
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-100 flex gap-2">
              <button onClick={() => setShowPayModal(false)} disabled={processing}
                className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 disabled:opacity-50">
                Cancel
              </button>
              <button onClick={processPayment} disabled={!canConfirm || processing}
                className="flex-[2] px-4 py-2.5 rounded-xl text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2">
                {processing ? <><Loader2 size={16} className="animate-spin" /> Processing…</> : <><Check size={16} /> Confirm Payment</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- official receipt modal ---------------- */}
      {showReceipt && receipt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowReceipt(false)} />
          <div className="relative bg-white rounded-2xl shadow-2xl z-10 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white px-6 py-4 border-b border-gray-100 flex items-center justify-between z-10 no-print">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Receipt size={18} className="text-blue-600" /> Official Receipt
              </h2>
              <button onClick={() => setShowReceipt(false)} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-400">
                <X size={18} />
              </button>
            </div>

            <ReceiptPaper ref={receiptRef} receipt={receipt} config={config} printLogo={printLogo} />

            <div className="px-6 py-4 border-t border-gray-100 flex flex-wrap gap-2 no-print">
              <ActionButton variant="secondary" size="sm" onClick={() => setShowReceipt(false)}>Close</ActionButton>
              <ActionButton variant="secondary" size="sm" onClick={downloadReceipt} icon={Download}>Download</ActionButton>
              <ActionButton variant="secondary" size="sm" onClick={emailReceipt} icon={Mail}>Email</ActionButton>
              <ActionButton size="sm" onClick={printReceipt} icon={Printer}>Print Receipt</ActionButton>
              <ActionButton size="sm" onClick={() => { showToast(`Transaction ${receipt.receiptNumber} completed`); resetTerminal() }} icon={RotateCcw}>
                Done / New
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className={`fixed bottom-6 right-6 z-[70] px-4 py-3 rounded-xl shadow-lg text-sm font-medium text-white ${toast.type === 'error' ? 'bg-red-600' : 'bg-emerald-600'}`}>
          {toast.message}
        </div>
      )}
    </div>
  )
}

function Row({ label, value, mono, small }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-gray-500 shrink-0">{label}</span>
      <span className={`text-gray-900 text-right ${mono ? 'font-mono' : ''} ${small ? 'text-[10px]' : 'text-[11px] font-medium'}`}>{value}</span>
    </div>
  )
}
