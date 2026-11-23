import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { Btn, Card, KpiCard, SectionCard, Spinner, TrendPill } from "../components/ui";

const SEMESTERS = [1, 2];

export default function ClassReport() {
  const { classId } = useParams();
  const [semester, setSemester] = useState(1);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setReport(await api(`/classes/${classId}/semester-report/?semester=${semester}`));
    } catch (err) {
      setError(err);
    }
  }, [classId, semester]);

  useEffect(() => {
    load();
  }, [load]);

  const completeCount = report?.students.filter((s) => s.final !== null).length || 0;
  const pendingCount = (report?.students.length || 0) - completeCount;

  return (
    <div className="flex flex-col w-full gap-space-lg">
      <section className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md bg-surface-container-lowest p-space-lg rounded-xl shadow-sm">
        <div className="flex flex-col gap-space-2xs">
          <div className="flex items-center gap-space-sm flex-wrap">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-primary bg-primary-fixed px-space-xs py-space-2xs rounded-lg font-semibold">
              Teacher's Portal
            </span>
            <span className="inline-flex items-center gap-space-xs text-on-surface-variant font-label-md text-label-md">
              <span className="w-2 h-2 rounded-full bg-tertiary-fixed-dim inline-block" />
              Semester report · computed by the grade engine
            </span>
          </div>
          <div className="flex items-center gap-space-md mt-space-2xs flex-wrap">
            <div className="relative">
              <select
                className="appearance-none bg-surface-container-low text-on-surface font-headline-sm text-headline-sm font-bold pl-space-md pr-space-xl py-space-xs rounded-xl focus:outline-none cursor-pointer hover:bg-surface-container transition-colors"
                value={String(semester)}
                onChange={(e) => setSemester(Number(e.target.value))}
              >
                {SEMESTERS.map((s) => (
                  <option key={s} value={s}>
                    Semester {s}
                  </option>
                ))}
              </select>
              <span className="material-symbols-outlined text-on-surface-variant pointer-events-none absolute right-2 top-2.5 text-base">
                expand_more
              </span>
            </div>
          </div>
          <div className="flex items-center gap-space-lg text-on-surface-variant font-body-sm text-body-sm mt-space-2xs flex-wrap">
            <span className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-sm text-primary">school</span>
              Subject: <strong className="text-on-surface font-semibold ml-1">{report?.class.subject ?? "…"}</strong>
            </span>
            <span className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-sm text-tertiary-container">groups</span>
              Section: <strong className="text-on-surface font-semibold ml-1">{report?.class.section ?? "…"}</strong>
            </span>
          </div>
        </div>
        <div className="flex items-center gap-space-sm flex-wrap self-start lg:self-center">
          <Btn variant="secondary" icon="table_chart" onClick={() => window.history.back()}>
            Back to Gradebook
          </Btn>
          <Btn variant="secondary" icon="print" onClick={() => window.print()}>
            Print
          </Btn>
        </div>
      </section>

      {error ? (
        <Card className="p-space-xl">
          <p className="font-body-md text-body-md text-on-error-container">{error.message}</p>
        </Card>
      ) : !report ? (
        <Spinner />
      ) : (
        <>
          <section className="grid grid-cols-1 md:grid-cols-3 gap-space-lg">
            <KpiCard
              label="Class Semester Final"
              icon="workspace_premium"
              value={report.class_final ?? "—"}
              progress={report.class_final ?? 0}
              scaleLabel="Scale 100"
              footnote={report.complete ? "All learners finalized" : "Pending learner grades"}
            />
            <KpiCard label="Finalized" icon="check_circle" value={completeCount} trendTone="good" />
            <KpiCard
              label="Pending"
              icon="hourglass_top"
              value={pendingCount}
              trend={pendingCount > 0 ? "incomplete quarters" : "none"}
              trendTone={pendingCount > 0 ? "warn" : "good"}
            />
          </section>

          <SectionCard
            title={`Semester ${semester} — per-learner grades`}
            sub="Quarterly grades, semester final, and encoding gaps"
          >
            <p className="mb-space-sm flex items-center gap-space-xs font-label-sm text-label-sm text-on-surface-variant md:hidden">
              <span className="material-symbols-outlined text-base">swipe</span>
              Swipe horizontally to review quarterly grades.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="min-w-[220px] max-md:sticky max-md:left-0 max-md:z-20 max-md:bg-surface-container-lowest max-md:shadow-[2px_0_0_rgba(210,224,232,0.8)]">Learner</th>
                    <th className="text-center">Q{semester * 2 - 1}</th>
                    <th className="text-center">Q{semester * 2}</th>
                    <th className="text-right">Semester Final</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {report.students.map((s) => (
                    <tr key={s.student_id}>
                      <td className="max-md:sticky max-md:left-0 max-md:z-10 max-md:bg-surface-container-lowest max-md:shadow-[2px_0_0_rgba(210,224,232,0.8)]">
                        <p className="font-label-md text-label-md text-on-surface">{s.full_name}</p>
                        <p className="font-data-tabular-sm text-data-tabular-sm text-on-surface-variant">{s.lrn}</p>
                      </td>
                      <td className="text-center font-data-tabular-md text-data-tabular-md text-on-surface">
                        {s[`q${semester * 2 - 1}`] ?? "—"}
                        {s[`blanks_q${semester * 2 - 1}`] > 0 && (
                          <TrendPill tone="warn">{s[`blanks_q${semester * 2 - 1}`]} blank</TrendPill>
                        )}
                      </td>
                      <td className="text-center font-data-tabular-md text-data-tabular-md text-on-surface">
                        {s[`q${semester * 2}`] ?? "—"}
                        {s[`blanks_q${semester * 2}`] > 0 && (
                          <TrendPill tone="warn">{s[`blanks_q${semester * 2}`]} blank</TrendPill>
                        )}
                      </td>
                      <td className="text-right">
                        {s.final !== null ? (
                          <span className="inline-flex items-center font-bold text-tertiary-container bg-surface-container-high px-2 py-0.5 rounded-full text-data-tabular-sm">
                            {s.final}
                          </span>
                        ) : (
                          <span className="text-on-surface-variant/50">—</span>
                        )}
                      </td>
                      <td>
                        {s.final !== null ? (
                          <TrendPill tone="good" icon="check_circle">finalized</TrendPill>
                        ) : s[`q${semester * 2 - 1}`] !== null || s[`q${semester * 2}`] !== null ? (
                          <TrendPill tone="info">in progress</TrendPill>
                        ) : (
                          <TrendPill tone="neutral">no grades yet</TrendPill>
                        )}
                      </td>
                    </tr>
                  ))}
                  {report.students.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-space-lg text-center font-body-md text-body-md text-on-surface-variant">
                        No learners in this section yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </SectionCard>
        </>
      )}
    </div>
  );
}
