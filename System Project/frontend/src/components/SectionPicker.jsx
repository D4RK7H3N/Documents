import { useMemo, useState } from 'react'

/**
 * Picks a section for a student.
 *
 * A section is not just a name: it carries the strand and the year level, so
 * the school already has one per class. Asking for a free-text name made it
 * easy to put a student in a section that does not exist, or in one that
 * belongs to another strand - the class list and the student's record then
 * disagreed. This offers the existing sections (with their strand shown),
 * grouped by year level, and still allows typing a name for a class that has
 * to be created on the spot.
 *
 *   <SectionPicker
 *     sections={sections}
 *     value={form.section}
 *     onChange={(name) => setForm({ ...form, section: name })}
 *   />
 */
export default function SectionPicker({
  sections = [],
  value = '',
  onChange,
  gradeLevel = '',
  levelType = '',
  placeholder = 'Select a section',
  allowNew = true,
  inputClass = 'w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-900',
}) {
  const [custom, setCustom] = useState('')
  const [showCustom, setShowCustom] = useState(false)

  const options = useMemo(() => {
    let list = sections.filter(Boolean)
    if (levelType) list = list.filter(s => !s.level_type || s.level_type === levelType)
    if (gradeLevel) list = list.filter(s => !s.grade_year || s.grade_year === gradeLevel)
    return [...list].sort((a, b) => {
      const g = (a.grade_year || '').localeCompare(b.grade_year || '')
      return g !== 0 ? g : String(a.name).localeCompare(String(b.name))
    })
  }, [sections, levelType, gradeLevel])

  // Group by year level so the list reads the way the roster is organised.
  const groups = useMemo(() => {
    const byGrade = new Map()
    for (const s of options) {
      const key = s.grade_year || 'Other'
      if (!byGrade.has(key)) byGrade.set(key, [])
      byGrade.get(key).push(s)
    }
    return [...byGrade.entries()]
  }, [options])

  const known = options.some(s => s.name === value)
  const needsCustom = allowNew && value && !known

  const label = (s) => {
    const strand = s.strand_name || s.course_name
    return strand ? `${s.name} — ${strand}` : s.name
  }

  return (
    <div className="space-y-2">
      <select
        value={known || !value ? value : ''}
        onChange={(e) => {
          const v = e.target.value
          if (v === '__new__') {
            setShowCustom(true)
            return
          }
          setShowCustom(false)
          setCustom('')
          onChange?.(v)
        }}
        className={inputClass}
      >
        <option value="">{placeholder}</option>
        {groups.map(([grade, list]) => (
          <optgroup key={grade} label={grade}>
            {list.map(s => (
              <option key={s.id ?? s.name} value={s.name}>{label(s)}</option>
            ))}
          </optgroup>
        ))}
        {allowNew && (
          <option value="__new__">+ Other (type a new section name)</option>
        )}
      </select>

      {(showCustom || needsCustom) && (
        <input
          type="text"
          value={custom || (needsCustom ? value : '')}
          onChange={(e) => {
            setCustom(e.target.value)
            onChange?.(e.target.value)
          }}
          placeholder="New section name"
          className={inputClass}
        />
      )}
    </div>
  )
}
