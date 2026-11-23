import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useReactToPrint } from 'react-to-print'
import PageHeader from '../components/PageHeader'
import ActionButton from '../components/ActionButton'
import PesoSign from '../components/PesoSign'
import StatusBadge from '../components/StatusBadge'
import {
  Search, Receipt, CreditCard, Banknote, Loader2, Printer, X, AlertCircle,
  Check, User, Users, Plus, Minus, Wallet, RotateCcw, Download, Mail, Info,
  CalendarDays,
} from 'lucide-react'
import apiClient, { financeAPI, studentsAPI, chargeAPI, productAPI, salesAPI, tourAPI, terminalAPI, cashReportAPI, disbursementAPI, assessmentAPI } from '../services/api'
import ReceiptPaper, { RECEIPT_PAGE_STYLE } from '../components/ReceiptPaper'
import { useSchoolConfig } from '../contexts/SchoolConfigContext'
import { useAuth } from '../context/AuthContext'
import { storage } from '../services/storage'
import { staffName } from '../utils/staffName'
import { isElectron, printHtml, buildReceiptHtml, buildDailyCashReportHtml } from '../utils/printDocument'

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
  const { user } = useAuth()

  // ---- terminal / mode -------------------------------------------------
  const [mode, setMode] = useState('student')       // student | walkin
  const [activeTab, setActiveTab] = useState('checkout') // checkout | tuition | history | daily

  // ---- daily collection & disbursement report ---------------------------
  const [showDailyModal, setShowDailyModal] = useState(false)
  const [dailyDate, setDailyDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [dailyPreview, setDailyPreview] = useState(null)
  const [dailyLoading, setDailyLoading] = useState(false)
  const [manualRows, setManualRows] = useState([])          // {description, amount}
  const [manualForm, setManualForm] = useState({ description: '', amount: '' })
  const [disbForm, setDisbForm] = useState({ description: '', amount: '' })
  const [disbSaving, setDisbSaving] = useState(false)
  const [showDenoms, setShowDenoms] = useState(false)
  const [denoms, setDenoms] = useState({ '1000': '', '500': '', '200': '', '100': '', '50': '', '20': '', coins: '' })
  const [dailySaving, setDailySaving] = useState(false)

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
  const [customAmount, setCustomAmount] = useState('')
  const [tendered, setTendered] = useState('')
  // Set when the cashier presses Exact: the field grays out so the amount
  // cannot be nudged off the total by accident. Edit unlocks it again.
  const [tenderedLocked, setTenderedLocked] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [showReceipt, setShowReceipt] = useState(false)
  const [receipt, setReceipt] = useState(null)
  const [toast, setToast] = useState(null)
  const [transactions, setTransactions] = useState([])
  // Tour enrollments with an outstanding balance for the selected student.
  const [tourEnrollments, setTourEnrollments] = useState([])
  // This register's name from the device registry (Django admin → Terminals);
  // printed on every receipt. Null for plain-browser sessions.
  const [terminalName, setTerminalName] = useState(null)

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

  // Inside Electron the receipt goes through the main-process print pipeline
  // (explicit 80mm portrait options) because the native dialog otherwise
  // starts from the printer driver's defaults and prints landscape on A4.
  const handlePrintReceipt = async () => {
    if (isElectron()) {
      try {
        await printHtml(buildReceiptHtml(receipt, config, printLogo), {
          pageSize: 'receipt',
          title: 'Official Receipt',
        })
      } catch (e) {
        showToast(e.message || 'Print failed', 'error')
      }
      return
    }
    printReceipt()
  }

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

  // ---- daily collection & disbursement report ---------------------------
  const loadDaily = useCallback(async (date) => {
    if (!date) return
    setDailyLoading(true)
    try {
      const d = await cashReportAPI.preview(date)
      setDailyPreview(d)
    } catch {
      showToast('Failed to load the daily report', 'error')
    } finally {
      setDailyLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const addDisbursement = async () => {
    const amount = Number(disbForm.amount)
    if (!disbForm.description.trim() || !amount || amount <= 0) {
      showToast('Enter a description and an amount', 'error')
      return
    }
    setDisbSaving(true)
    try {
      await disbursementAPI.create({ date: dailyDate, description: disbForm.description.trim(), amount })
      setDisbForm({ description: '', amount: '' })
      await loadDaily(dailyDate)
      showToast('Disbursement recorded', 'success')
    } catch {
      showToast('Failed to record the disbursement', 'error')
    } finally {
      setDisbSaving(false)
    }
  }

  const removeDisbursement = async (id) => {
    try {
      await disbursementAPI.remove(id)
      await loadDaily(dailyDate)
    } catch {
      showToast('Could not remove the disbursement', 'error')
    }
  }

  const addManualRow = () => {
    const amount = Number(manualForm.amount)
    if (!manualForm.description.trim() || !amount || amount <= 0) {
      showToast('Enter a description and an amount', 'error')
      return
    }
    setManualRows((rows) => [...rows, { description: manualForm.description.trim(), amount }])
    setManualForm({ description: '', amount: '' })
  }

  const removeManualRow = (idx) => setManualRows((rows) => rows.filter((_, i) => i !== idx))

  const autoRows = dailyPreview?.auto_collections || []
  const disbRows = dailyPreview?.disbursements || []
  const dailyTotalCollection =
    Math.round(
      (autoRows.reduce((s, r) => s + Number(r.amount || 0), 0) +
        manualRows.reduce((s, r) => s + Number(r.amount || 0), 0)) * 100
    ) / 100
  const dailyTotalDisbursement = disbRows.reduce((s, r) => s + Number(r.amount || 0), 0)
  const dailyNet = Math.round((dailyTotalCollection - dailyTotalDisbursement) * 100) / 100
  const countedTotal =
    Object.entries(denoms).reduce(
      (s, [key, qty]) => s + (key === 'coins' ? Number(qty || 0) : Number(qty || 0) * Number(key)),
      0
    )
  const countedDiff = Math.round((countedTotal - dailyNet) * 100) / 100

  const saveDailyReport = async () => {
    setDailySaving(true)
    try {
      const saved = await cashReportAPI.save({
        date: dailyDate,
        manual_rows: manualRows,
        denominations: Object.fromEntries(
          Object.entries(denoms).map(([k, v]) => [k, Number(v || 0)])
        ),
      })
      setShowDenoms(false)
      showToast('Daily report saved', 'success')
      const preparedBy = user?.firstName || user?.username || ''
      await printHtml(
        buildDailyCashReportHtml({
          config,
          // The inlined data URI is the only logo form that reliably renders
          // inside the self-contained print document.
          logo: printLogo || config?.logo_url || config?.logo,
          report: saved,
          preparedBy,
          checkedBy: config?.report_checked_by || '',
        })
      )
      await loadDaily(dailyDate)
    } catch {
      showToast('Failed to save the daily report', 'error')
    } finally {
      setDailySaving(false)
    }
  }


  // Resolve this register's name once so receipts label themselves with the
  // terminal the admin set (falls back to omitting the line in a browser).
  useEffect(() => {
    let cancelled = false
    terminalAPI.getCurrent().then((d) => {
      const name = d?.terminal?.name || null
      if (!cancelled && name) setTerminalName(name)
    }).catch(() => {})
    return () => { cancelled = true }
  }, [])

  // Student search: name OR 12-digit LRN
  const skipSearchRef = useRef(false)
  useEffect(() => {
    const term = query.trim()
    // Selecting a student sets the query to their LRN/name programmatically;
    // that change must not re-run the search and re-open the dropdown.
    if (skipSearchRef.current) {
      skipSearchRef.current = false
      setSearchResults([])
      return
    }
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
    skipSearchRef.current = true
    setQuery(student.lrn || `${student.first_name} ${student.last_name}`)
    setCtxLoading(true)
    setSelected({})
    loadTourEnrollments(student.id)
    try {
      const ctx = await studentsAPI.settlementContext(student.id)
      setContext(ctx)
    } catch (err) {
      showToast('Failed to load student account', 'error')
    } finally {
      setCtxLoading(false)
    }
  }

  // Educational tours the student is enrolled in (via their section), with a
  // remaining balance — each one is payable at the register like tuition.
  const loadTourEnrollments = useCallback(async (studentId) => {
    if (!studentId) { setTourEnrollments([]); return }
    try {
      const data = await tourAPI.getEnrollmentsByStudent(studentId)
      const list = Array.isArray(data) ? data : data.results || []
      setTourEnrollments(list.filter(e => Number(e.balance || 0) > 0))
    } catch {
      setTourEnrollments([])
    }
  }, [])

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
          // Highlight when part of the fee has already been settled.
          partial: Number(context?.totals?.tuition_paid || 0) > 0,
        })
      }
      if (category !== 'tuition') {
        charges.forEach(c => rows.push({
          key: `charge-${c.id}`, kind: 'charge', id: c.id,
          name: c.item_name, description: c.description,
          unit: c.unit_price, qty: c.qty, balance: c.balance, locked: true,
          partial: c.status === 'partial',
        }))
        // Assessment fees with a remaining balance are payable at the
        // register too. They are settled through the assessment-payment
        // endpoint, so they carry their own kind.
        ;(context?.unpaid_assessments || []).forEach(a => rows.push({
          key: `assessment-${a.id}`, kind: 'assessment', id: a.id,
          name: a.name, description: 'Assessment fee',
          unit: a.balance, qty: 1, balance: a.balance, locked: true,
          partial: Number(a.amount_paid || 0) > 0,
        }))
        // Tours the student's section was enrolled into. Settled through the
        // tour-payment endpoint, which enforces the enrollment balance.
        tourEnrollments.forEach(e => rows.push({
          key: `tour-${e.id}`, kind: 'tour', id: e.id,
          name: e.tour_name, description: e.tour_destination || 'Educational tour',
          unit: Number(e.balance || 0), qty: 1, balance: Number(e.balance || 0), locked: true,
          partial: e.status === 'Partial',
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
  }, [category, charges, supplies, academicProducts, context, tourEnrollments])

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
    if (it.kind === 'charge' || it.kind === 'tour') {
      const cap = it.balance
      const want = Number(it.unit || 0) * (it.qty || 1)
      return sum + Math.min(cap, want)
    }
    return sum + Number(it.unit || 0) * (it.qty || 1)
  }, 0)

  const itemCount = selectedList.length

  // ---- payment details -------------------------------------------------
  const collectingNow = useMemo(() => {
    // Never collect more than the amount due - the backend rejects any
    // settlement above a charge's remaining balance with a 400.
    return Math.min(Math.max(0, parseFloat(customAmount) || 0), totalSelected)
  }, [totalSelected, customAmount])

  const change = useMemo(() => {
    const t = parseFloat(tendered) || 0
    return Math.max(0, t - collectingNow)
  }, [tendered, collectingNow])

  const tenderedValid = method !== 'Cash' || (parseFloat(tendered) || 0) >= collectingNow
  const referenceRequired = method === 'GCash' || method === 'Bank Transfer'
  const canConfirm = collectingNow > 0 && tenderedValid && (!referenceRequired || reference.trim())

  const openPayModal = () => {
    if (!itemCount) return
    // The amount field starts on the full amount due, so the usual case is
    // one click on Confirm; a partial payment is just a different number.
    setCustomAmount(String(totalSelected)); setTendered(''); setTenderedLocked(false)
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
      for (const item of selectedList.filter(i => i.kind === 'charge' || i.kind === 'tuition' || i.kind === 'tour' || i.kind === 'assessment')) {
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
        } else if (item.kind === 'tour') {
          // Tour fees are settled against the enrollment row; the endpoint
          // rejects anything above the remaining balance.
          await tourAPI.createPayment({
            enrollment_id: item.id,
            amount: Number(share.toFixed(2)),
            payment_method: method,
            reference_number: reference.trim() || undefined,
            remarks: `Cashier collection (${method})`,
          })
        } else if (item.kind === 'assessment') {
          // Assessment fees are settled against the assessment row.
          await assessmentAPI.createPayment({
            assessment_id: item.id,
            amount: Number(share.toFixed(2)),
            payment_method: method,
            reference_number: reference.trim() || undefined,
            remarks: `Cashier collection (${method})`,
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

      // What the family still owes after this payment. The receipt has to
      // say it — otherwise they leave the counter believing they are clear.
      const tuitionCollected = lines
        .filter(l => l.kind === 'tuition')
        .reduce((s, l) => s + Number(l.amount || 0), 0)
      const tuitionDue = Number(context?.totals?.tuition_balance || 0)
      const outstandingTuition = Math.max(0, tuitionDue - tuitionCollected)
      const outstandingTotal = Math.max(
        0,
        Number(context?.totals?.outstanding || 0) - Number(collected || 0)
      )
      const extraRows = []
      if (tuitionCollected > 0) extraRows.push(['Outstanding Tuition', peso(outstandingTuition)])
      if (mode === 'student' && outstandingTotal > 0) {
        extraRows.push(['Outstanding Balance', peso(outstandingTotal)])
      }

      const r = {
        receiptNumber: receiptNo,
        timestamp: new Date().toISOString(),
        // Printed documents carry the staff profile name, not the login username.
        cashierName: staffName(),
        terminalId: terminalName,
        student: context?.student || null,
        payerName,
        mode,
        lines,
        extraRows,
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
        loadTourEnrollments(studentId)
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
    setCustomAmount(''); setTendered('')
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
      `Cashier: ${receipt.cashierName}${receipt.terminalId ? ` (${receipt.terminalId})` : ''}`,
      receipt.student ? `Student: ${receipt.student.first_name} ${receipt.student.last_name}` : `Payer: ${receipt.payerName}`,
      '', 'ITEMS', ...receipt.lines.map(l => `${l.name}${l.size ? ` (${l.size})` : ''} x${l.qty}  ${peso(l.amount)}`),
      '', `TOTAL: ${peso(receipt.total)}`,
      `Method: ${receipt.method}${receipt.reference ? ` (${receipt.reference})` : ''}`,
      receipt.method === 'Cash' ? `Tendered: ${peso(receipt.tendered)}  Change: ${peso(receipt.change)}` : '',
      ...(receipt.extraRows || []).map(([label, value]) => `${label}: ${value}`),
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
            {/* Walk-in is disabled for now — sales must be tied to a student
                so the daily collection report can attribute them. */}
            <ActionButton variant="secondary" size="sm" onClick={() => { setShowDailyModal(true); loadDaily(dailyDate) }} icon={CalendarDays}>
              Daily Report
            </ActionButton>
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

            {/* Tuition breakdown - what the fee is made of, per term.
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
                  {(context.tuition_breakdown.terms || []).map(q => (
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
                const isPartial = !!row.partial
                const lineTotal = row.kind === 'charge' || row.kind === 'tour'
                  ? Math.min(row.balance, Number(row.unit) * (row.qty || 1))
                  : Number(row.unit) * (row.qty || 1)
                return (
                  <div key={row.key}
                    className={`border rounded-xl p-3 flex items-start gap-3 transition-colors ${isSel ? 'border-blue-300 bg-blue-50/40' : isPartial ? 'border-yellow-300 bg-yellow-50' : 'border-gray-200 bg-white'}`}>
                    <input type="checkbox" checked={isSel} onChange={() => toggleItem(row)}
                      disabled={(row.kind === 'charge' || row.kind === 'tour') && row.balance <= 0}
                      className="mt-1 w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-gray-900">{row.name}</span>
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${row.kind === 'product' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-blue-50 text-blue-700 border border-blue-200'}`}>
                          {row.kind === 'product' ? 'Product' : row.kind === 'tour' ? 'Tour' : 'Fee'}
                        </span>
                        {isPartial && (
                          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-800 border border-yellow-300">
                            Partially Paid
                          </span>
                        )}
                      </div>
                      {row.description && <p className="text-xs text-gray-500 mt-0.5">{row.description}</p>}
                      {row.kind === 'charge' || row.kind === 'tour' ? (
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
      ) : activeTab === 'history' ? (
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
                    <tr key={t.id} className={t.status === 'partial' ? 'bg-yellow-50 hover:bg-yellow-100' : 'hover:bg-gray-50'}>
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
      ) : null}

      {/* ---------------- daily collection & disbursement report ---------------- */}
      {showDailyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowDailyModal(false)} />
          <div className="relative bg-gray-50 rounded-2xl shadow-2xl z-10 w-full max-w-4xl max-h-[92vh] overflow-y-auto p-6 space-y-5">
          {/* header: date + totals */}
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Report date</label>
              <input type="date" value={dailyDate} onChange={(e) => setDailyDate(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="flex items-center gap-4 text-right">
              <div>
                <p className="text-xs text-gray-500">TOTAL COLLECTION</p>
                <p className="text-xl font-bold text-gray-900">{peso(dailyTotalCollection)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">NET AMOUNT</p>
                <p className="text-xl font-bold text-emerald-700">{peso(dailyNet)}</p>
              </div>
              <button onClick={() => setShowDenoms(true)} disabled={dailyLoading}
                className="px-4 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors disabled:opacity-50">
                Generate Report
              </button>
            </div>
          </div>

          {dailyLoading ? (
            <div className="py-16 flex items-center justify-center text-gray-400 gap-2">
              <Loader2 size={18} className="animate-spin" /> Loading…
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* collections */}
              <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-800 text-sm">COLLECTIONS</h3>
                  <span className="text-xs text-gray-400">
                    since {dailyPreview?.period_start ? new Date(dailyPreview.period_start).toLocaleDateString('en-PH') : '—'}
                  </span>
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr>
                      <th className="px-5 py-2 text-left text-[11px] font-semibold text-gray-500 uppercase">Description</th>
                      <th className="px-3 py-2 text-right text-[11px] font-semibold text-gray-500 uppercase">Qty</th>
                      <th className="px-5 py-2 text-right text-[11px] font-semibold text-gray-500 uppercase">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {autoRows.map((r, i) => (
                      <tr key={`a-${i}`}>
                        <td className="px-5 py-2.5 text-gray-700">{r.description}</td>
                        <td className="px-3 py-2.5 text-right font-mono text-gray-500">{r.count ?? 1}</td>
                        <td className="px-5 py-2.5 text-right font-mono text-gray-800">{peso(r.amount)}</td>
                      </tr>
                    ))}
                    {manualRows.map((r, i) => (
                      <tr key={`m-${i}`} className="bg-blue-50/50">
                        <td className="px-5 py-2.5 text-gray-700">
                          {r.description}
                          <span className="ml-1.5 text-[10px] uppercase text-blue-500">manual</span>
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-gray-500">1</td>
                        <td className="px-5 py-2.5 text-right font-mono text-gray-800">
                          {peso(r.amount)}
                          <button onClick={() => removeManualRow(i)} className="ml-2 text-gray-300 hover:text-red-500"><X size={13} /></button>
                        </td>
                      </tr>
                    ))}
                    {!autoRows.length && !manualRows.length && (
                      <tr><td className="px-5 py-6 text-center text-gray-400" colSpan={3}>No collections in this period yet.</td></tr>
                    )}
                  </tbody>
                </table>
                <div className="px-5 py-2.5 border-t border-gray-200 bg-gray-50 flex items-center gap-2">
                  <input value={manualForm.description} onChange={(e) => setManualForm({ ...manualForm, description: e.target.value })}
                    placeholder="Manual row (e.g. donation)" className="flex-1 px-3 py-1.5 border border-gray-200 rounded-lg text-xs" />
                  <input type="number" min="0" step="0.01" value={manualForm.amount} onChange={(e) => setManualForm({ ...manualForm, amount: e.target.value })}
                    placeholder="Amount" className="w-24 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-mono" />
                  <button onClick={addManualRow} className="px-2.5 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded-lg">Add</button>
                </div>
              </div>

              {/* disbursements */}
              <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100">
                  <h3 className="font-semibold text-gray-800 text-sm">LESS: DISBURSEMENT</h3>
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr>
                      <th className="px-5 py-2 text-left text-[11px] font-semibold text-gray-500 uppercase">Description</th>
                      <th className="px-3 py-2 text-right text-[11px] font-semibold text-gray-500 uppercase">Qty</th>
                      <th className="px-5 py-2 text-right text-[11px] font-semibold text-gray-500 uppercase">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {disbRows.map((d) => (
                      <tr key={d.id}>
                        <td className="px-5 py-2.5 text-gray-700">{d.description}</td>
                        <td className="px-3 py-2.5 text-right font-mono text-gray-500">{d.count ?? 1}</td>
                        <td className="px-5 py-2.5 text-right font-mono text-gray-800">
                          {peso(d.amount)}
                          <button onClick={() => removeDisbursement(d.id)} className="ml-2 text-gray-300 hover:text-red-500"><X size={13} /></button>
                        </td>
                      </tr>
                    ))}
                    {!disbRows.length && (
                      <tr><td className="px-5 py-6 text-center text-gray-400" colSpan={3}>No disbursements logged for this date.</td></tr>
                    )}
                  </tbody>
                </table>
                <div className="px-5 py-2.5 border-t border-gray-200 bg-gray-50 flex items-center gap-2">
                  <input value={disbForm.description} onChange={(e) => setDisbForm({ ...disbForm, description: e.target.value })}
                    placeholder="Expense (e.g. fare, supplies)" className="flex-1 px-3 py-1.5 border border-gray-200 rounded-lg text-xs" />
                  <input type="number" min="0" step="0.01" value={disbForm.amount} onChange={(e) => setDisbForm({ ...disbForm, amount: e.target.value })}
                    placeholder="Amount" className="w-24 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-mono" />
                  <button onClick={addDisbursement} disabled={disbSaving}
                    className="px-2.5 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-50">{disbSaving ? '…' : 'Add'}</button>
                </div>
              </div>
            </div>
          )}
          </div>
        </div>
      )}

      {/* ---------------- denomination modal ---------------- */}
      {showDenoms && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowDenoms(false)} />
          <div className="relative bg-white rounded-2xl shadow-2xl z-10 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Cash Denominations</h2>
              <button onClick={() => setShowDenoms(false)} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-400"><X size={18} /></button>
            </div>
            <div className="p-6 space-y-4">
              <table className="w-full text-sm">
                <tbody className="divide-y divide-gray-100">
                  {[['1000', '₱ 1,000'], ['500', '₱ 500'], ['200', '₱ 200'], ['100', '₱ 100'], ['50', '₱ 50'], ['20', '₱ 20'], ['coins', 'Coins (amount)']].map(([key, label]) => (
                    <tr key={key}>
                      <td className="py-2 text-gray-700">{label}</td>
                      <td className="py-2 text-right">
                        <input type="number" min="0" step={key === 'coins' ? '0.01' : '1'} value={denoms[key]}
                          onChange={(e) => setDenoms({ ...denoms, [key]: e.target.value })}
                          placeholder={key === 'coins' ? '0.00' : '0'}
                          className="w-28 px-3 py-1.5 border border-gray-300 rounded-lg text-right font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className={`rounded-xl p-4 flex items-center justify-between ${countedDiff === 0 ? 'bg-emerald-50 border border-emerald-200' : 'bg-amber-50 border border-amber-300'}`}>
                <div>
                  <p className="text-xs text-gray-500">Counted total vs NET</p>
                  <p className="text-lg font-bold text-gray-900">{peso(countedTotal)}</p>
                </div>
                <div className="text-right">
                  {countedDiff === 0
                    ? <span className="text-xs font-semibold text-emerald-700">Balanced</span>
                    : <span className="text-xs font-semibold text-amber-700">Difference: {peso(countedDiff)}</span>}
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setShowDenoms(false)}
                  className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl">Cancel</button>
                <button onClick={saveDailyReport} disabled={dailySaving}
                  className="flex-1 px-4 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl disabled:opacity-50">
                  {dailySaving ? 'Saving…' : 'Save & Print'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- payment details modal ---------------- */}
      {showPayModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => !processing && setShowPayModal(false)} />
          <div className="relative bg-white rounded-2xl shadow-2xl z-10 w-full max-w-lg flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between shrink-0">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <CreditCard size={18} className="text-blue-600" /> Payment Details
              </h2>
              <button onClick={() => setShowPayModal(false)} disabled={processing}
                className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-400">
                <X size={18} />
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto">
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
                <label className="block text-xs font-medium text-gray-600 mb-1.5">
                  Amount to collect
                </label>
                <div className="relative">
                  <PesoSign size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input type="number" min="0" step="0.01" value={customAmount}
                    onChange={(e) => setCustomAmount(e.target.value)}
                    onFocus={(e) => e.target.select()}
                    className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <p className="text-[11px] text-gray-400 mt-1">
                  The full amount due is {peso(totalSelected)}. Type a smaller number for a
                  partial payment.
                </p>
              </div>

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
                      {/* An Exact payment is locked so it cannot be nudged off
                          the collected amount by accident. Edit re-opens it. */}
                      <input type="number" min="0" step="0.01" value={tendered}
                        onChange={(e) => setTendered(e.target.value)}
                        disabled={tenderedLocked}
                        className={`w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-lg font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 ${tenderedLocked ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''}`} />
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {DENOMS.map(d => (
                      <button key={d} disabled={tenderedLocked} onClick={() => setTendered(String((parseFloat(tendered) || 0) + d))}
                        className="px-2.5 py-1 text-xs font-medium rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed">
                        +{pesoShort(d)}
                      </button>
                    ))}
                    {tenderedLocked ? (
                      <button onClick={() => setTenderedLocked(false)}
                        className="px-2.5 py-1 text-xs font-medium rounded-lg border border-blue-300 bg-blue-50 hover:bg-blue-100 text-blue-700">
                        Edit Amount
                      </button>
                    ) : (
                      <button onClick={() => { setTendered(String(collectingNow)); setTenderedLocked(true) }}
                        className="px-2.5 py-1 text-xs font-medium rounded-lg border border-emerald-300 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed">
                        Exact
                      </button>
                    )}
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
              <ActionButton size="sm" onClick={handlePrintReceipt} icon={Printer}>Print Receipt</ActionButton>
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
