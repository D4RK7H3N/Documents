import { useState, useEffect, useMemo, useRef } from 'react'
import { useReactToPrint } from 'react-to-print'
import PageHeader from '../components/PageHeader'
import ActionButton from '../components/ActionButton'
import StatusBadge from '../components/StatusBadge'
import { financeAPI, studentsAPI, chargeAPI } from '../services/api'
import {
  Search, Clock, AlertCircle, Loader2, Check, X,
  Download, Eye, Printer,
  ChevronLeft, ChevronRight, Filter, XCircle, AlertTriangle, CheckCircle
} from 'lucide-react'
import PesoSign from '../components/PesoSign'
import { useSchoolConfig } from '../contexts/SchoolConfigContext'
import { staffName } from '../utils/staffName'
import { isElectron, printNode } from '../utils/printDocument'
import { ITEMS_PER_PAGE } from '../constants/list'


// A record belongs to a graduate when the student has left the roster:
// their status/enrollment says Graduated, or their year level was marked
// as Graduated.
const isGraduatedRecord = (p) =>
  p?.status === 'Graduated' ||
  p?.enrollment_status === 'Graduated' ||
  p?.student_status === 'Graduated' ||
  (p?.grade || '').toString().trim().toLowerCase() === 'graduated'
const gradeLevels = ['Grade 11', 'Grade 12', '1st Year Bundled', '2nd Year Bundled']
const balanceRanges = [
  { value: 'all', label: 'All Balances' },
  { value: 'below_1000', label: 'Below ₱1,000' },
  { value: '1000_5000', label: '₱1,000 - ₱5,000' },
  { value: 'above_5000', label: 'Above ₱5,000' },
]

