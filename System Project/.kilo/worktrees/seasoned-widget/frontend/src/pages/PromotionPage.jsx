import { useState, useEffect } from 'react'
import PageHeader from '../components/PageHeader'
import ActionButton from '../components/ActionButton'
import { studentsAPI, academicAPI } from '../services/api'
import { GraduationCap, ArrowRight, ChevronRight, ChevronDown, Layers, Users, Loader2, Check, AlertTriangle, BookOpen, X } from 'lucide-react'

export default function PromotionPage() {
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [promoting, setPromoting] = useState(false)
  const [result, setResult] = useState(null)
  const [toast, setToast] = useState(null)
  const [sections, setSections] = useState([])
  const [openGroup, setOpenGroup] = useState(null)
  const [openSection, setOpenSection] = useState(null)
  const [editStudent, setEditStudent] = useState(null)
  const [editSection, setEditSection] = useState('')
  const [editGroupKey, setEditGroupKey] = useState('')
  const [savingSection, setSavingSection] = useState(false)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  const fetchPreview = async () => {
    setLoading(true)
    try {
      const [data, sectionsData] = await Promise.all([
        studentsAPI.promotionPreview('all'),
        academicAPI.getSections().catch(() => []),
      ])
      setPreview(data)
      setSections(Array.isArray(sectionsData) ? sectionsData : sectionsData.results || [])
    } catch (err) {
      showToast('Failed to load promotion preview', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchPreview() }, [])

  // Target grade per promotion group -> sections valid for the TARGET grade
  const groupGradeMap = {
    shs_grade_11: { label: 'Grade 12', prefix: 'SHS' },
    shs_grade_12: { label: 'Graduate', prefix: 'SHS' },
    bundled_year_1: { label: '2nd Year', prefix: 'BUN' },
    bundled_year_2: { label: 'Graduate', prefix: 'BUN' },
  }

  const sectionsForStudent = () => {
    const g = groupGradeMap[editGroupKey]
    if (!g) return sections
    return sections
      .filter(s => {
        const lt = String(s.level_type || '').toUpperCase()
        if (lt) {
          const ok = g.prefix === 'SHS' ? ['SHS', 'ALL'].includes(lt) : ['BUN', 'COL', 'ALL'].includes(lt)
          if (!ok) return false
        }
        const gy = String(s.grade_year || '').toLowerCase()
        if (gy && g.label !== 'Graduate') {
          return gy.includes(g.label.toLowerCase())
        }
        return true
      })
      .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
  }

  const openSectionEdit = (student, groupKey) => {
    setEditStudent(student)
    setEditGroupKey(groupKey)
    setEditSection(student.section || '')
  }

  const handleSaveSection = async () => {
    if (!editStudent || savingSection) return
    setSavingSection(true)
    try {
      await studentsAPI.patch(editStudent.id, { section: editSection })
      showToast(`${editStudent.first_name} ${editStudent.last_name} → ${editSection || 'No section'}`)
      setEditStudent(null)
      fetchPreview()
    } catch (err) {
      showToast(err?.response?.data?.error || 'Failed to update section', 'error')
    } finally {
      setSavingSection(false)
    }
  }

  const handlePromote = async (type, section = '') => {
    if (promoting) return
    const label = type === 'shs' ? 'SHS' : type === 'bundled' ? 'Bundled' : 'all eligible'
    const scope = section ? ` in section "${section}"` : ''
    const group = (groups[type] || []).filter((s) => !section || (s.section || 'Unassigned') === section)
    const names = group.map((s) => `${s.first_name} ${s.last_name}`).join(', ')
    const detail = names.length > 140 ? `${names.slice(0, 140)}…` : names
    const question = section
      ? `Promote these ${group.length} student(s)${scope}?\n\n${detail || 'No matching students'}`
      : `Promote all ${label} students${scope}?`
    if (!window.confirm(question)) return
    setPromoting(true)
    setResult(null)
    try {
      const data = await studentsAPI.promoteStudents(type, section)
      const skipped = data?.skipped_dropouts || 0
      const normalized = {
        ...(data || {}),
        success: data?.success !== false,
        message: (data?.message || 'Promotion completed')
          + (skipped ? ` · ${skipped} skipped (dropout)` : ''),
      }
      setResult(normalized)
      showToast(normalized.message)
      fetchPreview()
    } catch (err) {
      setResult({ success: false, message: err.response?.data?.error || 'Promotion failed', promoted_count: 0, graduated_count: 0 })
      showToast(err.response?.data?.error || 'Promotion failed', 'error')
    } finally {
      setPromoting(false)
    }
  }

  const typeForGroup = (groupKey) =>
    groupKey === 'shs_grade_11' || groupKey === 'shs_grade_12' ? 'shs' : 'bundled'

  const counts = preview?.counts || {}
  const groups = preview?.preview || {}
  const bySection = preview?.by_section || {}
  const excludedDropouts = preview?.excluded_dropouts || {}
  const total = counts.shs_grade_11_to_12 + counts.shs_grade_12_to_graduate + counts.bundled_year_1_to_2 + counts.bundled_year_2_to_graduate
  // Students already run through promotion. Without these the page looks
  // broken when everyone eligible has already been promoted.
  const promoted = preview?.already_promoted || {}
  const promotedList = [...(promoted.shs_grade_12 || []), ...(promoted.bundled_year_2 || [])]
  const promotedTotal = promotedList.length

  const statCards = [
    { key: 'shs_grade_11', label: 'Grade 11 → Grade 12', value: counts.shs_grade_11_to_12 || 0, icon: Users, statBg: 'bg-blue-50', iconBg: 'bg-blue-100', iconColor: 'text-blue-600', hoverBg: 'hover:bg-blue-100', ring: 'hover:ring-blue-300' },
    { key: 'shs_grade_12', label: 'Grade 12 → Graduate', value: counts.shs_grade_12_to_graduate || 0, icon: GraduationCap, statBg: 'bg-green-50', iconBg: 'bg-green-100', iconColor: 'text-green-600', hoverBg: 'hover:bg-green-100', ring: 'hover:ring-green-300' },
    { key: 'bundled_year_1', label: '1st Year → 2nd Year', value: counts.bundled_year_1_to_2 || 0, icon: Users, statBg: 'bg-purple-50', iconBg: 'bg-purple-100', iconColor: 'text-purple-600', hoverBg: 'hover:bg-purple-100', ring: 'hover:ring-purple-300' },
    { key: 'bundled_year_2', label: '2nd Year → Graduate', value: counts.bundled_year_2_to_graduate || 0, icon: GraduationCap, statBg: 'bg-amber-50', iconBg: 'bg-amber-100', iconColor: 'text-amber-600', hoverBg: 'hover:bg-amber-100', ring: 'hover:ring-amber-300' },
  ]

  // Sections belonging to the cohort the user clicked into.
  const activeSections = openGroup ? (bySection?.[openGroup] || []) : []
  const activeDropouts = openGroup ? (excludedDropouts?.[openGroup] || []) : []

  const openCohortMeta = statCards.find((c) => c.key === openGroup)

  return (
    <div>
      <PageHeader
        title="Promotion Management"
        subtitle="Advance students to the next year level with auto tuition update"
        actions={
          <div className="flex gap-2">
            <ActionButton variant="secondary" onClick={fetchPreview} loading={loading} icon={Loader2} size="sm">Refresh</ActionButton>
          </div>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {statCards.map((card, i) => {
          const isOpen = openGroup === card.key
          const sectionCount = (bySection?.[card.key] || []).length
          return (
            <button
              key={i}
              type="button"
              onClick={() => {
                setOpenGroup(isOpen ? null : card.key)
                setOpenSection(null)
              }}
              title="Click to list sections"
              className={`${card.statBg} ${card.hoverBg} rounded-2xl p-4 border text-left cursor-pointer transition-all ring-2 ${card.ring} ${
                isOpen ? 'ring-offset-2 ring-blue-400' : 'ring-transparent'
              } ${card.value === 0 ? 'opacity-60' : ''}`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 ${card.iconBg} rounded-xl flex items-center justify-center shrink-0`}>
                  <card.icon size={20} className={card.iconColor} />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-gray-500">{card.label}</p>
                  <p className="text-xl font-bold text-gray-800">{card.value}</p>
                  {sectionCount > 0 && (
                    <p className="text-[10px] text-gray-400 mt-0.5">{sectionCount} section{sectionCount !== 1 ? 's' : ''}</p>
                  )}
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {openGroup && (
        <div className="bg-white rounded-2xl border border-gray-100 mb-6 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between gap-3">
            <h3 className="font-semibold text-gray-800 flex items-center gap-2">
              <Layers size={16} className="text-blue-600" />
              {openCohortMeta?.label} — sections
            </h3>
            <div className="flex items-center gap-2">
              {(bySection?.[openGroup] || []).length > 0 && (
                <ActionButton
                  variant="secondary"
                  size="sm"
                  loading={promoting}
                  onClick={() => handlePromote(typeForGroup(openGroup))}
                >
                  Promote all sections
                </ActionButton>
              )}
              <button onClick={() => { setOpenGroup(null); setOpenSection(null) }}
                className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                title="Close">
                <X size={16} />
              </button>
            </div>
          </div>

          {activeSections.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">
              No eligible students in this cohort
              {activeDropouts.length > 0 && (
                <span className="block text-xs text-amber-600 mt-1">
                  {activeDropouts.length} excluded as {activeDropouts.length === 1 ? 'a dropout' : 'dropouts'}
                </span>
              )}
            </p>
          ) : (
            <div className="divide-y divide-gray-50">
              {activeSections.map((grp) => {
                const isSectionOpen = openSection === grp.section
                return (
                  <div key={grp.section}>
                    <div className={`px-5 py-3 flex items-center justify-between gap-3 ${isSectionOpen ? 'bg-blue-50/60' : 'hover:bg-gray-50'}`}>
                      <button
                        type="button"
                        onClick={() => setOpenSection(isSectionOpen ? null : grp.section)}
                        className="flex items-center gap-2 min-w-0 text-left cursor-pointer"
                        title="Click to list students"
                      >
                        {isSectionOpen
                          ? <ChevronDown size={14} className="text-blue-500 shrink-0" />
                          : <ChevronRight size={14} className="text-gray-400 shrink-0" />}
                        <span className="text-sm font-medium text-gray-800">{grp.section}</span>
                        <span className="text-xs text-gray-400">{grp.count} student{grp.count !== 1 ? 's' : ''}</span>
                      </button>
                      <ActionButton
                        size="sm"
                        loading={promoting}
                        onClick={() => handlePromote(typeForGroup(openGroup), grp.section)}
                      >
                        Promote section
                      </ActionButton>
                    </div>
                    {isSectionOpen && (
                      <div className="bg-gray-50/60 border-t border-gray-100">
                        {grp.students.map((s) => (
                          <button
                            key={s.id}
                            type="button"
                            onClick={() => openSectionEdit(s, openGroup)}
                            className="w-full px-8 py-2.5 flex items-center justify-between hover:bg-blue-50 transition-colors text-left cursor-pointer"
                            title="Click to manage section"
                          >
                            <div className="min-w-0">
                              <p className="text-sm text-gray-700">{s.first_name} {s.last_name}</p>
                              <p className="text-xs text-gray-400">{s.lrn}</p>
                            </div>
                            <ChevronRight size={13} className="text-gray-400 shrink-0" />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {activeDropouts.length > 0 && (
            <div className="px-5 py-3 border-t border-gray-100 bg-amber-50/60">
              <p className="text-xs text-amber-700 flex items-center gap-2">
                <AlertTriangle size={13} />
                Excluded from promotion ({activeDropouts.length} dropout{activeDropouts.length !== 1 ? 's' : ''}):
                {activeDropouts.map((s) => `${s.first_name} ${s.last_name}`).join(', ')}
              </p>
            </div>
          )}
        </div>
      )}

      {result && (
        <div className={`rounded-2xl p-4 mb-6 flex items-start gap-3 ${result.success ? 'bg-green-50' : 'bg-red-50'}`}>
          {result.success ? <Check size={20} className="text-green-600 mt-0.5" /> : <AlertTriangle size={20} className="text-red-600 mt-0.5" />}
          <div>
            <p className={`text-sm font-medium ${result.success ? 'text-green-800' : 'text-red-800'}`}>{result.message}</p>
            <p className="text-xs text-gray-500 mt-1">Promoted: {result.promoted_count || 0} · Graduated: {result.graduated_count || 0}</p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="animate-spin text-gray-400" />
        </div>
      ) : total === 0 ? (
        <div className="text-center py-12">
          <GraduationCap size={40} className="mx-auto text-gray-300 mb-3" />
          {promotedTotal > 0 ? (
            <>
              <p className="text-gray-500 font-medium">All eligible students have been promoted</p>
              <p className="text-xs text-gray-400 mt-1">
                {promotedTotal} student{promotedTotal === 1 ? '' : 's'} already graduated - nothing left to promote
              </p>
            </>
          ) : (
            <>
              <p className="text-gray-500 font-medium">No students eligible for promotion</p>
              <p className="text-xs text-gray-400 mt-1">All students are at their current year level</p>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-6 mb-6">
          <div className="flex gap-3">
            <ActionButton onClick={() => handlePromote('shs')} loading={promoting} icon={ArrowRight} size="sm">
              Promote All SHS ({counts.shs_grade_11_to_12 + counts.shs_grade_12_to_graduate})
            </ActionButton>
            <ActionButton onClick={() => handlePromote('bundled')} loading={promoting} icon={ArrowRight} size="sm">
              Promote All Bundled ({counts.bundled_year_1_to_2 + counts.bundled_year_2_to_graduate})
            </ActionButton>
            <ActionButton onClick={() => handlePromote('all')} loading={promoting} icon={ArrowRight}>
              Promote All ({total})
            </ActionButton>
          </div>
        </div>
      )}

      {editStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setEditStudent(null)} />
          <div className="relative bg-white rounded-2xl shadow-2xl z-10 w-full max-w-md">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Manage Section</h2>
              <button onClick={() => setEditStudent(null)} className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
                <X size={18} className="text-gray-400" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-gray-600">
                <span className="font-semibold text-gray-800">{editStudent.first_name} {editStudent.last_name}</span>
                <span className="text-gray-400"> · LRN: {editStudent.lrn || 'N/A'}</span>
              </p>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Section</label>
                <select value={editSection} onChange={(e) => setEditSection(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900">
                  <option value="">No section</option>
                  {sectionsForStudent().map(s => (
                    <option key={s.id} value={s.name}>{s.display_name || s.name}{s.grade_year ? ` (${s.grade_year})` : ''}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-3">
              <button onClick={() => setEditStudent(null)}
                className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors">Cancel</button>
              <button onClick={handleSaveSection} disabled={savingSection}
                className="px-4 py-2.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2">
                {savingSection ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />} Save
              </button>
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

      <style>{`
        @keyframes slide-up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .animate-slide-up { animation: slide-up 0.3s ease-out; }
      `}</style>
    </div>
  )
}
