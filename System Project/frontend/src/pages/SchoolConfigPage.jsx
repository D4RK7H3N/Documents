import { useState, useEffect, useRef } from 'react'
import { Navigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import ActionButton from '../components/ActionButton'
import { Building, Save, Loader2, Upload, Image, X, CheckCircle, AlertCircle, Shield } from 'lucide-react'
import { configAPI, academicAPI, adviserAPI } from '../services/api'
import { useSchoolConfig } from '../contexts/SchoolConfigContext'
import { useAuth } from '../context/AuthContext'

export default function SchoolConfigPage() {
  const { user } = useAuth()
  const { config, loading: configLoading, updateConfig } = useSchoolConfig()

  if (!user?.is_superuser && !user?.isAdmin) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="bg-white p-8 rounded-2xl border border-gray-100 max-w-md text-center">
          <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Shield size={28} className="text-red-500" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Admin Access Required</h2>
          <p className="text-sm text-gray-500">Only administrators can view and edit school configuration. Please contact your system administrator if you need access.</p>
        </div>
      </div>
    )
  }
  const [localForm, setLocalForm] = useState({})
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [logoFile, setLogoFile] = useState(null)
  const [logoPreview, setLogoPreview] = useState('')
  const [toast, setToast] = useState(null)
  const [sectionsList, setSectionsList] = useState([])
  // The running build's version (shown as "System Version"), read from the
  // Electron shell so it matches the installed app - not a hardcoded string.
  const [systemVersion, setSystemVersion] = useState('1.1.1')

  // Advisers manager (option C): advisers live here, sections point at one.
  const [advisers, setAdvisers] = useState([])
  const [newAdviser, setNewAdviser] = useState('')
  const [adviserBusy, setAdviserBusy] = useState(false)
  const fileInputRef = useRef(null)

  // Populate the per-signatory section dropdown.
  useEffect(() => {
    if (window.electronAPI?.getAppVersion) {
      window.electronAPI.getAppVersion()
        .then(v => { if (v) setSystemVersion(v) })
        .catch(() => {})
    }
  }, [])

  useEffect(() => {
    academicAPI.getSections()
      .then((data) => setSectionsList(Array.isArray(data) ? data : (data?.results || [])))
      .catch(() => setSectionsList([]))
  }, [])

  const loadAdvisers = () => {
    adviserAPI.listAll().then((d) => setAdvisers(Array.isArray(d) ? d : d?.results || [])).catch(() => setAdvisers([]))
  }
  useEffect(() => { loadAdvisers() }, [])

  const addAdviser = async () => {
    const name = newAdviser.trim()
    if (!name) return
    setAdviserBusy(true)
    try {
      await adviserAPI.create({ full_name: name })
      setNewAdviser('')
      loadAdvisers()
      showToast('Adviser added')
    } catch (err) {
      showToast(err?.response?.data?.full_name?.[0] || 'Failed to add adviser', 'error')
    } finally {
      setAdviserBusy(false)
    }
  }

  const removeAdviser = async (id) => {
    setAdviserBusy(true)
    try {
      await adviserAPI.remove(id)
      loadAdvisers()
      academicAPI.getSections().then((d) => setSectionsList(Array.isArray(d) ? d : (d?.results || []))).catch(() => {})
      showToast('Adviser removed')
    } catch {
      showToast('Failed to remove adviser', 'error')
    } finally {
      setAdviserBusy(false)
    }
  }

  // Assign one adviser to a section: this section points at the adviser, and
  // any other section that previously pointed at them is released.
  const assignAdviserToSection = async (adviserId, sectionId) => {
    setAdviserBusy(true)
    try {
      const previous = sectionsList.find(s => Number(s.adviser) === Number(adviserId) && s.id !== Number(sectionId))
      if (sectionId) {
        await academicAPI.patchSection(sectionId, { adviser: adviserId })
      }
      if (previous) {
        await academicAPI.patchSection(previous.id, { adviser: null })
      }
      academicAPI.getSections()
        .then((d) => setSectionsList(Array.isArray(d) ? d : (d?.results || [])))
        .catch(() => {})
      showToast(sectionId ? 'Adviser assigned' : 'Adviser unassigned')
    } catch {
      showToast('Failed to assign adviser', 'error')
    } finally {
      setAdviserBusy(false)
    }
  }

  useEffect(() => {
    if (config) {
      setLocalForm({
        school_name: config.school_name || '',
        school_short_name: config.school_short_name || '',
        tagline: config.tagline || '',
        address_line1: config.address_line1 || '',
        address_line2: config.address_line2 || '',
        city: config.city || '',
        province: config.province || '',
        zip_code: config.zip_code || '',
        country: config.country || '',
        phone_number: config.phone_number || '',
        mobile_number: config.mobile_number || '',
        email: config.email || '',
        website: config.website || '',
        current_academic_year: config.current_academic_year || '',
        student_id_prefix: config.student_id_prefix || '',
        receipt_header_text: config.receipt_header_text || '',
        receipt_footer_text: config.receipt_footer_text || '',
        report_checked_by: config.report_checked_by || '',
        list_print_signatories: (Array.isArray(config.list_print_signatories) ? config.list_print_signatories : [])
          .map((s) => ({ label: s?.label || '', name: s?.name || '', section: s?.section || '' })),
        list_print_signature_label: config.list_print_signature_label ?? 'Name and Signature',
        list_print_show_signatures: config.list_print_show_signatures !== false,
        list_print_show_generated_at: config.list_print_show_generated_at !== false,
        facebook_url: config.facebook_url || '',
        twitter_url: config.twitter_url || '',
        instagram_url: config.instagram_url || '',
      })
      setLogoPreview(config.logo_url || config.logo || '')
    }
  }, [config])

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }

  const handleLogoSelect = (e) => {
    const file = e.target.files[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      showToast('Please select a valid image file.', 'error')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      showToast('Image size must be less than 5MB.', 'error')
      return
    }
    setLogoFile(file)
    const reader = new FileReader()
    reader.onloadend = () => {
      setLogoPreview(reader.result)
    }
    reader.readAsDataURL(file)
  }

  const removeLogo = () => {
    setLogoFile(null)
    setLogoPreview(config?.logo_url || config?.logo || '')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleSave = async () => {
    if (saving) return
    setSaving(true)
    try {
      setEditing(false)

      let data
      if (logoFile) {
        data = new FormData()
        Object.keys(localForm).forEach((key) => {
          data.append(key, localForm[key])
        })
        data.append('logo', logoFile)
      } else {
        data = localForm
      }

      const updated = await configAPI.updateConfig(data)
      await updateConfig(updated)
      setLogoFile(null)
      showToast('School configuration updated successfully.')
    } catch (error) {
      setEditing(true)
      showToast(
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        'Unable to save configuration.',
        'error'
      )
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setEditing(false)
    setLogoFile(null)
    if (config) {
      setLocalForm({
        school_name: config.school_name || '',
        school_short_name: config.school_short_name || '',
        tagline: config.tagline || '',
        address_line1: config.address_line1 || '',
        address_line2: config.address_line2 || '',
        city: config.city || '',
        province: config.province || '',
        zip_code: config.zip_code || '',
        country: config.country || '',
        phone_number: config.phone_number || '',
        mobile_number: config.mobile_number || '',
        email: config.email || '',
        website: config.website || '',
        current_academic_year: config.current_academic_year || '',
        student_id_prefix: config.student_id_prefix || '',
        receipt_header_text: config.receipt_header_text || '',
        receipt_footer_text: config.receipt_footer_text || '',
        report_checked_by: config.report_checked_by || '',
        list_print_signatories: (Array.isArray(config.list_print_signatories) ? config.list_print_signatories : [])
          .map((s) => ({ label: s?.label || '', name: s?.name || '', section: s?.section || '' })),
        list_print_signature_label: config.list_print_signature_label ?? 'Name and Signature',
        list_print_show_signatures: config.list_print_show_signatures !== false,
        list_print_show_generated_at: config.list_print_show_generated_at !== false,
        facebook_url: config.facebook_url || '',
        twitter_url: config.twitter_url || '',
        instagram_url: config.instagram_url || '',
      })
      setLogoPreview(config.logo_url || config.logo || '')
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  if (configLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-blue-600" size={40} />
      </div>
    )
  }

  const inputClass = 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-gray-50 text-gray-900 focus:ring-2 focus:ring-blue-500 outline-none transition-colors'

  const labelClass = 'text-sm font-medium text-gray-600'

  const rowClass = 'flex flex-col gap-2 py-3 border-b border-gray-100'

  return (
    <div>
      <PageHeader
        title="School Configuration"
        subtitle="Manage school-wide settings"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'System' }, { label: 'School Config' }]}
        actions={
          editing ? (
            <div className="flex items-center gap-2">
              <ActionButton variant="secondary" onClick={handleCancel} disabled={saving}>
                Cancel
              </ActionButton>
              <ActionButton icon={Save} onClick={handleSave} loading={saving}>
                Save
              </ActionButton>
            </div>
          ) : (
            <ActionButton icon={Building} onClick={() => setEditing(true)}>
              Edit Configuration
            </ActionButton>
          )
        }
      />

      {toast && (
        <div className={`fixed bottom-6 left-6 z-50 px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white transition-all animate-slide-up flex items-center gap-2 ${toast.type === 'error' ? 'bg-red-600' : 'bg-green-600'}`}>
          {toast.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle size={16} />}
          {toast.message}
        </div>
      )}

      <div className="bg-white rounded-2xl border border-gray-100 p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          <div className="lg:col-span-2 space-y-6">

            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">School Identity</h3>
              <div className="space-y-4">

                <div className={rowClass}>
                  <label className={labelClass}>School Name *</label>
                  {editing ? (
                    <input
                      type="text"
                      value={localForm.school_name || ''}
                      onChange={(e) => setLocalForm({ ...localForm, school_name: e.target.value })}
                      className={inputClass}
                      placeholder="Enter school name"
                    />
                  ) : (
                    <span className="font-semibold text-gray-800 text-base">
                      {config?.school_name || 'Management System'}
                    </span>
                  )}
                </div>

                <div className={rowClass}>
                  <label className={labelClass}>Short Name</label>
                  {editing ? (
                    <input
                      type="text"
                      value={localForm.school_short_name || ''}
                      onChange={(e) => setLocalForm({ ...localForm, school_short_name: e.target.value })}
                      className={inputClass}
                    />
                  ) : (
                    <span className="font-medium text-gray-800">{config?.school_short_name || 'SCC'}</span>
                  )}
                </div>

                <div className={rowClass}>
                  <label className={labelClass}>Tagline</label>
                  {editing ? (
                    <input
                      type="text"
                      value={localForm.tagline || ''}
                      onChange={(e) => setLocalForm({ ...localForm, tagline: e.target.value })}
                      className={inputClass}
                    />
                  ) : (
                    <span className="font-medium text-gray-800">{config?.tagline || 'Education Excellence'}</span>
                  )}
                </div>

                <div className={rowClass}>
                  <label className={labelClass}>Academic Year</label>
                  {editing ? (
                    <input
                      type="text"
                      value={localForm.current_academic_year || ''}
                      onChange={(e) => setLocalForm({ ...localForm, current_academic_year: e.target.value })}
                      className={inputClass}
                      placeholder="e.g. 2026-2027"
                    />
                  ) : (
                    <span className="font-medium text-gray-800">{config?.current_academic_year || '—'}</span>
                  )}
                </div>

                <div className={rowClass}>
                  <label className={labelClass}>Student ID Prefix</label>
                  {editing ? (
                    <input
                      type="text"
                      value={localForm.student_id_prefix || ''}
                      onChange={(e) => setLocalForm({ ...localForm, student_id_prefix: e.target.value })}
                      className={inputClass}
                    />
                  ) : (
                    <span className="font-medium text-gray-800">{config?.student_id_prefix || 'STU'}</span>
                  )}
                </div>

              </div>
            </section>

            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Contact Information</h3>
              <div className="space-y-4">

                <div className={rowClass}>
                  <label className={labelClass}>Address</label>
                  {editing ? (
                    <input
                      type="text"
                      value={localForm.address_line1 || ''}
                      onChange={(e) => setLocalForm({ ...localForm, address_line1: e.target.value })}
                      className={inputClass}
                    />
                  ) : (
                    <span className="font-medium text-gray-800">{config?.address_line1 || 'Manila, Philippines'}</span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className={rowClass}>
                    <label className={labelClass}>City</label>
                    {editing ? (
                      <input
                        type="text"
                        value={localForm.city || ''}
                        onChange={(e) => setLocalForm({ ...localForm, city: e.target.value })}
                        className={inputClass}
                      />
                    ) : (
                      <span className="font-medium text-gray-800">{config?.city || 'Manila'}</span>
                    )}
                  </div>
                  <div className={rowClass}>
                    <label className={labelClass}>Province</label>
                    {editing ? (
                      <input
                        type="text"
                        value={localForm.province || ''}
                        onChange={(e) => setLocalForm({ ...localForm, province: e.target.value })}
                        className={inputClass}
                      />
                    ) : (
                      <span className="font-medium text-gray-800">{config?.province || 'Negros Occidental'}</span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className={rowClass}>
                    <label className={labelClass}>Phone</label>
                    {editing ? (
                      <input
                        type="text"
                        value={localForm.phone_number || ''}
                        onChange={(e) => setLocalForm({ ...localForm, phone_number: e.target.value })}
                        className={inputClass}
                      />
                    ) : (
                      <span className="font-medium text-gray-800">{config?.phone_number || '(034) 123-4567'}</span>
                    )}
                  </div>
                  <div className={rowClass}>
                    <label className={labelClass}>Mobile</label>
                    {editing ? (
                      <input
                        type="text"
                        value={localForm.mobile_number || ''}
                        onChange={(e) => setLocalForm({ ...localForm, mobile_number: e.target.value })}
                        className={inputClass}
                      />
                    ) : (
                      <span className="font-medium text-gray-800">{config?.mobile_number || 'N/A'}</span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className={rowClass}>
                    <label className={labelClass}>Email</label>
                    {editing ? (
                      <input
                        type="email"
                        value={localForm.email || ''}
                        onChange={(e) => setLocalForm({ ...localForm, email: e.target.value })}
                        className={inputClass}
                      />
                    ) : (
                      <span className="font-medium text-gray-800">{config?.email || 'info@schoolms.local'}</span>
                    )}
                  </div>
                  <div className={rowClass}>
                    <label className={labelClass}>Website</label>
                    {editing ? (
                      <input
                        type="url"
                        value={localForm.website || ''}
                        onChange={(e) => setLocalForm({ ...localForm, website: e.target.value })}
                        className={inputClass}
                      />
                    ) : (
                      <span className="font-medium text-gray-800">{config?.website || 'N/A'}</span>
                    )}
                  </div>
                </div>

              </div>
            </section>

            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Social Media</h3>
              <div className="space-y-4">
                <div className={rowClass}>
                  <label className={labelClass}>Facebook</label>
                  {editing ? (
                    <input
                      type="url"
                      value={localForm.facebook_url || ''}
                      onChange={(e) => setLocalForm({ ...localForm, facebook_url: e.target.value })}
                      className={inputClass}
                      placeholder="https://facebook.com/..."
                    />
                  ) : (
                    <span className="font-medium text-gray-800">{config?.facebook_url || 'N/A'}</span>
                  )}
                </div>
                <div className={rowClass}>
                  <label className={labelClass}>Twitter / X</label>
                  {editing ? (
                    <input
                      type="url"
                      value={localForm.twitter_url || ''}
                      onChange={(e) => setLocalForm({ ...localForm, twitter_url: e.target.value })}
                      className={inputClass}
                      placeholder="https://twitter.com/..."
                    />
                  ) : (
                    <span className="font-medium text-gray-800">{config?.twitter_url || 'N/A'}</span>
                  )}
                </div>
                <div className={rowClass}>
                  <label className={labelClass}>Instagram</label>
                  {editing ? (
                    <input
                      type="url"
                      value={localForm.instagram_url || ''}
                      onChange={(e) => setLocalForm({ ...localForm, instagram_url: e.target.value })}
                      className={inputClass}
                      placeholder="https://instagram.com/..."
                    />
                  ) : (
                    <span className="font-medium text-gray-800">{config?.instagram_url || 'N/A'}</span>
                  )}
                </div>
              </div>
            </section>

            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Receipt Configuration</h3>
              <div className="space-y-4">
                <div className={rowClass}>
                  <label className={labelClass}>Receipt Header Text</label>
                  {editing ? (
                    <input
                      type="text"
                      value={localForm.receipt_header_text || ''}
                      onChange={(e) => setLocalForm({ ...localForm, receipt_header_text: e.target.value })}
                      className={inputClass}
                    />
                  ) : (
                    <span className="font-medium text-gray-800">{config?.receipt_header_text || 'N/A'}</span>
                  )}
                </div>
                <div className={rowClass}>
                  <label className={labelClass}>Receipt Footer Text</label>
                  {editing ? (
                    <textarea
                      value={localForm.receipt_footer_text || ''}
                      onChange={(e) => setLocalForm({ ...localForm, receipt_footer_text: e.target.value })}
                      className={inputClass}
                      rows={2}
                    />
                  ) : (
                    <span className="font-medium text-gray-800">{config?.receipt_footer_text || 'Thank you for your payment!'}</span>
                  )}
                </div>
              </div>
            </section>

            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Student List Print</h3>
              <div className="space-y-4">
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={localForm.list_print_show_signatures !== false}
                    onChange={(e) => setLocalForm({ ...localForm, list_print_show_signatures: e.target.checked })}
                    disabled={!editing}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  Show signature block
                </label>

                {localForm.list_print_show_signatures !== false && (
                  <>
                    <div>
                      <label className={labelClass}>Signatories</label>
                      {editing ? (
                        <div className="space-y-2 mt-2">
                          {localForm.list_print_signatories.map((sig, i) => (
                            <div key={i} className="flex gap-2 items-center">
                              <input
                                type="text"
                                value={sig.label}
                                onChange={(e) => {
                                  const next = [...localForm.list_print_signatories]
                                  next[i] = { ...next[i], label: e.target.value }
                                  setLocalForm({ ...localForm, list_print_signatories: next })
                                }}
                                placeholder="Role, e.g. Adviser"
                                className={inputClass}
                              />
                              <input
                                type="text"
                                value={sig.name}
                                onChange={(e) => {
                                  const next = [...localForm.list_print_signatories]
                                  next[i] = { ...next[i], name: e.target.value }
                                  setLocalForm({ ...localForm, list_print_signatories: next })
                                }}
                                placeholder="Name (optional)"
                                className={inputClass}
                              />
                              <select
                                value={sig.section || ''}
                                onChange={(e) => {
                                  const next = [...localForm.list_print_signatories]
                                  next[i] = { ...next[i], section: e.target.value }
                                  setLocalForm({ ...localForm, list_print_signatories: next })
                                }}
                                className={`${inputClass} sm:w-44 shrink-0`}
                                title="Section this signatory handles. Leave blank to print on every section."
                              >
                                <option value="">All sections</option>
                                {sectionsList.map((s) => (
                                  <option key={s.id} value={s.name}>{s.name}</option>
                                ))}
                              </select>
                              <button
                                type="button"
                                onClick={() => setLocalForm({
                                  ...localForm,
                                  list_print_signatories: localForm.list_print_signatories.filter((_, x) => x !== i),
                                })}
                                className="p-2 rounded-lg text-red-600 hover:bg-red-50 transition-colors shrink-0"
                                title="Remove signatory"
                              >
                                <X size={16} />
                              </button>
                            </div>
                          ))}
                          {localForm.list_print_signatories.length >= 8 ? (
                            <p className="text-xs text-gray-400">Maximum of 8 signatories.</p>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setLocalForm({
                                ...localForm,
                                list_print_signatories: [...localForm.list_print_signatories, { label: '', name: '' }],
                              })}
                              className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
                            >
                              + Add signatory
                            </button>
                          )}
                          <p className="text-xs text-gray-400">
                            Leave the name blank to print an empty signature line. Pick a section to
                            sign only that section&apos;s list, or leave it blank to sign every list.
                          </p>
                        </div>
                      ) : (
                        <span className="font-medium text-gray-800">
                          {(config?.list_print_signatories || []).length
                            ? config.list_print_signatories.map((s) => s.label).join(', ')
                            : 'None configured'}
                        </span>
                      )}
                    </div>

                    <div className={rowClass}>
                      <label className={labelClass}>Signature Caption</label>
                      {editing ? (
                        <input
                          type="text"
                          value={localForm.list_print_signature_label}
                          onChange={(e) => setLocalForm({ ...localForm, list_print_signature_label: e.target.value })}
                          className={inputClass}
                        />
                      ) : (
                        <span className="font-medium text-gray-800">{config?.list_print_signature_label || 'Name and Signature'}</span>
                      )}
                    </div>
                  </>
                )}

                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={localForm.list_print_show_generated_at !== false}
                    onChange={(e) => setLocalForm({ ...localForm, list_print_show_generated_at: e.target.checked })}
                    disabled={!editing}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  Show "Document generated on ..." timestamp
                </label>
              </div>
            </section>

            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Advisers</h3>
              <div className="space-y-3">
                <p className="text-xs text-gray-400">
                  Advisers are managed here and picked up automatically by the cashier
                  settlement panel and the class list prints. Assign each adviser to a section.
                </p>
                {advisers.length === 0 && (
                  <p className="text-sm text-gray-400">No advisers yet — add the first one below.</p>
                )}
                <div className="space-y-2">
                  {advisers.map((adv) => {
                    const assignedSection = sectionsList.find(s => Number(s.adviser) === Number(adv.id))
                    return (
                      <div key={adv.id} className="flex flex-wrap gap-2 items-center">
                        <input
                          type="text"
                          defaultValue={adv.full_name}
                          onBlur={async (e) => {
                            const name = e.target.value.trim()
                            if (name && name !== adv.full_name) {
                              try { await adviserAPI.update(adv.id, { full_name: name }); loadAdvisers(); showToast('Adviser renamed') }
                              catch { showToast('Failed to rename adviser', 'error') }
                            } else { e.target.value = adv.full_name }
                          }}
                          className="flex-1 min-w-[160px] px-3 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900"
                        />
                        <select
                          value={assignedSection ? assignedSection.id : ''}
                          onChange={(e) => assignAdviserToSection(adv.id, e.target.value || null)}
                          disabled={adviserBusy}
                          className="px-3 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900 sm:w-44 shrink-0"
                          title="Section this adviser handles"
                        >
                          <option value="">No section</option>
                          {sectionsList.map((s) => (
                            <option key={s.id} value={s.id}>{s.name}{s.grade_year ? ` (${s.grade_year})` : ''}</option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => removeAdviser(adv.id)}
                          disabled={adviserBusy}
                          className="p-2 rounded-lg text-red-600 hover:bg-red-50 transition-colors shrink-0"
                          title="Remove adviser"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    )
                  })}
                </div>
                <div className="flex gap-2 items-center">
                  <input
                    type="text"
                    value={newAdviser}
                    onChange={(e) => setNewAdviser(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addAdviser() } }}
                    placeholder="New adviser name"
                    className="flex-1 px-3 py-2 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900"
                  />
                  <button
                    type="button"
                    onClick={addAdviser}
                    disabled={adviserBusy || !newAdviser.trim()}
                    className="px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 border border-blue-200 rounded-xl disabled:opacity-50 shrink-0"
                  >
                    + Add adviser
                  </button>
                </div>
                <div>
                  <label className={labelClass}>Daily Report — Checked by</label>
                  <input
                    type="text"
                    value={localForm.report_checked_by || ''}
                    onChange={(e) => setLocalForm({ ...localForm, report_checked_by: e.target.value })}
                    placeholder="Name printed as 'Checked by' on the Daily Collection & Disbursement Report"
                    className={inputClass}
                  />
                </div>
              </div>
            </section>

          </div>

          <div className="space-y-6">
            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">School Logo</h3>

              <div className="bg-gray-50 rounded-xl border border-gray-100 p-4">
                <div className="relative mb-4">
                  {logoPreview ? (
                    <div className="relative group">
                      <img
                        src={logoPreview}
                        alt="School logo preview"
                        className="w-full h-48 object-contain rounded-lg bg-white border border-gray-200"
                      />
                      {editing && (
                        <button
                          onClick={removeLogo}
                          className="absolute -top-2 -right-2 w-7 h-7 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center shadow-md transition-colors"
                          title="Remove logo"
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="w-full h-48 rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-400 bg-white">
                      <Image size={40} className="mb-2 opacity-50" />
                      <span className="text-xs text-center px-4">No logo uploaded</span>
                    </div>
                  )}
                </div>

                {editing && (
                  <div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleLogoSelect}
                      className="hidden"
                      id="logo-upload"
                    />
                    <label
                      htmlFor="logo-upload"
                      className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg cursor-pointer text-sm font-medium transition-colors border border-blue-200"
                    >
                      <Upload size={15} />
                      {logoFile ? 'Change Logo' : 'Upload Logo'}
                    </label>
                    <p className="text-xs text-gray-400 text-center mt-2">
                      JPG, PNG, GIF, WebP (max 5MB)
                    </p>
                    {logoFile && (
                      <p className="text-xs text-blue-600 text-center mt-1 font-medium truncate">
                        {logoFile.name}
                      </p>
                    )}
                  </div>
                )}

                {!editing && !logoPreview && (
                  <p className="text-xs text-gray-400 text-center">
                    No logo set
                  </p>
                )}
              </div>
            </section>

            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">System Information</h3>
              <div className="bg-gray-50 rounded-xl border border-gray-100 p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-500 text-sm">System Version</span>
                  <span className="font-medium text-gray-800 text-sm">v{systemVersion}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 text-sm">Database</span>
                  <span className="font-medium text-green-600 text-sm">Operational</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 text-sm">Last Updated</span>
                  <span className="font-medium text-gray-800 text-sm">
                    {config?.updated_at ? new Date(config.updated_at).toLocaleString() : 'N/A'}
                  </span>
                </div>
              </div>
            </section>
          </div>

        </div>
      </div>

      <style>{`
        @keyframes slide-up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .animate-slide-up { animation: slide-up 0.3s ease-out; }
      `}</style>
    </div>
  )
}