export default function PendingPaymentsPage() {
  const { config, printLogo } = useSchoolConfig()
  // 'all' | 'active' | 'graduated' — graduates keep their balances but sit in
  // their own tab.
  const [statusTab, setStatusTab] = useState('all')
  const [loading, setLoading] = useState(true)
  const [payments, setPayments] = useState([])
  const [students, setStudents] = useState({})
  const [charges, setCharges] = useState({})
  const [toast, setToast] = useState(null)

  const [search, setSearch] = useState('')
  const [selectedGrade, setSelectedGrade] = useState('')
  const [selectedSection, setSelectedSection] = useState('')
  const [selectedRange, setSelectedRange] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)

  const [showViewStudent, setShowViewStudent] = useState(false)
  const [viewingStudent, setViewingStudent] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }

  const fetchData = async () => {
    try {
      setLoading(true)
      // Must use /tuition-payments/records/ (aggregated per student). The plain
      // /tuition-payments/ list marks student_id/amount_paid as write_only and
      // has no total_tuition, so every record computed to balance 0 and was
      // filtered out - students with an unsettled balance never appeared.
      const [recordsData, studentsData, chargesData] = await Promise.all([
        financeAPI.getTuitionRecords().catch(() => []),
        // include_inactive: StudentViewSet.get_queryset() excludes
        // Drop-out/Inactive/Transferred by default, and those students still
        // owe balances - without this their details all show as N/A.
        studentsAPI.getAll({ include_inactive: true }).catch(() => []),
        chargeAPI.summary().catch(() => ({ students: [] }))
      ])

      const allPayments = Array.isArray(recordsData) ? recordsData : (recordsData.results || [])
      const allStudents = Array.isArray(studentsData) ? studentsData : (studentsData.results || [])

      // Outstanding per-item balances from partial ("Half") cashier payments.
      // Only item-source balances are ADDED to the outstanding total, because
      // Student.tuition_balance already accounts for money taken against
      // tuition - adding tuition-source charges too would double-count them.
      const chargeMap = {}
      ;(chargesData?.students || []).forEach(c => { chargeMap[c.student_id] = c })
      setCharges(chargeMap)

      const studentsMap = {}
      allStudents.forEach(s => {
        studentsMap[s.id] = {
          id: s.id,
          name: `${s.first_name || ''} ${s.last_name || ''}`.trim(),
          lrn: s.lrn,
          grade: s.current_grade_level || s.grade || '',
          section: s.section || '',
          gender: s.gender || '',
          birthday: s.date_of_birth || '',
          address: s.address || s.guardian_address || '',
          contact: s.contact_number || s.phone || '',
          guardian: s.guardian_name || '',
          // List endpoint exposes guardian_contact as guardian_phone.
          guardian_contact: s.guardian_contact || s.guardian_phone || '',
          // Resolved by the backend: the section's adviser (School Config
          // adviser manager) with the student's own field as fallback.
          adviser: s.adviser || '',
          enrollment_status: s.enrollment_status || '',
          graduated_sy: s.graduated_sy || '',
        }
      })

      const pendingRecords = allPayments
        .map(p => {
          const student = studentsMap[p.student_id] || {}
          const total = parseFloat(p.total_tuition || 0)
          const paid = parseFloat(p.amount_paid || 0)
          const tuitionBalance = parseFloat(p.balance != null ? p.balance : total - paid)
          const status = p.status || (total > 0 && paid >= total ? 'paid' : paid > 0 ? 'partial' : 'unpaid')
          const charge = chargeMap[p.student_id] || {}
          const itemBalance = parseFloat(charge.item_balance || 0)
          const balance = tuitionBalance + itemBalance
          // Excluded only when fully settled across BOTH tuition and items.
          if ((status === 'paid' || tuitionBalance <= 0) && itemBalance <= 0) return null
          return {
            ...p,
            id: p.id != null ? p.id : p.student_id,
            student_id: p.student_id,
            studentName: student.name || p.student_name || 'N/A',
            lrn: student.lrn || p.lrn || 'N/A',
            grade: p.grade || student.grade || 'N/A',
            section: p.section || student.section || 'N/A',
            total_tuition: total,
            amount_paid: paid,
            tuition_balance: tuitionBalance,
            item_balance: itemBalance,
            owed_items: charge.items || [],
            tuition_charge_balance: parseFloat(charge.tuition_charge_balance || 0),
            balance,
            last_payment_date: p.latest_payment_date || p.payment_date || p.updated_at || null,
            status,
            // The student's own state, so a graduate is recognised even when
            // the tuition record still names an old year level.
            student_status: student.status || '',
            enrollment_status: student.enrollment_status || '',
          }
        })
        .filter(Boolean)

      // Students who owe only for items (no tuition record at all) must still
      // appear, so union them in rather than losing them.
      ;(chargesData?.students || []).forEach(c => {
        if (pendingRecords.some(r => r.student_id === c.student_id)) return
        if (parseFloat(c.item_balance || 0) <= 0) return
        const student = studentsMap[c.student_id] || {}
        pendingRecords.push({
          id: `charge-${c.student_id}`,
          student_id: c.student_id,
          studentName: student.name || c.student_name || 'N/A',
          lrn: student.lrn || c.lrn || 'N/A',
          grade: student.grade || 'N/A',
          section: student.section || 'N/A',
          total_tuition: 0,
          amount_paid: 0,
          tuition_balance: 0,
          item_balance: parseFloat(c.item_balance || 0),
          owed_items: c.items || [],
          tuition_charge_balance: parseFloat(c.tuition_charge_balance || 0),
          balance: parseFloat(c.item_balance || 0),
          last_payment_date: null,
          status: 'unpaid',
          student_status: student.status || '',
          enrollment_status: student.enrollment_status || '',
        })
      })

      setPayments(pendingRecords)
      setStudents(studentsMap)
    } catch (error) {
      console.error('Error fetching data:', error)
      showToast('Failed to load pending payments', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    setCurrentPage(1)
  }, [search, selectedGrade, selectedSection, selectedRange])

  const filteredPayments = useMemo(() => {
    let filtered = [...payments]

    // Graduated students keep their balances here (the school still collects
    // them) but live in their own tab so the working list stays readable.
    if (statusTab === 'graduated') {
      filtered = filtered.filter(p => isGraduatedRecord(p))
    } else if (statusTab === 'active') {
      filtered = filtered.filter(p => !isGraduatedRecord(p))
    }

    if (search) {
      const q = search.toLowerCase()
      filtered = filtered.filter(p =>
        (p.studentName || '').toLowerCase().includes(q) ||
        (p.lrn || '').toLowerCase().includes(q)
      )
    }

    if (selectedGrade) {
      filtered = filtered.filter(p => p.grade === selectedGrade)
    }

    if (selectedSection) {
      filtered = filtered.filter(p => p.section === selectedSection)
    }

    if (selectedRange !== 'all') {
      filtered = filtered.filter(p => {
        if (selectedRange === 'below_1000') return p.balance < 1000
        if (selectedRange === '1000_5000') return p.balance >= 1000 && p.balance <= 5000
        if (selectedRange === 'above_5000') return p.balance > 5000
        return true
      })
    }

    return filtered.sort((a, b) => b.balance - a.balance)
  }, [payments, search, selectedGrade, selectedSection, selectedRange, statusTab])

  const paginatedPayments = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE
    return filteredPayments.slice(start, start + ITEMS_PER_PAGE)
  }, [filteredPayments, currentPage])

  const totalPages = Math.ceil(filteredPayments.length / ITEMS_PER_PAGE)

  const stats = useMemo(() => {
    const totalPending = filteredPayments.reduce((sum, p) => sum + p.balance, 0)
    const studentCount = new Set(filteredPayments.map(p => p.student_id)).size
    const avgBalance = studentCount > 0 ? totalPending / studentCount : 0
    return { totalPending, studentCount, avgBalance }
  }, [filteredPayments])

  const uniqueSections = [...new Set(payments.map(p => p.section).filter(Boolean))].sort()

  const resetFilters = () => {
    setSearch('')
    setSelectedGrade('')
    setSelectedSection('')
    setSelectedRange('all')
  }

  // ---- statement of account ---------------------------------------------
  // A statement of where the account stands - owed items and the current
  // tuition balance - for follow-up collection. This page does not take
  // money, so this is deliberately NOT a receipt: no OR number, no
  // tendered/change, nothing that implies a payment happened here.
  const statementRef = useRef(null)
  const [statement, setStatement] = useState(null)
  const [showStatement, setShowStatement] = useState(false)

  const STATEMENT_PAGE_STYLE = `
    @page { size: A4 portrait; margin: 12mm; }
    html, body { background: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .statement-content { box-shadow: none !important; border: none !important; margin: 0 !important; padding: 0 !important; width: 100% !important; max-width: none !important; }
    .statement-content table { page-break-inside: auto; }
    .statement-content tr { page-break-inside: avoid; }
  `

  const printStatement = useReactToPrint({
    contentRef: statementRef,
    documentTitle: 'Statement of Account',
    pageStyle: STATEMENT_PAGE_STYLE,
  })

  // Electron routes through the main-process print pipeline (explicit A4
  // portrait) because the native dialog otherwise starts from the printer
  // driver's defaults.
  const handlePrintStatement = async () => {
    if (isElectron()) {
      try {
        await printNode(statementRef.current, {
          pageSize: 'A4',
          title: 'Statement of Account',
          extraCss: STATEMENT_PAGE_STYLE,
        })
      } catch (e) {
        showToast(e.message || 'Print failed', 'error')
      }
      return
    }
    printStatement()
  }

  const handlePrintStatementFor = (payment) => {
    const student = students[payment.student_id] || {}
    const isGraduated = payment.grade === 'Graduated' || student.enrollment_status === 'Graduated'
    setStatement({
      generatedAt: new Date().toISOString(),
      preparedBy: staffName(),
      studentName: payment.studentName || 'N/A',
      lrn: payment.lrn && payment.lrn !== 'N/A' ? payment.lrn : '',
      grade: payment.grade || 'N/A',
      section: payment.section || 'N/A',
      // A graduate's section no longer matters — show the graduation instead
      // of "Graduated — <section>".
      isGraduated,
      graduatedSy: student.graduated_sy || '',
      // The class adviser resolves from the section (School Config adviser
      // manager), falling back to the student's own adviser field.
      adviser: student.adviser || '',
      totalTuition: Number(payment.total_tuition || 0),
      amountPaid: Number(payment.amount_paid || 0),
      tuitionBalance: Number(payment.tuition_balance ?? 0),
      owedItems: (payment.owed_items || []).map(i => ({
        name: i.item_name,
        qty: Number(i.qty || 1),
        unitPrice: Number(i.unit_price || 0),
        amountPaid: Number(i.amount_paid || 0),
        balance: Number(i.balance || 0),
        isTuition: i.source === 'tuition',
      })),
      itemBalance: Number(payment.item_balance || 0),
      totalDue: Number(payment.balance || 0),
    })
    setShowStatement(true)
  }

  const handleViewStudent = (payment) => {
    const studentData = students[payment.student_id]
    setViewingStudent({ ...payment, ...studentData })
    setShowViewStudent(true)
  }

  const handleExportCSV = () => {
    const headers = ['LRN', 'Student Name', 'Grade', 'Section', 'Total Tuition', 'Amount Paid', 'Remaining Balance', 'Last Payment Date']
    const rows = filteredPayments.map(p => [
      p.lrn,
      p.studentName,
      p.grade,
      p.section,
      p.total_tuition.toLocaleString(),
      p.amount_paid.toLocaleString(),
      p.balance.toLocaleString(),
      p.last_payment_date ? new Date(p.last_payment_date).toLocaleDateString() : 'N/A',
    ])
    const csvContent = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n')
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pending_payments_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
    showToast('Pending payments exported successfully')
  }

  const getBalanceColor = (balance, total) => {
    if (balance <= 0) return 'text-green-600 bg-green-50'
    const ratio = balance / total
    if (ratio > 0.7) return 'text-red-600 bg-red-50'
    if (ratio > 0.3) return 'text-yellow-600 bg-yellow-50'
    return 'text-green-600 bg-green-50'
  }

  const statCards = [
    { label: 'Total Pending Amount', value: `₱${stats.totalPending.toLocaleString()}`, icon: Clock, statBg: 'bg-amber-50', iconBg: 'bg-amber-100', iconColor: 'text-amber-600' },
    { label: 'Students with Balance', value: stats.studentCount, icon: AlertCircle, statBg: 'bg-blue-50', iconBg: 'bg-blue-100', iconColor: 'text-blue-600' },
    { label: 'Avg Balance per Student', value: `₱${Math.round(stats.avgBalance).toLocaleString()}`, icon: PesoSign, statBg: 'bg-purple-50', iconBg: 'bg-purple-100', iconColor: 'text-purple-600' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-blue-600" size={40} />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Pending Payments"
        subtitle="Outstanding student payment balances"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Finance' }, { label: 'Pending Payments' }]}
        actions={
          <ActionButton icon={Download} variant="outline" size="sm" onClick={handleExportCSV}>Export CSV</ActionButton>
        }
      />

      <div className="flex flex-row justify-between gap-4 mb-5">
        {statCards.map((stat, index) => (
          <div key={index} className={`${stat.statBg} rounded-2xl p-4 flex-1 border border-transparent`}>
            <div className="flex items-center justify-between mb-3">
              <div className={`w-10 h-10 ${stat.iconBg} rounded-xl flex items-center justify-center`}>
                <stat.icon size={20} className={stat.iconColor} />
              </div>
            </div>
            <p className="text-xl sm:text-2xl font-bold text-gray-800">{stat.value}</p>
            <p className="text-xs sm:text-sm text-gray-500 mt-0.5">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Tabs: graduates keep their balances but sit in their own tab, so the
          working list stays readable. */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {(() => {
          const grad = payments.filter(p => isGraduatedRecord(p))
          const active = payments.filter(p => !isGraduatedRecord(p))
          const gradTotal = grad.reduce((s, p) => s + Number(p.balance || 0), 0)
          const tabs = [
            ['all', 'All Pending', payments.length, null],
            ['active', 'Active', active.length, null],
            ['graduated', 'Graduated', grad.length, gradTotal],
          ]
          return tabs.map(([id, label, count, total]) => (
            <button key={id} onClick={() => { setStatusTab(id); setCurrentPage(1) }}
              className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
                statusTab === id
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
              }`}>
              {label}
              <span className={`ml-1.5 text-xs ${statusTab === id ? 'text-blue-100' : 'text-gray-400'}`}>{count}</span>
              {total != null && total > 0 && (
                <span className={`ml-2 text-xs ${statusTab === id ? 'text-blue-100' : 'text-gray-400'}`}>
                  (₱{Number(total).toLocaleString()})
                </span>
              )}
            </button>
          ))
        })()}
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-4 mb-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800 text-sm flex items-center gap-2">
            <Filter size={14} className="text-blue-600" /> Filters
          </h3>
          {(search || selectedGrade || selectedSection || selectedRange !== 'all') && (
            <button onClick={resetFilters} className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1">
              <X size={12} /> Reset
            </button>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="text" placeholder="Search student or LRN..." value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900" />
          </div>
          <select value={selectedGrade} onChange={(e) => setSelectedGrade(e.target.value)}
            className="px-3 py-2.5 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900">
            <option value="">All Grades</option>
            {gradeLevels.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
          <select value={selectedSection} onChange={(e) => setSelectedSection(e.target.value)}
            className="px-3 py-2.5 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900">
            <option value="">All Sections</option>
            {uniqueSections.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={selectedRange} onChange={(e) => setSelectedRange(e.target.value)}
            className="px-3 py-2.5 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900">
            {balanceRanges.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        {filteredPayments.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center mb-4">
              <CheckCircle size={28} className="text-green-600" />
            </div>
            <p className="text-gray-600 font-medium text-lg mb-1">All caught up!</p>
            <p className="text-gray-400 text-sm">
              {search || selectedGrade || selectedSection || selectedRange !== 'all' ? 'No results match your filters' : 'No pending payments found'}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px]">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr className="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    <th className="px-4 py-3.5">LRN</th>
                    <th className="px-4 py-3.5">Student Name</th>
                    <th className="px-4 py-3.5 hidden sm:table-cell">Grade</th>
                    <th className="px-4 py-3.5 hidden md:table-cell">Section</th>
                    <th className="px-4 py-3.5 text-right">Total Tuition</th>
                    <th className="px-4 py-3.5 text-right hidden sm:table-cell">Amount Paid</th>
                    <th className="px-4 py-3.5 text-right">Balance</th>
                    <th className="px-4 py-3.5 hidden lg:table-cell">Last Payment</th>
                    <th className="px-4 py-3.5 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50 text-sm">
                  {paginatedPayments.map((payment) => (
                    <tr key={payment.id} className="hover:bg-gray-50 transition-colors group">
                      <td className="px-4 py-3.5">
                        <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded-lg text-gray-600">{payment.lrn}</span>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center text-white text-xs font-semibold shrink-0">
                            {(payment.studentName || '?')[0]?.toUpperCase()}
                          </div>
                          <span className="font-medium text-gray-800">{payment.studentName}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 hidden sm:table-cell text-gray-600">{payment.grade}</td>
                      <td className="px-4 py-3.5 hidden md:table-cell text-gray-600">{payment.section}</td>
                      <td className="px-4 py-3.5 text-right font-semibold text-gray-800">₱{payment.total_tuition.toLocaleString()}</td>
                      <td className="px-4 py-3.5 text-right text-green-600 hidden sm:table-cell">₱{payment.amount_paid.toLocaleString()}</td>
                      <td className="px-4 py-3.5 text-right">
                        <span className={`inline-flex px-2 py-1 rounded-lg text-xs font-semibold ${getBalanceColor(payment.balance, payment.total_tuition)}`}>
                          ₱{payment.balance.toLocaleString()}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 hidden lg:table-cell text-gray-500 text-xs">
                        {payment.last_payment_date ? new Date(payment.last_payment_date).toLocaleDateString() : 'No payments yet'}
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center justify-center gap-1">
                          {/* Collection happens in the Cashier. This page is a
                              record of who owes what, so it no longer collects. */}
                          <button onClick={() => handleViewStudent(payment)}
                            className="p-2 hover:bg-blue-50 rounded-lg text-blue-600 transition-colors"
                            title="View Student">
                            <Eye size={15} />
                          </button>
                          <button onClick={() => handlePrintStatementFor(payment)}
                            className="p-2 hover:bg-violet-50 rounded-lg text-violet-600 transition-colors"
                            title="Print Statement">
                            <Printer size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
                <p className="text-xs text-gray-500">
                  Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}-{Math.min(currentPage * ITEMS_PER_PAGE, filteredPayments.length)} of {filteredPayments.length}
                </p>
                <div className="flex items-center gap-1">
                  <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}
                    className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed text-gray-600">
                    <ChevronLeft size={16} />
                  </button>
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                    <button key={page} onClick={() => setCurrentPage(page)}
                      className={`w-8 h-8 rounded-lg text-xs font-medium transition-colors ${page === currentPage ? 'bg-blue-600 text-white' : 'hover:bg-gray-100 text-gray-600'}`}>
                      {page}
                    </button>
                  ))}
                  <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}
                    className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed text-gray-600">
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>


      {showViewStudent && viewingStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowViewStudent(false)} />
          <div className="relative bg-white rounded-2xl shadow-2xl z-10 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between rounded-t-2xl z-10">
              <h2 className="text-lg font-semibold text-gray-900">Student Profile</h2>
              <button onClick={() => setShowViewStudent(false)} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
                <X size={18} />
              </button>
            </div>
            <div className="p-6">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center text-white font-bold text-lg">
                  {(viewingStudent.studentName || '?')[0]?.toUpperCase()}
                </div>
                <div>
                  <p className="font-semibold text-gray-900 text-lg">{viewingStudent.studentName}</p>
                  <p className="text-sm text-gray-500">LRN: {viewingStudent.lrn}</p>
                </div>
              </div>

              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">Grade / Section</span>
                  <span className="text-sm font-medium text-gray-800">{viewingStudent.grade} - {viewingStudent.section}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">Gender</span>
                  <span className="text-sm font-medium text-gray-800">{viewingStudent.gender || 'N/A'}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">Birthday</span>
                  <span className="text-sm font-medium text-gray-800">{viewingStudent.birthday || 'N/A'}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">Contact</span>
                  <span className="text-sm font-medium text-gray-800">{viewingStudent.contact || 'N/A'}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">Address</span>
                  <span className="text-sm font-medium text-gray-800 text-right max-w-[180px]">{viewingStudent.address || viewingStudent.guardian_address || 'N/A'}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">Guardian</span>
                  <span className="text-sm font-medium text-gray-800">{viewingStudent.guardian || 'N/A'}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">Guardian Contact</span>
                  <span className="text-sm font-medium text-gray-800">{viewingStudent.guardian_contact || 'N/A'}</span>
                </div>
              </div>

              {viewingStudent.owed_items?.length > 0 && (
                <div className="mt-4 bg-white rounded-xl border border-gray-100 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold text-gray-700">Owed Items</h4>
                    <span className="text-xs text-gray-500">
                      Item balance: ₱{parseFloat(viewingStudent.item_balance || 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {viewingStudent.owed_items.map(item => (
                      <div key={item.id} className="flex items-center justify-between gap-3 py-2 px-3 rounded-lg bg-gray-50">
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-800 truncate">{item.item_name}</p>
                          <p className="text-xs text-gray-500">
                            {item.qty} × ₱{parseFloat(item.unit_price).toLocaleString()} · paid ₱{parseFloat(item.amount_paid).toLocaleString()}
                            {item.source === 'tuition' && <span className="ml-1 text-purple-600">(tuition installment)</span>}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-sm font-bold text-amber-600">₱{parseFloat(item.balance).toLocaleString()}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  {viewingStudent.tuition_charge_balance > 0 && (
                    <p className="text-xs text-gray-500 mt-3 pt-3 border-t border-gray-100">
                      Tuition installments still owed: ₱{parseFloat(viewingStudent.tuition_charge_balance).toLocaleString()}
                      <span className="ml-1">(already included in the tuition balance above — not added again)</span>
                    </p>
                  )}
                </div>
              )}

              <div className="bg-gray-50 rounded-xl p-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-3">Tuition Summary</h4>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Total</p>
                    <p className="text-base font-bold text-gray-800">₱{viewingStudent.total_tuition?.toLocaleString() || 0}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Paid</p>
                    <p className="text-base font-bold text-green-600">₱{viewingStudent.amount_paid?.toLocaleString() || 0}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Balance</p>
                    {/* Tuition only - must not include item balances, which are
                        listed separately under Owed Items. */}
                    <p className="text-base font-bold text-red-600">₱{parseFloat(viewingStudent.tuition_balance ?? viewingStudent.balance ?? 0).toLocaleString()}</p>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>Payment Progress</span>
                    <span>{viewingStudent.total_tuition > 0 ? Math.round((viewingStudent.amount_paid / viewingStudent.total_tuition) * 100) : 0}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className={`h-2 rounded-full ${getBalanceColor(viewingStudent.balance, viewingStudent.total_tuition).split(' ')[0].replace('text-', 'bg-')}`}
                      style={{ width: `${viewingStudent.total_tuition > 0 ? (viewingStudent.amount_paid / viewingStudent.total_tuition) * 100 : 0}%` }} />
                  </div>
                </div>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-100 flex justify-end">
              <ActionButton variant="secondary" onClick={() => setShowViewStudent(false)}>Close</ActionButton>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className={`fixed bottom-6 left-6 z-50 px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white transition-all animate-slide-up flex items-center gap-2 ${toast.type === 'error' ? 'bg-red-600' : 'bg-gray-800'}`}>
          {toast.type === 'error' ? <AlertTriangle size={16} /> : <Check size={16} />}
          {toast.message}
        </div>
      )}

      {/* ---------------- printable statement of account ----------------
          NOT a receipt: this page takes no money. It lists the student's
          owed items and their current tuition balance so the family knows
          what to settle - payment happens in the Cashier. */}
      {showStatement && statement && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowStatement(false)} />
          <div className="relative bg-white rounded-2xl shadow-2xl z-10 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white px-6 py-4 border-b border-gray-100 flex items-center justify-between z-10 no-print">
              <h2 className="text-lg font-semibold text-gray-900">Statement of Account</h2>
              <button onClick={() => setShowStatement(false)} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-400">
                <X size={18} />
              </button>
            </div>

            <div ref={statementRef} className="statement-content bg-white p-6">
              {/* school header */}
              <div className="flex items-center gap-3 border-b-2 border-gray-800 pb-3 mb-4">
                {printLogo && <img src={printLogo} alt="" className="w-14 h-14 object-contain shrink-0" />}
                <div className="flex-1 text-center">
                  <p className="text-lg font-bold text-gray-900 uppercase">{config?.school_name || 'School Name'}</p>
                  {config?.full_address && <p className="text-xs text-gray-600">{config.full_address}</p>}
                  {config?.contact_info && <p className="text-xs text-gray-600">{config.contact_info}</p>}
                  <p className="text-sm font-semibold text-gray-800 mt-2 tracking-wide uppercase">Statement of Account</p>
                </div>
              </div>

              {/* student info */}
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs mb-4">
                <p><span className="text-gray-500">Student:</span> <span className="font-semibold text-gray-900">{statement.studentName}</span></p>
                <p><span className="text-gray-500">LRN:</span> <span className="font-medium text-gray-900">{statement.lrn || '—'}</span></p>
                <p>
                  <span className="text-gray-500">{statement.isGraduated ? 'Status:' : 'Grade / Section:'}</span>{' '}
                  <span className="font-medium text-gray-900">
                    {statement.isGraduated
                      ? `Graduated${statement.graduatedSy ? ` · S.Y. ${statement.graduatedSy}` : ''}`
                      : `${statement.grade} — ${statement.section}`}
                  </span>
                </p>
                <p><span className="text-gray-500">Date prepared:</span> <span className="font-medium text-gray-900">{new Date(statement.generatedAt).toLocaleDateString('en-PH', { year: 'numeric', month: 'long', day: 'numeric' })}</span></p>
                {statement.adviser && (
                  <p className="col-span-2"><span className="text-gray-500">Class Adviser:</span> <span className="font-medium text-gray-900">{statement.adviser}</span></p>
                )}
              </div>

              {/* tuition summary */}
              <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">Tuition</p>
              <table className="w-full text-xs border border-gray-200 mb-4">
                <tbody>
                  <tr className="border-b border-gray-100">
                    <td className="px-3 py-1.5 text-gray-600">Total Tuition Fee</td>
                    <td className="px-3 py-1.5 text-right font-medium text-gray-900">₱{statement.totalTuition.toLocaleString()}</td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="px-3 py-1.5 text-gray-600">Amount Paid</td>
                    <td className="px-3 py-1.5 text-right font-medium text-gray-900">₱{statement.amountPaid.toLocaleString()}</td>
                  </tr>
                  <tr className="bg-red-50">
                    <td className="px-3 py-1.5 font-semibold text-gray-900">Current Tuition Balance</td>
                    <td className="px-3 py-1.5 text-right font-bold text-red-700">₱{statement.tuitionBalance.toLocaleString()}</td>
                  </tr>
                </tbody>
              </table>

              {/* owed items */}
              <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">Owed Items</p>
              {statement.owedItems.length === 0 ? (
                <p className="text-xs text-gray-500 border border-dashed border-gray-200 rounded-lg p-3 mb-4">No item charges on this account.</p>
              ) : (
                <table className="w-full text-xs border border-gray-200 mb-4">
                  <thead className="bg-gray-50 text-gray-600 uppercase">
                    <tr>
                      <th className="px-3 py-1.5 text-left font-medium">Item</th>
                      <th className="px-3 py-1.5 text-center font-medium">Qty</th>
                      <th className="px-3 py-1.5 text-right font-medium">Price</th>
                      <th className="px-3 py-1.5 text-right font-medium">Paid</th>
                      <th className="px-3 py-1.5 text-right font-medium">Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statement.owedItems.map((it, i) => (
                      <tr key={i} className="border-t border-gray-100">
                        <td className="px-3 py-1.5 text-gray-800">
                          {it.name}
                          {it.isTuition && <span className="ml-1 text-[10px] text-purple-600">(tuition installment)</span>}
                        </td>
                        <td className="px-3 py-1.5 text-center text-gray-600">{it.qty}</td>
                        <td className="px-3 py-1.5 text-right text-gray-600">₱{it.unitPrice.toLocaleString()}</td>
                        <td className="px-3 py-1.5 text-right text-gray-600">₱{it.amountPaid.toLocaleString()}</td>
                        <td className="px-3 py-1.5 text-right font-semibold text-amber-700">₱{it.balance.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {/* total due */}
              <div className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-lg px-4 py-2.5 mb-4">
                <span className="text-sm font-semibold text-gray-900">Total Amount Due</span>
                <span className="text-lg font-bold text-amber-800">₱{statement.totalDue.toLocaleString()}</span>
              </div>

              {/* footer */}
              <div className="flex items-end justify-between pt-6 text-xs text-gray-600">
                <div>
                  <p className="text-gray-500">Prepared by</p>
                  <p className="border-t border-gray-400 mt-4 pt-1 font-medium text-gray-800">{statement.preparedBy}</p>
                </div>
                <p className="text-[10px] text-gray-400 max-w-[220px] text-right">
                  Please settle outstanding balances at the Cashier. This statement is not an official receipt.
                </p>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-100 flex flex-wrap gap-2 no-print">
              <ActionButton variant="secondary" size="sm" onClick={() => setShowStatement(false)}>Close</ActionButton>
              <ActionButton size="sm" onClick={handlePrintStatement} icon={Printer}>Print Statement</ActionButton>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slide-up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .animate-slide-up { animation: slide-up 0.3s ease-out; }
      `}</style>
    </div>
  )
}