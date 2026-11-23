import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Card, EmptyState, ErrorBanner, PageHeader, SectionCard, Spinner, TrendPill } from "../components/ui";

export default function AdminClassRecords() {
  const navigate = useNavigate();
  const [assignments, setAssignments] = useState(null);
  const [grades, setGrades] = useState({});
  const [error, setError] = useState(null);
  const [sectionFilter, setSectionFilter] = useState("all");

  const load = useCallback(async () => {
    try {
      const list = await api("/admin/assignments/?page_size=200");
      setAssignments(list.results || []);
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const classIds = useMemo(() => (assignments || []).map((a) => a.id), [assignments]);

  useEffect(() => {
    if (!assignments) return;
    Promise.all(
      assignments.map(async (a) => {
        const g = await api(`/classes/${a.id}/grades/?quarter=1`).catch(() => null);
        return [a.id, g];
      })
    ).then((entries) => setGrades(Object.fromEntries(entries)));
  }, [assignments]);

  if (error) return <ErrorBanner error={error} />;
  if (!assignments) return <Spinner />;

  const sections = [...new Set(assignments.map((a) => a.section_name))];
  const rows = assignments.filter(
    (a) => sectionFilter === "all" || a.section_name === sectionFilter
  );

  const gradeStats = (id) => {
    const g = grades[id];
    if (!g) return null;
    const withGrades = g.students.filter((s) => s.grade !== null);
    const avg = withGrades.length
      ? (withGrades.reduce((sum, s) => sum + s.grade, 0) / withGrades.length).toFixed(1)
      : null;
    return { total: g.students.length, withGrades: withGrades.length, avg };
  };

  return (
    <>
      <PageHeader
        eyebrow="Class Records"
        title="All Class Gradebooks"
        sub="Open any class's gradebook or report — read-only inspection for administrators."
      />
      <Card className="p-space-lg">
        <div className="flex items-center gap-space-2xs bg-surface-container-low p-space-2xs rounded-xl w-fit">
          <button
            onClick={() => setSectionFilter("all")}
            className={`px-space-md py-space-2xs rounded-lg font-label-sm text-label-sm ${
              sectionFilter === "all"
                ? "bg-surface-container-lowest text-on-surface shadow-sm font-semibold"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            All sections
          </button>
          {sections.map((s) => (
            <button
              key={s}
              onClick={() => setSectionFilter(s)}
              className={`px-space-md py-space-2xs rounded-lg font-label-sm text-label-sm ${
                sectionFilter === s
                  ? "bg-surface-container-lowest text-on-surface shadow-sm font-semibold"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </Card>

      {rows.length === 0 ? (
        <Card className="p-space-xl">
          <EmptyState icon="table_chart" title="No class assignments yet" sub="Create them under Academics." />
        </Card>
      ) : (
        <SectionCard title="Classes" sub={`${rows.length} classes`}>
          <div className="flex flex-col gap-space-md">
            {rows.map((a) => {
              const st = gradeStats(a.id);
              return (
                <div key={a.id} className="flex flex-wrap items-center gap-space-md bg-surface-container-low rounded-xl p-space-md">
                  <div className="flex-1 min-w-0">
                    <p className="font-label-md text-label-md text-on-surface">{a.subject_name}</p>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">
                      {a.section_name} · {a.teacher_name}
                    </p>
                  </div>
                  {st && st.avg !== null ? (
                    <TrendPill tone="info">Q1 avg {st.avg}</TrendPill>
                  ) : (
                    <TrendPill tone="neutral">no grades yet</TrendPill>
                  )}
                  {st && (
                    <span className="font-data-tabular-sm text-data-tabular-sm text-on-surface-variant">
                      {st.withGrades}/{st.total} graded
                    </span>
                  )}
                  <Btn variant="secondary" icon="table_chart" onClick={() => navigate(`/gradebook/${a.id}`)}>
                    Gradebook
                  </Btn>
                  <Btn variant="secondary" icon="summarize" onClick={() => navigate(`/classes/${a.id}/report`)}>
                    Report
                  </Btn>
                </div>
              );
            })}
          </div>
        </SectionCard>
      )}
    </>
  );
}
