import { forwardRef, useState } from 'react'
import { useSchoolConfig } from '../contexts/SchoolConfigContext'

const StudentSectionReport = forwardRef(({ students, filters, schoolName }, ref) => {
  // printLogo is a data URI - an external image here makes the print iframe
  // hang in Electron (react-to-print#511).
  const { config, printLogo } = useSchoolConfig()
  // Signature block comes entirely from School Config > Student List Print.
  // No hardcoded roles: if nothing is configured, none are printed.
  const allSignatories = Array.isArray(config?.list_print_signatories)
    ? config.list_print_signatories.filter((s) => s && s.label)
    : []
  // A signatory scoped to a section only signs that section's list; one with
  // no section (e.g. Principal) signs every list.
  const printedSection = (filters?.section || '').trim()
  const norm = (v) => String(v || '').trim().toLowerCase()
  const signatories = printedSection
    ? allSignatories.filter((s) => !norm(s.section) || norm(s.section) === norm(printedSection))
    : allSignatories.filter((s) => !norm(s.section))
  const sigLabel = config?.list_print_signature_label ?? 'Name and Signature'
  const showSignatures = config?.list_print_show_signatures !== false
  const showGeneratedAt = config?.list_print_show_generated_at !== false
  const [imgError, setImgError] = useState(false)
  const name = schoolName || config?.school_name || 'School Name'

  const formatDate = () => {
    return new Date().toLocaleDateString('en-US', {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  }

  const getSchoolYear = () => {
    const now = new Date()
    const year = now.getFullYear()
    return now.getMonth() >= 5 ? `${year} - ${year + 1}` : `${year - 1} - ${year}`
  }

  const getTrackStrandCourse = (student) => {
    const lt = student.level_type
    if (lt === 'BUN' || lt === 'COL') {
      return student.course || student.course_name || student.track_strand || student.strand_name || ''
    }
    return student.track_strand || student.strand_name || ''
  }

  // Derive the printed strand/course line from the section's own students
  const studentStrands = [...new Set(students.map(getTrackStrandCourse).filter(Boolean))]
  const isCourseLevel = students.length > 0 && students.every(s => s.level_type === 'BUN' || s.level_type === 'COL')
  const strandHeader = isCourseLevel ? 'Course' : 'Track/Strand'
  const strandDisplay = studentStrands.length > 0
    ? studentStrands.join(' / ')
    : (filters?.strand || (isCourseLevel ? 'All Courses' : 'All Tracks/Strands'))

  const getGradeYear = (student) => {
    const lt = student.level_type
    if (lt === 'SHS') return student.shs_grade ? `Grade ${student.shs_grade}` : student.grade || 'N/A'
    if (lt === 'BUN') {
      const ym = { '1': '1st Year', '2': '2nd Year' }
      return student.college_year ? ym[student.college_year] || `${student.college_year} Year` : student.year_level || student.grade || 'N/A'
    }
    return student.year_level || student.grade || 'N/A'
  }

  return (
    <div ref={ref} className="print-report" style={{ fontFamily: 'Arial, sans-serif', fontSize: '10px', lineHeight: 1.25, color: '#000', background: '#fff', padding: '4mm' }}>
      <div className="flex items-center justify-center gap-3 mb-4 pb-2 border-b-2 border-gray-300">
        <div className="w-10 h-10 flex-shrink-0">
          {!imgError && printLogo ? (
            <img src={printLogo} alt="School Logo" className="w-full h-full object-contain"
              onError={() => setImgError(true)} />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-blue-600 text-white text-lg font-bold rounded">
              {(config?.school_name || 'S')[0]}
            </div>
          )}
        </div>
        <div className="text-center">
          <p className="text-sm font-bold uppercase" style={{ color: '#000' }}>{name}</p>
          <p className="text-xs font-bold" style={{ color: '#000' }}>CLASS STUDENT LIST</p>
          <p className="text-[9px]" style={{ color: '#333' }}>School Year: {getSchoolYear()}</p>
        </div>
      </div>

      <div className="p-2 rounded mb-3 border-l-2 border-gray-400" style={{ background: '#f5f5f5' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px', fontSize: '9px' }}>
          <div><strong>Section:</strong> {filters?.section || 'All Sections'}</div>
          <div><strong>{strandHeader}:</strong> {strandDisplay}</div>
          <div><strong>Grade Level:</strong> {filters?.gradeLevel || 'All Grade Levels'}</div>
          <div><strong>Total Students:</strong> {students.length}</div>
        </div>
      </div>

      <table className="w-full border-collapse mb-4" style={{ fontSize: '9px' }}>
        <thead>
          <tr style={{ background: '#f0f0f0', color: '#000' }}>
            <th className="border border-gray-400 px-1 py-1 text-center font-bold" style={{ width: '4%' }}>No.</th>
            <th className="border border-gray-400 px-1 py-1 text-left font-bold" style={{ width: '13%' }}>LRN</th>
            <th className="border border-gray-400 px-1 py-1 text-left font-bold" style={{ width: '31%' }}>Full Name</th>
            <th className="border border-gray-400 px-1 py-1 text-left font-bold" style={{ width: '8%' }}>Gender</th>
            <th className="border border-gray-400 px-1 py-1 text-left font-bold" style={{ width: '12%' }}>Grade/Year</th>
            <th className="border border-gray-400 px-1 py-1 text-left font-bold" style={{ width: '20%' }}>{strandHeader}</th>
            <th className="border border-gray-400 px-1 py-1 text-left font-bold" style={{ width: '12%' }}>Contact No.</th>
          </tr>
        </thead>
        <tbody>
          {students.map((s, i) => (
            <tr key={s.id} style={{ background: i % 2 === 0 ? '#fff' : '#fafafa' }}>
              <td className="border border-gray-400 px-1 py-0.5 text-center" style={{ color: '#000' }}>{i + 1}</td>
              <td className="border border-gray-400 px-1 py-0.5" style={{ color: '#000' }}>{s.lrn || s.student_id || 'N/A'}</td>
              <td className="border border-gray-400 px-1 py-0.5 font-medium" style={{ color: '#000' }}>
                {s.last_name?.toUpperCase()}, {s.first_name} {s.middle_name ? `${s.middle_name.charAt(0)}.` : ''}
              </td>
              <td className="border border-gray-400 px-1 py-0.5" style={{ color: '#000' }}>{s.gender || ''}</td>
              <td className="border border-gray-400 px-1 py-0.5" style={{ color: '#000' }}>{getGradeYear(s)}</td>
              <td className="border border-gray-400 px-1 py-0.5" style={{ color: '#000' }}>{getTrackStrandCourse(s)}</td>
              <td className="border border-gray-400 px-1 py-0.5" style={{ color: '#000' }}>{s.contact_number || s.contact || ''}</td>
            </tr>
          ))}
          {students.length === 0 && (
            <tr>
              <td colSpan={7} className="border border-gray-400 py-6 text-center italic" style={{ color: '#888' }}>No students found.</td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="pt-3 border-t border-gray-300">
        {showSignatures && signatories.length > 0 && (
          <div className="flex justify-between mt-10 gap-6">
            {signatories.map((sig, i) => (
              <div key={`${sig.label}-${i}`} className="flex-1 text-center">
                <div className="border-t border-gray-600 pt-1 text-[9px] font-bold">{sig.label}</div>
                {sig.name && <div className="text-[8px]" style={{ color: '#000' }}>{sig.name}</div>}
                {!sig.name && <p className="text-[8px]" style={{ color: '#666' }}>{sigLabel}</p>}
              </div>
            ))}
          </div>
        )}
        {showGeneratedAt && (
          <p className="text-center text-[8px] mt-4" style={{ color: '#888' }}>Document generated on {formatDate()}</p>
        )}
      </div>

      <style>{`
        @media print {
          @page { size: 8.5in 13in portrait; margin: 10mm; }
          .print-report { padding: 0 !important; margin: 0 !important; font-size: 10px !important; }
          .print-report * { color: #000 !important; }
          .print-report th, .print-report td { font-size: 9px !important; padding: 2px 4px !important; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        }
      `}</style>
    </div>
  )
})

StudentSectionReport.displayName = 'StudentSectionReport'
export default StudentSectionReport
