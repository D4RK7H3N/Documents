import { useState, useEffect, useMemo, useCallback } from 'react'
import PageHeader from '../components/PageHeader'
import ActionButton from '../components/ActionButton'
import { financeAPI } from '../services/api'
import { useSchoolConfig } from '../contexts/SchoolConfigContext'
import { storage } from '../services/storage'
import {
  Loader2, Printer, AlertCircle, Check, RotateCcw, Store, Receipt,
  Search, ChevronLeft, ChevronRight, TrendingUp, GraduationCap,
  CreditCard, Banknote, Wallet,
} from 'lucide-react'
import { printHtml, buildRevenueReportHtml, buildTerminalReportHtml } from '../utils/printDocument'
import { terminalAPI } from '../services/api'
import { useAuth } from '../context/AuthContext'

const ITEMS_PER_PAGE = 15

export default function StaffRevenuePage() {
  const { config, printLogo } = useSchoolConfig()
  const { user } = useAuth()
  // Only the super administrator sees every terminal; staff see their own
  // register's numbers and print their own total report.
  const isSuperAdmin = !!user?.is_superuser || !!user?.isAdmin
  const [loading, setLoading] = useState(true)
  const [byTerminal, setByTerminal] = useState([])
  const [transactions, setTransactions] = useState([])
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [selectedTerminal, setSelectedTerminal] = useState('All')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  // This register's name from the device registry — a staff user's own
  // terminal (falls back to the Unassigned bucket for browser sessions).
  const [myTerminal, setMyTerminal] = useState(null)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }

  // Server-side filtered: the revenue endpoint applies date_from/date_to to
  // the POS and tuition querysets before grouping by terminal, so the cards,
  // the table and the per-terminal printables all see the same period.
  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (startDate) params.date_from = startDate
      if (endDate) params.date_to = endDate
      const d = await financeAPI.getRevenue(params)
      setByTerminal(Array.isArray(d?.by_terminal) ? d.by_terminal : [])
      setTransactions(Array.isArray(d?.revenue) ? d.revenue : d?.results || [])
    } catch {
      showToast('Failed to load terminal revenue', 'error')
      setByTerminal([])
      setTransactions([])
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate])

  useEffect(() => { fetchData() }, [fetchData])

  useEffect(() => {
    let cancelled = false
    terminalAPI.getCurrent().then((d) => {
      const name = d?.terminal?.name || null
      if (!cancelled && name) setMyTerminal(name)
    }).catch(() => {})
    return () => { cancelled = true }
  }, [])

  useEffect(() => { setCurrentPage(1) }, [selectedTerminal, searchQuery])

  // A staff user's own terminal name ('Unassigned' when the session has no
  // device id, e.g. plain-browser logins).
  const myTerminalName = myTerminal || 'Unassigned'
  const myRow = byTerminal.find(t => t.terminal_name === myTerminalName) || {
    terminal_name: myTerminalName, staff_names: [], pos: 0, tuition: 0, total: 0, transactions: 0,
  }

  // Client-side narrowing of the same period's rows by terminal + search.
  // Only attribution-capable kinds (POS + tuition) carry the `terminal` key;
  // null means "Unassigned" (legacy rows and plain-browser sessions) and IS
  // shown — otherwise every pre-attribution record would vanish.
  // Staff are always scoped to their own register.
  const filteredTransactions = useMemo(() => {
    let filtered = transactions.filter(t => t.terminal !== undefined)
    if (!isSuperAdmin) {
      filtered = filtered.filter(t => (t.terminal || 'Unassigned') === myTerminalName)
    } else if (selectedTerminal !== 'All') {
      filtered = filtered.filter(t => (t.terminal || 'Unassigned') === selectedTerminal)
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      filtered = filtered.filter(t =>
        (t.customer || '').toLowerCase().includes(q) ||
        (t.reference || '').toLowerCase().includes(q) ||
        (t.type || '').toLowerCase().includes(q)
      )
    }
    return filtered
  }, [transactions, selectedTerminal, searchQuery, isSuperAdmin, myTerminalName])

  const paginatedTransactions = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE
    return filteredTransactions.slice(start, start + ITEMS_PER_PAGE)
  }, [filteredTransactions, currentPage])

  const totalPages = Math.max(1, Math.ceil(filteredTransactions.length / ITEMS_PER_PAGE))

  const terminalSums = useMemo(() => ({
    pos: byTerminal.reduce((s, t) => s + Number(t.pos || 0), 0),
    tuition: byTerminal.reduce((s, t) => s + Number(t.tuition || 0), 0),
    total: byTerminal.reduce((s, t) => s + Number(t.total || 0), 0),
    txns: byTerminal.reduce((s, t) => s + Number(t.transactions || 0), 0),
    terminals: byTerminal.filter(t => t.terminal_name !== 'Unassigned').length,
  }), [byTerminal])

  const peso = (n) => `₱${Number(n || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const statCards = isSuperAdmin ? [
    { label: 'Total POS', value: peso(terminalSums.pos), icon: TrendingUp, statBg: 'bg-green-50', iconBg: 'bg-green-100', iconColor: 'text-green-600' },
    { label: 'Total Tuition', value: peso(terminalSums.tuition), icon: GraduationCap, statBg: 'bg-blue-50', iconBg: 'bg-blue-100', iconColor: 'text-blue-600' },
    { label: 'Transactions', value: terminalSums.txns.toLocaleString(), icon: Receipt, statBg: 'bg-purple-50', iconBg: 'bg-purple-100', iconColor: 'text-purple-600' },
    { label: 'Terminals', value: terminalSums.terminals.toLocaleString(), icon: Store, statBg: 'bg-amber-50', iconBg: 'bg-amber-100', iconColor: 'text-amber-600' },
  ] : [
    // Staff: scoped to their own register only.
    { label: 'My POS', value: peso(myRow.pos), icon: TrendingUp, statBg: 'bg-green-50', iconBg: 'bg-green-100', iconColor: 'text-green-600' },
    { label: 'My Tuition', value: peso(myRow.tuition), icon: GraduationCap, statBg: 'bg-blue-50', iconBg: 'bg-blue-100', iconColor: 'text-blue-600' },
    { label: 'My Total', value: peso(myRow.total), icon: Store, statBg: 'bg-amber-50', iconBg: 'bg-amber-100', iconColor: 'text-amber-600' },
    { label: 'My Transactions', value: Number(myRow.transactions || 0).toLocaleString(), icon: Receipt, statBg: 'bg-purple-50', iconBg: 'bg-purple-100', iconColor: 'text-purple-600' },
  ]

  const getPrintedBy = () => {
    try {
      const u = JSON.parse(storage.getSync('user') || 'null')
      return [u?.firstName, u?.lastName].filter(Boolean).join(' ') || u?.username || 'Staff'
    } catch { return 'Staff' }
  }

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
    (startDate || endDate) ? `Period: ${startDate || '...'} to ${endDate || '...'}` : 'All records'

  // Summary sheet: every register's revenue for the period. Grand totals on
  // the Revenue page are unaffected; these figures are the terminal sums.
  const handlePrintAll = async () => {
    try {
      await printHtml(
        buildRevenueReportHtml({
          config: reportConfig(),
          logo: printLogo || config?.logo_url || config?.logo,
          dateRangeText: dateRangeText() + (selectedTerminal !== 'All' ? ` · Terminal: ${selectedTerminal}` : ''),
          totals: {
            total_revenue: terminalSums.total,
            total_pos: terminalSums.pos,
            total_tuition: terminalSums.tuition,
            total_transactions: terminalSums.txns,
          },
          byTerminal,
          // The by-terminal table stays on screen; the printed report is for
          // the staff user's totals — each terminal prints its own sheet via
          // its row button.
          includeTerminals: false,
          // Full line-items for the filtered period, so the header report
          // includes everything the per-terminal sheets do.
          rows: filteredTransactions,
          preparedBy: getPrintedBy(),
          generatedAt: new Date().toLocaleString('en-PH'),
        }),
        { pageSize: 'A4', title: 'Staff Revenue Report' }
      )
    } catch (e) {
      showToast(e.message || 'Print failed', 'error')
    }
  }

  // One A4 sheet per register: its totals plus every transaction line-item
  // attributed to it in the period.
  const handlePrintTerminal = async (t) => {
    try {
      const rows = transactions.filter(x => (x.terminal || 'Unassigned') === t.terminal_name)
      await printHtml(
        buildTerminalReportHtml({
          config: reportConfig(),
          logo: printLogo || config?.logo_url || config?.logo,
          terminal: t,
          dateRangeText: dateRangeText(),
          rows,
          preparedBy: getPrintedBy(),
          generatedAt: new Date().toLocaleString('en-PH'),
        }),
        { pageSize: 'A4', title: `Staff Revenue — ${t.terminal_name}` }
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
    <div className="min-h-0">
      <div className="no-print">
        <PageHeader
          title="Staff Revenue"
          subtitle="Revenue per register (terminal) and its staff"
          breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Finance' }, { label: 'Staff Revenue' }]}
          actions={
            isSuperAdmin ? (
              <div className="flex flex-wrap gap-2">
                <ActionButton icon={Printer} size="sm" onClick={handlePrintAll}>Print Report</ActionButton>
              </div>
            ) : undefined
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
            <Receipt size={14} className="text-blue-600" /> Filters
          </h3>
          <button onClick={() => { setStartDate(''); setEndDate(''); setSelectedTerminal('All'); setSearchQuery('') }}
            className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1">
            <RotateCcw size={12} /> Reset
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
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
          {isSuperAdmin && (
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Terminal</label>
              <select value={selectedTerminal} onChange={(e) => setSelectedTerminal(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900">
                <option value="All">All Terminals</option>
                {byTerminal.map(t => (
                  <option key={t.terminal_id || 'unassigned'} value={t.terminal_name}>{t.terminal_name}</option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Search</label>
            <input type="text" placeholder="Search payer, reference..."
              value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900" />
          </div>
        </div>
      </div>

      {isSuperAdmin ? (
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden mb-5">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-gray-800 text-sm flex items-center gap-2">
            <Store size={14} className="text-blue-600" /> Revenue by Terminal
          </h3>
          <span className="text-xs text-gray-400">POS + Tuition · {dateRangeText()}</span>
        </div>
        {byTerminal.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14">
            <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mb-4">
              <Store size={24} className="text-gray-400" />
            </div>
            <p className="text-gray-600 font-medium">No terminal revenue yet</p>
            <p className="text-gray-400 text-sm mt-1">
              Devices register automatically after their first logged-in transaction from the Electron app.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto overflow-y-visible">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">Terminal</th>
                  <th className="px-4 py-3 text-left">Staff</th>
                  <th className="px-4 py-3 text-right">POS</th>
                  <th className="px-4 py-3 text-right">Tuition</th>
                  <th className="px-4 py-3 text-right">Total</th>
                  <th className="px-4 py-3 text-right">Txns</th>
                  <th className="px-4 py-3 text-right no-print">Print</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {byTerminal.map(t => (
                  <tr key={t.terminal_id || 'unassigned'} className={t.terminal_name === 'Unassigned' ? 'bg-gray-50/60' : 'hover:bg-gray-50'}>
                    <td className="px-4 py-3">
                      <span className="font-medium text-gray-800">{t.terminal_name}</span>
                      {t.terminal_name === 'Unassigned' && (
                        <span className="ml-2 text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full align-middle">browser / legacy</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{(t.staff_names || []).join(', ') || '—'}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-700">{peso(t.pos)}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-700">{peso(t.tuition)}</td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-800">{peso(t.total)}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{t.transactions}</td>
                    <td className="px-4 py-3 text-right no-print">
                      <button onClick={() => handlePrintTerminal(t)}
                        className="p-1.5 rounded-lg text-gray-400 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                        title={`Print ${t.terminal_name} revenue report`}>
                        <Printer size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      ) : (
      // Staff view: only their own register, with their printable total report.
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden mb-5">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-gray-800 text-sm flex items-center gap-2">
            <Store size={14} className="text-blue-600" /> My Terminal
          </h3>
          <span className="text-xs text-gray-400">POS + Tuition · {dateRangeText()}</span>
        </div>
        <div className="p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="font-semibold text-gray-900">{myTerminalName}</p>
            <p className="text-xs text-gray-500 mt-1">
              POS {peso(myRow.pos)} · Tuition {peso(myRow.tuition)} · {myRow.transactions} transaction{myRow.transactions === 1 ? '' : 's'}
            </p>
            <p className="text-lg font-bold text-gray-800 mt-2">{peso(myRow.total)}</p>
          </div>
          <ActionButton icon={Printer} size="sm" onClick={() => handlePrintTerminal(myRow)}>
            Print My Report
          </ActionButton>
        </div>
      </div>
      )}

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
              {searchQuery || selectedTerminal !== 'All' ? 'Try adjusting your filters' : 'No terminal-attributed payments in this period'}
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
                    <th className="px-4 py-3 text-left hidden md:table-cell">Terminal</th>
                    <th className="px-4 py-3 text-right">Amount</th>
                    <th className="px-4 py-3 text-left hidden xl:table-cell">Method</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {paginatedTransactions.map((txn) => (
                    <tr key={txn.entry_id || `${txn.kind}-${txn.id}` || `${txn.reference}-${txn.date}`}
                      className={selectedTerminal !== 'All' ? 'bg-blue-50/40' : 'hover:bg-gray-50'}>
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {new Date(txn.date || txn.created_at || txn.payment_date).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded-lg text-gray-600">
                          {txn.reference || `#${txn.id}` || '-'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center text-white text-xs font-semibold shrink-0">
                            {(txn.customer || '?')[0]?.toUpperCase()}
                          </div>
                          <span className="font-medium text-gray-800 text-sm truncate max-w-[140px]">{txn.customer || 'N/A'}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell text-gray-600 whitespace-nowrap">{txn.type || 'N/A'}</td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <span className="text-gray-600 text-xs truncate max-w-[160px] block">
                          {txn.products && txn.products[0]
                            ? `${txn.products[0].name}${txn.products[0].quantity > 1 ? ` x${txn.products[0].quantity}` : ''}`
                            : '-'}
                        </span>
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <span className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded-lg">{txn.terminal || 'Unassigned'}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-800 whitespace-nowrap">
                        {peso(txn.amount)}
                      </td>
                      <td className="px-4 py-3 hidden xl:table-cell">
                        <div className="flex items-center gap-1.5 text-gray-500">
                          {txn.method?.toLowerCase().includes('gcash') ? <CreditCard size={13} /> : txn.method?.toLowerCase().includes('bank') || txn.method?.toLowerCase().includes('card') ? <Banknote size={13} /> : <Wallet size={13} />}
                          <span className="capitalize text-xs">{txn.method || 'Cash'}</span>
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

      {toast && (
        <div className={`fixed bottom-6 left-6 z-50 px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white transition-all animate-slide-up flex items-center gap-2 ${toast.type === 'error' ? 'bg-red-600' : 'bg-gray-800'}`}>
          {toast.type === 'error' ? <AlertCircle size={16} /> : <Check size={16} />}
          {toast.message}
        </div>
      )}

      <style>{`
        @keyframes slide-up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .animate-slide-up { animation: slide-up 0.3s ease-out; }
      `}</style>
    </div>
  )
}
