import { useState, useEffect, useMemo } from 'react'
import PageHeader from '../components/PageHeader'
import ActionButton from '../components/ActionButton'
import { financeAPI, studentsAPI } from '../services/api'
import { useSchoolConfig } from '../contexts/SchoolConfigContext'
import { storage } from '../services/storage'
import {
  TrendingUp, Loader2, Printer,
  Download, Search, X, Filter, ChevronLeft, ChevronRight,
  ArrowUpDown, Banknote, CreditCard, Receipt, AlertCircle, Check,
  Wallet, Coins, Pencil, Trash2
} from 'lucide-react'
import PesoSign from '../components/PesoSign'
import { printHtml, buildRevenueReportHtml } from '../utils/printDocument'

const ITEMS_PER_PAGE = 15

const statusOptions = [
  { value: 'all', label: 'All Status' },
  { value: 'paid', label: 'Paid' },
  { value: 'partial', label: 'Partial' },
  { value: 'pending', label: 'Pending' },
  { value: 'unpaid', label: 'Unpaid' },
]

export default function RevenuePage() {
  const { config, printLogo } = useSchoolConfig()
  const [loading, setLoading] = useState(true)
  const [transactions, setTransactions] = useState([])
  const [filteredTransactions, setFilteredTransactions] = useState([])
  const [toast, setToast] = useState(null)
  const [editingEntry, setEditingEntry] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [savingEntry, setSavingEntry] = useState(false)
  const [deletingEntry, setDeletingEntry] = useState(false)
  const [error, setError] = useState(null)

  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [selectedType, setSelectedType] = useState('All')
  const [selectedMethod, setSelectedMethod] = useState('All')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)

  const [revenueTotals, setRevenueTotals] = useState({
    total_revenue: 0,
    total_pos: 0,
    total_tuition: 0,
    total_assessment: 0,
    total_dorm: 0,
    total_tour: 0,
    total_graduation: 0,
    total_general: 0,
    total_transactions: 0,
    pos_count: 0,
    tuition_count: 0,
    assessment_count: 0,
    dorm_count: 0,
    tour_count: 0,
    graduation_count: 0,
    general_count: 0,
  })

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }

  const fetchData = async () => {
    try {
      setLoading(true)
      const revenueData = await financeAPI.getRevenue().catch(() => ({ revenue: [], totals: {} }))

      const revenueList = Array.isArray(revenueData) ? revenueData : (revenueData.results || revenueData.revenue || [])

      if (revenueData.totals) {
        setRevenueTotals(prev => ({ ...prev, ...revenueData.totals }))
      }

      const mergedTransactions = revenueList.map(r => {
        let source = r.type || 'Revenue'
        let paymentType = r.type || r.payment_type || 'Revenue'

        if (r.type === 'Tuition' || (r.products && r.products[0] && (r.products[0].name?.toLowerCase().includes('tuition') || r.products[0].name === 'Tuition Fee'))) {
          source = 'Tuition'
          paymentType = 'Tuition'
        } else if (['Miscellaneous', 'Laboratory', 'Assessment', 'Other'].includes(r.type)) {
          source = r.type
          paymentType = r.type
        } else if (r.type === 'Assessment') {
          source = 'Assessment'
          paymentType = 'Assessment'
        } else if (r.type === 'Dorm') {
          source = 'Dorm'
          paymentType = 'Dorm'
        } else if (r.type === 'Tour') {
          source = 'Tour'
          paymentType = 'Tour'
        } else if (r.type === 'Graduation') {
          source = 'Graduation'
          paymentType = 'Graduation'
        } else if (r.type === 'POS') {
          source = 'POS'
          paymentType = 'POS'
        }

        return {
          ...r,
          type: paymentType,
          source: source,
          payerName: r.customer || r.student_name || r.name || 'N/A',
          method: r.payment_method || r.method || 'Cash',
          status: r.status || 'paid',
          date: r.date || r.created_at || r.payment_date || r.transaction_date,
          amount: parseFloat(r.amount) || parseFloat(r.total) || 0,
          reference_no: r.reference || r.reference_number || r.reference_no || `-`,
        }
      })

      const sortedTransactions = mergedTransactions.sort((a, b) => {
        const dateA = new Date(a.date || a.created_at || 0)
        const dateB = new Date(b.date || b.created_at || 0)
        return dateB - dateA
      })

      setTransactions(sortedTransactions)
    } catch (error) {
      console.error('Error fetching revenue data:', error)
      showToast('Failed to load revenue data', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [startDate, endDate, selectedType, selectedMethod, searchQuery, transactions, currentPage])

  const applyFilters = () => {
    let filtered = [...transactions]

    if (startDate) filtered = filtered.filter(t => {
      const d = new Date(t.date || t.created_at || t.payment_date)
      return d >= new Date(startDate)
    })
    if (endDate) filtered = filtered.filter(t => {
      const d = new Date(t.date || t.created_at || t.payment_date)
      return d <= new Date(endDate + 'T23:59:59')
    })
    if (selectedType !== 'All') {
      if (selectedType === 'General') {
        filtered = filtered.filter(t => ['Miscellaneous', 'Laboratory', 'Assessment', 'Other'].includes(t.type))
      } else {
        filtered = filtered.filter(t => t.type?.toLowerCase() === selectedType.toLowerCase())
      }
    }
    if (selectedMethod !== 'All') {
      filtered = filtered.filter(t => {
        const method = (t.method || 'Cash').toLowerCase().replace('_', '')
        const selected = selectedMethod.toLowerCase().replace('_', '')
        return method === selected || (selected === 'cash' && !method.includes('gcash') && !method.includes('card') && !method.includes('bank')) || (selected === 'gcash' && method.includes('gcash'))
      })
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      filtered = filtered.filter(t =>
        (t.payerName || '').toLowerCase().includes(q) ||
        (t.reference_no || t.id?.toString() || '').toLowerCase().includes(q) ||
        (t.type || '').toLowerCase().includes(q) ||
        (t.source || '').toLowerCase().includes(q)
      )
    }

    setFilteredTransactions(filtered)
    setCurrentPage(1)
  }

  const resetFilters = () => {
    setStartDate('')
    setEndDate('')
    setSelectedType('All')
    setSelectedMethod('All')
    setSearchQuery('')
    setCurrentPage(1)
  }

  const paginatedTransactions = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE
    return filteredTransactions.slice(start, start + ITEMS_PER_PAGE)
  }, [filteredTransactions, currentPage])

  const totalPages = Math.ceil(filteredTransactions.length / ITEMS_PER_PAGE)

  const totals = useMemo(() => {
    const totalIncome = filteredTransactions.reduce((sum, t) => sum + t.amount, 0)
    // Tuition is the bulk of what the school collects; everything else
    // (products, charges, tours, dorm, graduation) is "other payments".
    const tuition = filteredTransactions
      .filter(t => t.kind === 'tuition' || t.type === 'Tuition')
      .reduce((sum, t) => sum + t.amount, 0)
    const other = totalIncome - tuition
    const totalRecords = filteredTransactions.length
    return { totalIncome, tuition, other, totalRecords }
  }, [filteredTransactions])

  const revenueBreakdown = useMemo(() => {
    const breakdown = {}

    const typeLabels = {
      'Tuition': 'Tuition',
      'Miscellaneous': 'Miscellaneous',
      'Laboratory': 'Laboratory',
      'Assessment': 'Assessment',
      'Other': 'Other',
      'Dorm': 'Dorm',
      'Tour': 'Tour',
      'Graduation': 'Graduation',
      'POS': 'POS',
    }

    filteredTransactions.forEach(t => {
      const type = t.type || 'Other'
      const displayType = typeLabels[type] || type
      if (!breakdown[displayType]) breakdown[displayType] = { type: displayType, count: 0, total: 0 }
      breakdown[displayType].count += 1
      breakdown[displayType].total += t.amount
    })

    return Object.values(breakdown).map(b => ({
      ...b,
      percent: totals.totalIncome > 0 ? ((b.total / totals.totalIncome) * 100).toFixed(1) : '0.0'
    })).sort((a, b) => b.total - a.total)
  }, [filteredTransactions, totals.totalIncome])

  // ---- correct / remove a single revenue entry ---------------------------
  // The amount is not editable: rewriting it would change financial history
  // without a matching payment. A wrong amount should be deleted and re-entered.
  const openEditEntry = (txn) => {
    setEditingEntry({
      txn,
      payment_method: txn.method || 'Cash',
      payment_type: txn.type || '',
      remarks: txn.remarks || '',
    })
    setError(null)
  }

  const closeEditEntry = () => {
    setEditingEntry(null)
    setError(null)
  }

  const saveEditEntry = async () => {
    if (!editingEntry) return
    setSavingEntry(true)
    setError(null)
    const { txn, ...changes } = editingEntry
    try {
      await financeAPI.updateRevenueEntry(txn.kind, txn.id, changes)
      showToast('Revenue entry updated')
      closeEditEntry()
      await fetchData()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to update entry')
    } finally {
      setSavingEntry(false)
    }
  }

  const confirmDeleteEntry = async () => {
    if (!deleteTarget) return
    setDeletingEntry(true)
    setError(null)
    try {
      await financeAPI.deleteRevenueEntry(deleteTarget.kind, deleteTarget.id)
      showToast('Revenue entry deleted')
      setDeleteTarget(null)
      await fetchData()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to delete entry')
    } finally {
      setDeletingEntry(false)
    }
  }

  const handleExportCSV = () => {
    const headers = ['Date', 'Receipt No.', 'Payer Name', 'Type', 'Source', 'Amount', 'Method', 'Status']
    const rows = filteredTransactions.map(t => [
      new Date(t.date || t.created_at || t.payment_date).toLocaleDateString(),
      t.reference_no || `#${t.id}` || '-',
      t.payerName || 'N/A',
      t.type || 'N/A',
      t.source || t.type || 'N/A',
      t.amount.toLocaleString(),
      t.method || 'Cash',
      t.status || 'N/A',
    ])
    const csvContent = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n')
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `revenue_report_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
    showToast('Revenue report exported successfully')
  }

  const statCards = [
    { label: 'Total Collected', value: `₱${totals.totalIncome.toLocaleString()}`, icon: TrendingUp, statBg: 'bg-green-50', iconBg: 'bg-green-100', iconColor: 'text-green-600', printBorder: 'border-green-200' },
    { label: 'Tuition', value: `₱${totals.tuition.toLocaleString()}`, icon: Wallet, statBg: 'bg-blue-50', iconBg: 'bg-blue-100', iconColor: 'text-blue-600', printBorder: 'border-blue-200' },
    { label: 'Other Payments', value: `₱${totals.other.toLocaleString()}`, icon: Coins, statBg: 'bg-amber-50', iconBg: 'bg-amber-100', iconColor: 'text-amber-600', printBorder: 'border-amber-200' },
    { label: 'Payments Received', value: totals.totalRecords.toLocaleString(), icon: Receipt, statBg: 'bg-purple-50', iconBg: 'bg-purple-100', iconColor: 'text-purple-600', printBorder: 'border-purple-200' },
  ]

  const getStatusBadge = null
  // Staff name for printed reports (bottom-right footer)
  const getPrintedBy = () => {
    try {
      const u = JSON.parse(storage.getSync('user') || 'null')
      return [u?.firstName, u?.lastName].filter(Boolean).join(' ') || u?.username || 'Staff'
    } catch { return 'Staff' }
  }

  // ---- printable reports (A4 portrait, Electron-safe) ---------------------
  const reportConfig = () => ({
    school_name: config?.school_name,
    full_address: config?.address_line1
      ? [config.address_line1, config.city, config.province].filter(Boolean).join(', ')
      : '',
    contact_info: (() => {
      const tel = config?.phone_number || config?.mobile_number
      return [tel && `Tel. No. ${tel}`, config?.email && `Email ${config.email}`].filter(Boolean).join(' / ')
    })(),
    // printLogo is the logo inlined as a data URI — the only form that
    // reliably renders inside the self-contained print document.
    logo_url: printLogo || config?.logo_url || config?.logo,
  })

  const dateRangeText = () =>
    (startDate || endDate)
      ? `Period: ${startDate || '...'} to ${endDate || '...'}`
      : 'All records'

  const handlePrintReport = async () => {
    try {
      const extras = [
        selectedType !== 'All' && `Type: ${selectedType}`,
        selectedMethod !== 'All' && `Method: ${selectedMethod}`,
      ].filter(Boolean).join(' · ')
      await printHtml(
        buildRevenueReportHtml({
          config: reportConfig(),
          logo: printLogo || config?.logo_url || config?.logo,
          dateRangeText: dateRangeText() + (extras ? ` · ${extras}` : ''),
          totals: revenueTotals,
          includeTerminals: false,
          preparedBy: getPrintedBy(),
          generatedAt: new Date().toLocaleString('en-PH'),
        }),
        { pageSize: 'A4', title: 'Revenue Report' }
      )
    } catch (e) {
      showToast(e.message || 'Print failed', 'error')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-blue-600" size={40} />
      </div>
    )
  }

  return (
    <div className="print-report min-h-0">
      <div className="print-only">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
          {(config?.logo_url || config?.logo) && (
            <img src={config.logo_url || config.logo} alt="" style={{ width: 40, height: 40, objectFit: 'contain', flexShrink: 0 }} />
          )}
          <div style={{ flex: 1, textAlign: 'center' }}>
            <p style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', lineHeight: 1.1, margin: 0 }}>
              {config?.school_name?.toUpperCase() || 'USAT COLLEGE SAGAY CITY INC.'}
            </p>
            <p style={{ fontSize: '8px', margin: '1px 0' }}>
              {config?.address_line1 ? [config.address_line1, config.city, config.province].filter(Boolean).join(', ') : 'National Highway, Pob 1, Sagay City, Neg, Occ.'}
            </p>
            <p style={{ fontSize: '8px', margin: '1px 0' }}>
              {config?.phone_number || config?.email
                ? [config?.phone_number && `Tel. No. ${config.phone_number}`, config?.email && `Email ${config.email}`].filter(Boolean).join(' / ')
                : 'Tel. No. 034-722-8905 / Email usat1985@yahoo.com'}
            </p>
          </div>
          {/* Mirrors the logo on the right so the text block stays centred on
              the page while the logo remains flush left beside it. */}
          <span style={{ width: 40, flexShrink: 0 }} aria-hidden="true" />
        </div>
        <div style={{ borderBottom: '1px solid #000', margin: '4px 0 8px 0' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
          <div>
            <p style={{ fontSize: '12px', fontWeight: 700, margin: 0 }}>REVENUE REPORT</p>
            <p style={{ fontSize: '9px', margin: 0, color: '#333' }}>
              {(startDate || endDate) ? `Period: ${startDate || '...'} to ${endDate || '...'}` : 'All records'}
              {selectedType !== 'All' && ` · Type: ${selectedType}`}
              {selectedMethod !== 'All' && ` · Method: ${selectedMethod}`}
            </p>
          </div>
          <p style={{ fontSize: '8px', margin: 0 }}>
            Printed: {new Date().toLocaleDateString('en-PH')} {new Date().toLocaleTimeString('en-PH', { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
      <div className="no-print">
      <PageHeader
        title="Revenue Reports"
        subtitle="Financial reports and analytics"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Finance' }, { label: 'Revenue' }]}
        actions={
          <div className="flex flex-wrap gap-2">
            <ActionButton icon={Download} variant="outline" size="sm" onClick={handleExportCSV}>Export CSV</ActionButton>
            <ActionButton icon={Printer} size="sm" onClick={handlePrintReport} className="no-print">Print Report</ActionButton>
          </div>
        }
      />
      </div>

      <div className="flex flex-row justify-between gap-4 mb-5 no-print">
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

      <div className="bg-white rounded-2xl border border-gray-100 p-4 mb-5 no-print">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800 text-sm flex items-center gap-2">
            <Filter size={14} className="text-blue-600" /> Filters
          </h3>
          <button onClick={resetFilters} className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1">
            <X size={12} /> Reset
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Start Date</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">End Date</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Payment Type</label>
            <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900">
              <option value="All">All Types</option>
              <option value="Tuition">Tuition</option>
              <option value="Miscellaneous">Miscellaneous</option>
              <option value="Laboratory">Laboratory</option>
              <option value="Assessment">Assessment</option>
              <option value="Other">Other</option>
              <option value="Dorm">Dorm</option>
              <option value="Tour">Tour</option>
              <option value="Graduation">Graduation</option>
              <option value="POS">POS</option>
              <option value="General">All General</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Payment Method</label>
            <select value={selectedMethod} onChange={(e) => setSelectedMethod(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900">
              <option value="All">All Methods</option>
              <option value="Cash">Cash</option>
              <option value="GCash">GCash</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Search</label>
            <input type="text" placeholder="Search payer, reference..."
              value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900" />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden mb-5">
        <div className="px-4 py-3 border-b border-gray-100">
          <h3 className="font-semibold text-gray-800 text-sm">Revenue Breakdown</h3>
        </div>
        {revenueBreakdown.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10">
            <Receipt size={28} className="text-gray-300 mb-2" />
            <p className="text-sm text-gray-500">No revenue data available</p>
          </div>
        ) : (
          <div className="overflow-x-auto overflow-y-visible">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Payment Type</th>
                  <th className="px-4 py-3 text-right">No. of Transactions</th>
                  <th className="px-4 py-3 text-right">Total Amount</th>
                  <th className="px-4 py-3 text-right">% of Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {revenueBreakdown.map((item, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{item.type}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{item.count}</td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-800">₱{item.total.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 bg-gray-100 rounded-full h-1.5">
                          <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${item.percent}%` }} />
                        </div>
                        <span className="text-xs text-gray-500 w-10 text-right">{item.percent}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-50 border-t border-gray-100">
                <tr>
                  <td className="px-4 py-3 font-semibold text-gray-800">Total</td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-800">{revenueBreakdown.reduce((s, i) => s + i.count, 0)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-800">₱{totals.totalIncome.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-800">100%</td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h3 className="font-semibold text-gray-800 text-sm">Transaction History</h3>
          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="text" placeholder="Search by payer or receipt..."
              value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900" />
          </div>
        </div>

        {filteredTransactions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14">
            <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mb-4">
              <Receipt size={24} className="text-gray-400" />
            </div>
            <p className="text-gray-600 font-medium">No transactions found</p>
            <p className="text-gray-400 text-sm mt-1">
              {searchQuery || startDate || endDate || selectedType !== 'All' || selectedMethod !== 'All' ? 'Try adjusting your filters' : 'No payment records available'}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto overflow-y-visible">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Date</th>
                  <th className="px-4 py-3 text-left">Receipt No.</th>
                  <th className="px-4 py-3 text-left">Payer Name</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left hidden lg:table-cell">Item</th>
                  <th className="px-4 py-3 text-right">Amount</th>
                  <th className="px-4 py-3 text-left hidden md:table-cell">Method</th>
                  {/* Maintenance only - never part of the printed record. */}
                  <th className="px-4 py-3 text-right no-print">Actions</th>
                </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {paginatedTransactions.map((txn) => (
                    <tr key={txn.entry_id || `${txn.kind}-${txn.id}` || `${txn.reference_no}-${txn.date}`} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {new Date(txn.date || txn.created_at || txn.payment_date).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded-lg text-gray-600">
                          {txn.reference_no || `#${txn.id}` || '-'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center text-white text-xs font-semibold shrink-0">
                            {(txn.payerName || '?')[0]?.toUpperCase()}
                          </div>
                          <span className="font-medium text-gray-800 text-sm truncate max-w-[140px]">{txn.payerName}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell text-gray-600 whitespace-nowrap">{txn.type || 'N/A'}</td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <span className="text-gray-600 text-xs truncate max-w-[160px] block">
                          {txn.products && txn.products[0]
                            ? `${txn.products[0].name}${txn.products[0].size ? ` (${txn.products[0].size})` : ''}`
                            : txn.remarks || '-'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-800 whitespace-nowrap">
                        ₱{txn.amount.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <div className="flex items-center gap-1.5 text-gray-500">
                          {txn.method?.toLowerCase().includes('gcash') ? <CreditCard size={13} /> : txn.method?.toLowerCase().includes('bank') || txn.method?.toLowerCase().includes('card') ? <Banknote size={13} /> : <Wallet size={13} />}
                          <span className="capitalize text-xs">{txn.method || 'Cash'}</span>
                        </div>
                      </td>
                      {/* Maintenance actions. no-print keeps them out of the
                          printed report, which is the permanent record. */}
                      <td className="px-4 py-3 text-right whitespace-nowrap no-print">
                        <div className="inline-flex items-center gap-1">
                          <button onClick={() => openEditEntry(txn)}
                            className="p-1.5 rounded-lg text-gray-400 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                            title="Correct this entry">
                            <Pencil size={14} />
                          </button>
                          <button onClick={() => { setDeleteTarget(txn); setError(null) }}
                            className="p-1.5 rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                            title="Delete this entry">
                            <Trash2 size={14} />
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
                  Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}-{Math.min(currentPage * ITEMS_PER_PAGE, filteredTransactions.length)} of {filteredTransactions.length}
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

      <div className="print-only print-staff-footer">
        <div>
          <p style={{ fontSize: '10px', fontWeight: 600, margin: 0 }}>{getPrintedBy()}</p>
          <p style={{ fontSize: '8px', margin: 0, borderTop: '1px solid #000', paddingTop: '2px' }}>Prepared by (Staff)</p>
        </div>
      </div>

      {toast && (
        <div className={`fixed bottom-6 left-6 z-50 px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white transition-all animate-slide-up flex items-center gap-2 ${toast.type === 'error' ? 'bg-red-600' : 'bg-gray-800'}`}>
          {toast.type === 'error' ? <AlertCircle size={16} /> : <Check size={16} />}
          {toast.message}
        </div>
      )}

      {/* ---------------- edit revenue entry ---------------- */}
      {editingEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={closeEditEntry} />
          <div className="relative bg-white rounded-2xl shadow-2xl z-10 w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1 flex items-center gap-2">
              <Pencil size={16} className="text-blue-600" /> Correct Entry
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              {editingEntry.txn.payerName} &middot; {editingEntry.txn.type} &middot;
              {' '}<span className="font-mono">₱{Number(editingEntry.txn.amount).toLocaleString()}</span>
            </p>

            {error && (
              <div className="mb-3 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Method</label>
                <select value={editingEntry.payment_method}
                  onChange={(e) => setEditingEntry({ ...editingEntry, payment_method: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  {['Cash', 'GCash', 'Bank Transfer', 'Credit/Debit Card', 'Check'].map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Type</label>
                <input type="text" value={editingEntry.payment_type}
                  onChange={(e) => setEditingEntry({ ...editingEntry, payment_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Remarks</label>
                <input type="text" value={editingEntry.remarks}
                  onChange={(e) => setEditingEntry({ ...editingEntry, remarks: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>

            <p className="text-[11px] text-gray-400 mt-3">
              The amount is not editable here. If it is wrong, delete this entry
              and record the payment again.
            </p>

            <div className="flex justify-end gap-2 mt-5">
              <ActionButton variant="secondary" onClick={closeEditEntry}>Cancel</ActionButton>
              <ActionButton onClick={saveEditEntry} loading={savingEntry}>Save Changes</ActionButton>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- delete revenue entry ---------------- */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setDeleteTarget(null)} />
          <div className="relative bg-white rounded-2xl shadow-2xl z-10 w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
              <AlertCircle size={18} className="text-red-600" /> Delete Entry
            </h3>
            <p className="text-sm text-gray-600">
              Delete the {deleteTarget.type} entry for
              {' '}<strong>{deleteTarget.payerName}</strong> of
              {' '}<span className="font-semibold">₱{Number(deleteTarget.amount).toLocaleString()}</span>?
            </p>
            <p className="text-xs text-gray-500 mt-2">
              This removes the underlying record, so it disappears from Revenue,
              the cashier ledger and the SOA payment history. It cannot be undone.
            </p>

            {error && (
              <div className="mt-3 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <div className="flex justify-end gap-2 mt-5">
              <ActionButton variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</ActionButton>
              <ActionButton onClick={confirmDeleteEntry} loading={deletingEntry}
                className="bg-red-600 hover:bg-red-700">Delete</ActionButton>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slide-up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .animate-slide-up { animation: slide-up 0.3s ease-out; }
        .print-only { display: none !important; }
        @media print {
          @page { size: A4 landscape; margin: 0.5in; }
          /* Chromium drops background colours unless this is set, which
             strips the stat card tints from the printed report. */
          html, body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
          body * { visibility: hidden !important; }
          .print-report, .print-report * { visibility: visible !important; }
          .print-report { position: absolute !important; left: 0 !important; top: 0 !important; width: 100% !important; margin: 0 !important; padding: 0 !important; background: white !important; }
          .no-print, .no-print * { display: none !important; }
          .print-report .rounded-2xl { border-radius: 0 !important; }
          .print-report .border { border-width: 1px !important; }
          .print-report .shadow-sm { box-shadow: none !important; }
          .print-report table { width: 100% !important; border-collapse: collapse !important; }
          .print-report th, .print-report td { border: 1px solid #ddd !important; padding: 4px 8px !important; font-size: 11px !important; }
          .print-report .bg-white { background: white !important; }
          .print-report .bg-gray-50 { background: #f9fafb !important; }
          .print-only { display: block !important; visibility: visible !important; }
          .print-staff-footer { display: flex !important; justify-content: flex-end !important; margin-top: 24px !important; }
        }
      `}</style>
    </div>
  )
}