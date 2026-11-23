import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { Btn, Card, ErrorBanner, KpiCard, PageHeader, SectionCard, Spinner, TrendPill } from "../components/ui";

function GradeCell({ value }) {
  if (value === null || value === undefined) {
    return <span className="text-on-surface-variant/40">—</span>;
  }
  return (
    <span className="inline-flex items-center justify-center min-w-[34px] px-2 py-0.5 rounded-lg bg-surface-container-high font-data-tabular-sm text-data-tabular-sm font-semibold text-on-surface">
      {value}
    </span>
  );
}

const TYPE_TONES = {
  core: "info",
  applied: "warn",
  specialized: "neutral",
};

export default function StudentRecord() {
  const { studentId } = useParams();
  const [record, setRecord] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api(`/students/${studentId}/record/`)
      .then(setRecord)
      .catch(setError);
  }, [studentId]);

  if (error) {
    return (
      <Card className="p-space-xl">
        <p className="font-body-md text-body-md text-on-error-container">{error.message}</p>
      </Card>
    );
  }
  if (!record) return <Spinner />;

  const s = record.student;

  return (
    <>
      <PageHeader
        eyebrow={
          <span className="flex items-center gap-space-2xs">
            <Link to="/students" className="hover:text-on-surface">Students</Link>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span>Student Record</span>
          </span>
        }
        title={s.name}
        sub={`${s.grade_level} · ${s.section} · S.Y. ${s.school_year} · LRN ${s.lrn}`}
        actions={
          <TrendPill tone="info" icon="schedule">
            {record.last_updated
              ? `Last updated ${new Date(record.last_updated).toLocaleString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}`
              : "No grades yet"}
          </TrendPill>
        }
      />

      <section className="grid grid-cols-1 md:grid-cols-3 gap-space-lg">
        <KpiCard
          label="General Average — Semester 1"
          icon="workspace_premium"
          value={record.general_averages.s1 ?? "—"}
          progress={record.general_averages.s1 ?? 0}
          scaleLabel="Scale 100"
        />
        <KpiCard
          label="General Average — Semester 2"
          icon="workspace_premium"
          value={record.general_averages.s2 ?? "—"}
          progress={record.general_averages.s2 ?? 0}
          progressTone="bg-tertiary-container"
          scaleLabel="Scale 100"
        />
        <KpiCard label="Subjects Enrolled" icon="menu_book" value={record.subjects.length} />
      </section>

      <SectionCard
        title="Full-year grade record"
        sub="Quarterly grades, semester finals and general averages — computed by the grade engine"
      >
        {record.subjects.length === 0 ? (
          <p className="py-space-lg text-center font-body-md text-body-md text-on-surface-variant">
            No subjects assigned to this section yet.
          </p>
        ) : (
          <>
          <p className="mb-space-sm flex items-center gap-space-xs font-label-sm text-label-sm text-on-surface-variant md:hidden">
            <span className="material-symbols-outlined text-base">swipe</span>
            Swipe horizontally to review the full-year record.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="min-w-[220px] max-md:sticky max-md:left-0 max-md:z-20 max-md:bg-surface-container-lowest max-md:shadow-[2px_0_0_rgba(210,224,232,0.8)]">Subject</th>
                  <th className="text-center">Q1</th>
                  <th className="text-center">Q2</th>
                  <th className="text-right bg-secondary-container/40">S1 Final</th>
                  <th className="text-center">Q3</th>
                  <th className="text-center">Q4</th>
                  <th className="text-right bg-secondary-container/40">S2 Final</th>
                </tr>
              </thead>
              <tbody>
                {record.subjects.map((row) => (
                  <tr key={row.subject}>
                    <td className="max-md:sticky max-md:left-0 max-md:z-10 max-md:bg-surface-container-lowest max-md:shadow-[2px_0_0_rgba(210,224,232,0.8)]">
                      <p className="font-label-md text-label-md text-on-surface">{row.subject}</p>
                      <TrendPill tone={TYPE_TONES[row.subject_type] || "neutral"}>{row.subject_type}</TrendPill>
                    </td>
                    <td className="text-center"><GradeCell value={row.q1} /></td>
                    <td className="text-center"><GradeCell value={row.q2} /></td>
                    <td className="text-right bg-secondary-container/20">
                      <span className="font-data-tabular-lg text-data-tabular-lg font-bold text-primary">
                        {row.s1 ?? "—"}
                      </span>
                    </td>
                    <td className="text-center"><GradeCell value={row.q3} /></td>
                    <td className="text-center"><GradeCell value={row.q4} /></td>
                    <td className="text-right bg-secondary-container/20">
                      <span className="font-data-tabular-lg text-data-tabular-lg font-bold text-primary">
                        {row.s2 ?? "—"}
                      </span>
                    </td>
                  </tr>
                ))}
                <tr className="bg-surface-container-low">
                  <td className="font-headline-sm text-headline-sm text-on-surface max-md:sticky max-md:left-0 max-md:z-10 max-md:bg-surface-container-low">General Average</td>
                  <td colSpan={2} />
                  <td className="text-right">
                    <span className="inline-flex items-center font-bold text-tertiary-container bg-surface-container-high px-2 py-0.5 rounded-full text-data-tabular-sm">
                      {record.general_averages.s1 ?? "Incomplete"}
                    </span>
                  </td>
                  <td colSpan={2} />
                  <td className="text-right">
                    <span className="inline-flex items-center font-bold text-tertiary-container bg-surface-container-high px-2 py-0.5 rounded-full text-data-tabular-sm">
                      {record.general_averages.s2 ?? "Incomplete"}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          </>
        )}
      </SectionCard>

      <div className="flex items-center gap-space-sm">
        <Btn variant="secondary" icon="arrow_back" onClick={() => window.history.back()}>
          Back
        </Btn>
        <Btn variant="secondary" icon="print" onClick={() => window.print()}>
          Print record
        </Btn>
      </div>
    </>
  );
}
