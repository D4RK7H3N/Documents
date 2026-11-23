import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Btn, Card, ErrorBanner, KpiCard, PageHeader, SectionCard, Spinner, TrendPill } from "../components/ui";

function FinalPill({ value }) {
  if (value === null || value === undefined) return <span className="text-on-surface-variant/40">—</span>;
  if (value >= 90) {
    return <span className="inline-flex px-2 py-0.5 rounded-full bg-tertiary-fixed text-[#005236] font-data-tabular-sm font-bold">{value}</span>;
  }
  if (value < 75) {
    return <span className="inline-flex px-2 py-0.5 rounded-full bg-error-container text-on-error-container font-data-tabular-sm font-bold">{value}</span>;
  }
  return <span className="font-data-tabular-sm text-data-tabular-sm text-on-surface">{value}</span>;
}

export default function Reports() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [semester, setSemester] = useState(1);
  const [sectionId, setSectionId] = useState("");
  const [sections, setSections] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        if (isAdmin) {
          setSections(await api("/admin/sections/?page_size=200").then((d) => d.results || d));
        } else {
          const classes = await api("/teacher/classes/").then((d) => d.results || d);
          const unique = new Map();
          for (const c of classes) {
            if (!unique.has(c.section)) {
              unique.set(c.section, { id: c.section, name: c.section_name, grade_level: "" });
            }
          }
          setSections([...unique.values()]);
        }
      } catch (err) {
        setError(err);
      }
    };
    load();
  }, [isAdmin]);

  const loadReport = useCallback(async () => {
    if (!sectionId) return;
    setError(null);
    try {
      setReport(await api(`/sections/${sectionId}/report/?semester=${semester}`));
    } catch (err) {
      setError(err);
    }
  }, [sectionId, semester]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  useEffect(() => {
    if (sections?.length && !sectionId) setSectionId(String(sections[0].id));
  }, [sections, sectionId]);

  const stats = useMemo(() => {
    if (!report) return null;
    const gas = report.students.map((s) => s.general_average).filter((g) => g !== null);
    const classAvg = gas.length ? (gas.reduce((a, b) => a + b, 0) / gas.length).toFixed(1) : null;
    const honor = gas.filter((g) => g >= 90).length;
    const atRisk = gas.filter((g) => g < 75).length;
    return { classAvg, honor, atRisk, enrolled: report.students.length, pending: report.students.length - gas.length };
  }, [report]);

  return (
    <>
      <PageHeader
        eyebrow="Records"
        title="Section Reports"
        sub="Semester finals per learner across every subject — honor roll, at-risk flags and print-ready output."
        actions={
          <div className="flex items-center gap-space-sm flex-wrap">
            <div className="flex items-center gap-space-2xs bg-surface-container-low p-space-2xs rounded-xl">
              {[1, 2].map((s) => (
                <button
                  key={s}
                  onClick={() => setSemester(s)}
                  className={`px-space-md py-space-2xs rounded-lg font-label-md text-label-md ${
                    semester === s
                      ? "bg-surface-container-lowest text-on-surface shadow-sm font-semibold"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  Semester {s}
                </button>
              ))}
            </div>
            <Btn variant="secondary" icon="print" onClick={() => window.print()} disabled={!report}>
              Print
            </Btn>
          </div>
        }
      />
      {error && <div className="mb-space-sm"><ErrorBanner error={error} /></div>}

      <Card className="p-space-lg">
        <p className="font-label-md text-label-md text-on-surface-variant mb-space-2xs">Section</p>
        <select
          value={sectionId}
          onChange={(e) => setSectionId(e.target.value)}
          className="appearance-none bg-surface-container-low text-on-surface font-headline-sm text-headline-sm font-bold pl-space-md pr-space-xl py-space-xs rounded-xl focus:outline-none cursor-pointer hover:bg-surface-container transition-colors"
        >
          {!sections?.length && <option value="">No sections available</option>}
          {sections?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} {s.grade_level ? `(${s.grade_level})` : ""}
            </option>
          ))}
        </select>
      </Card>

      {!report ? (
        error ? null : <Spinner />
      ) : (
        <>
          <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-space-lg">
            <KpiCard label="Enrolled" icon="group" value={stats.enrolled} />
            <KpiCard
              label="Section General Average"
              icon="workspace_premium"
              value={stats.classAvg ?? "—"}
              progress={stats.classAvg ?? 0}
              scaleLabel="Scale 100"
            />
            <KpiCard
              label="Honor Roll (≥ 90)"
              icon="military_tech"
              value={stats.honor}
              trend={stats.honor > 0 ? "top quintile" : "none yet"}
              trendTone="good"
            />
            <KpiCard
              label="At Risk (< 75)"
              icon="warning"
              value={stats.atRisk}
              trend={stats.atRisk > 0 ? "needs intervention" : "none"}
              trendTone={stats.atRisk > 0 ? "bad" : "good"}
            />
          </section>

          <SectionCard
            title={`Semester ${semester} — learner × subject matrix`}
            sub="Semester final grades per subject, computed by the grade engine"
          >
            <p className="mb-space-sm flex items-center gap-space-xs font-label-sm text-label-sm text-on-surface-variant md:hidden">
              <span className="material-symbols-outlined text-base">swipe</span>
              Swipe horizontally to compare every subject.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="min-w-[220px] max-md:sticky max-md:left-0 max-md:z-20 max-md:bg-surface-container-lowest max-md:shadow-[2px_0_0_rgba(210,224,232,0.8)]">Learner</th>
                    {report.subjects.map((s) => (
                      <th key={s.id} className="text-center min-w-[90px]">
                        {s.name}
                      </th>
                    ))}
                    <th className="text-right bg-secondary-container/40 text-primary font-bold">General Avg</th>
                  </tr>
                </thead>
                <tbody>
                  {report.students.map((s) => (
                    <tr key={s.student_id}>
                      <td className="max-md:sticky max-md:left-0 max-md:z-10 max-md:bg-surface-container-lowest max-md:shadow-[2px_0_0_rgba(210,224,232,0.8)]">
                        <button
                          onClick={() => navigate(`/students/${s.student_id}/record`)}
                          className="text-left hover:text-primary transition-colors"
                        >
                          <p className="font-label-md text-label-md text-on-surface">{s.full_name}</p>
                          <p className="font-data-tabular-sm text-data-tabular-sm text-on-surface-variant">{s.lrn}</p>
                        </button>
                      </td>
                      {report.subjects.map((sub, i) => (
                        <td key={sub.id} className="text-center">
                          <FinalPill value={s.finals[i]} />
                        </td>
                      ))}
                      <td className="text-right bg-secondary-container/20">
                        <span className="inline-flex items-center font-bold text-primary bg-surface-container-high px-2 py-0.5 rounded-full text-data-tabular-sm">
                          {s.general_average ?? "—"}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {report.students.length === 0 && (
                    <tr>
                      <td colSpan={report.subjects.length + 2} className="p-space-lg text-center font-body-md text-body-md text-on-surface-variant">
                        No learners in this section yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="mt-space-sm font-label-sm text-label-sm text-on-surface-variant">
              {"Green \u2265 90 (honor roll) \u00b7 red < 75 (at risk) \u00b7 click a learner for their full-year record."}
            </p>
          </SectionCard>
        </>
      )}
    </>
  );
}
