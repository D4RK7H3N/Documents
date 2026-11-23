import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Btn, Card, KpiCard, TrendPill } from "../components/ui";

const QUARTERS = [1, 2, 3, 4];

function FilterPills({ options, value, onChange }) {
  return (
    <div className="flex items-center gap-space-2xs bg-surface-container-low border border-outline-variant/70 p-space-2xs rounded-lg overflow-x-auto">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`min-h-11 px-space-md py-space-xs rounded-lg font-label-sm text-label-sm whitespace-nowrap ${
            value === opt.value
              ? "bg-surface-container-lowest text-on-surface shadow-sm font-semibold"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function QuarterPills({ quarter, onChange, lockedSet }) {
  return (
    <FilterPills
      options={QUARTERS.map((q) => ({ value: q, label: lockedSet?.has(q) ? `Q${q} 🔒` : `Q${q}` }))}
      value={quarter}
      onChange={onChange}
    />
  );
}

function TeacherDashboard({ user }) {
  const navigate = useNavigate();
  const [quarter, setQuarter] = useState(1);
  const [classes, setClasses] = useState(null);
  const [details, setDetails] = useState([]);
  const [classFilter, setClassFilter] = useState("all");
  const [error, setError] = useState(null);

  useEffect(() => {
    api("/teacher/classes/")
      .then((d) => setClasses(d.results || d))
      .catch(setError);
  }, []);

  useEffect(() => {
    if (!classes) return;
    setError(null);
    Promise.all(
      classes.map(async (c) => {
        const [assessments, grades] = await Promise.all([
          api(`/classes/${c.id}/assessments/?quarter=${quarter}`),
          api(`/classes/${c.id}/grades/?quarter=${quarter}`),
        ]);
        const rows = grades.students || [];
        const totalBlanks = rows.reduce((sum, r) => sum + (r.blanks || 0), 0);
        const filled = rows.filter((r) => r.grade !== null);
        const avg = filled.length
          ? (filled.reduce((s, r) => s + r.grade, 0) / filled.length).toFixed(1)
          : null;
        const complete = rows.length > 0 && rows.every((r) => r.blanks === 0 && r.grade !== null);
        const pending = assessments.filter(() => totalBlanks > 0).length;
        return { ...c, assessments, rows, avg, complete, totalBlanks, pending };
      })
    )
      .then(setDetails)
      .catch(setError);
  }, [classes, quarter]);

  const kpis = useMemo(() => {
    const learners = details.reduce((n, c) => n + (c.rows?.length || 0), 0);
    const toEncode = details.reduce((n, c) => n + (c.totalBlanks > 0 ? c.pending : 0), 0);
    const avgs = details.map((c) => Number(c.avg)).filter((n) => !Number.isNaN(n));
    const classAvg = avgs.length ? (avgs.reduce((a, b) => a + b, 0) / avgs.length).toFixed(1) : null;
    const locked = new Set(details.flatMap((c) => c.locked_quarters || []));
    const totalAssessments = details.reduce((n, c) => n + (c.assessments?.length || 0), 0);
    const postingRate = totalAssessments
      ? Math.round(((totalAssessments - toEncode) / totalAssessments) * 100)
      : 0;
    return { learners, toEncode, classAvg, locked, totalAssessments, postingRate };
  }, [details]);

  if (error) {
    return (
      <Card className="p-space-xl">
        <p className="font-body-md text-body-md text-on-error-container">{error.message}</p>
      </Card>
    );
  }
  if (!classes) return null;

  const attention = details
    .filter((c) => classFilter === "all" || String(c.id) === classFilter)
    .filter((c) => c.totalBlanks > 0);

  return (
    <>
      <section className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md bg-surface-container-lowest p-space-xl rounded-xl shadow-sm">
        <div className="flex flex-col gap-space-2xs">
          <div className="flex items-center gap-space-xs text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider">
            <span className="inline-block w-2 h-2 rounded-full bg-primary" />
            DepEd Order No. 8, s. 2015 / S.Y. {classes[0]?.school_year || ""}
          </div>
          <h1 className="font-headline-xl text-headline-xl text-on-surface tracking-tight">
            Academic Overview
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Monitoring {kpis.learners} learners across {classes.length} classes for Quarter {quarter}
          </p>
        </div>
        <div className="flex items-center gap-space-sm flex-wrap">
          <Btn variant="secondary" icon="class" onClick={() => navigate("/classes")}>
            My Classes
          </Btn>
          <Btn
            icon="edit_note"
            onClick={() => {
              const target = details.find((c) => c.totalBlanks > 0) || details[0];
              if (target) navigate(`/gradebook/${target.id}?quarter=${quarter}`);
            }}
          >
            Encode Scores
          </Btn>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-space-lg">
        <KpiCard
          label="Class Mean Grade"
          icon="school"
          value={kpis.classAvg ?? "—"}
          progress={kpis.classAvg ?? 0}
          scaleLabel="Scale 100"
        />
        <KpiCard
          label="Scores to Encode"
          icon="warning"
          value={kpis.toEncode}
          trend={kpis.toEncode > 0 ? "action needed" : "all set"}
          trendTone={kpis.toEncode > 0 ? "bad" : "good"}
          actionStrip={
            kpis.toEncode > 0
              ? { label: "Action Trigger", value: "Requires Encoding" }
              : undefined
          }
        />
        <KpiCard
          label="Grade Posting Rate"
          icon="fact_check"
          value={`${kpis.postingRate}%`}
          progress={kpis.postingRate}
          progressTone="bg-tertiary-container"
          scaleLabel={`${kpis.totalAssessments - kpis.toEncode} of ${kpis.totalAssessments}`}
        />
        <KpiCard
          label="Quarters Locked"
          icon="lock"
          value={kpis.locked.size}
          footnote="Locked by administrator"
        />
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-12 gap-space-xl">
        <div className="lg:col-span-7 flex flex-col bg-surface-container-lowest p-space-xl rounded-xl shadow-sm gap-space-lg">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-space-xs">
            <div>
              <h2 className="font-headline-md text-headline-md text-on-surface">Class Grade Status</h2>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Quarterly averages and completion per class
              </p>
            </div>
            <FilterPills
              options={[
                { value: "all", label: "All" },
                ...details.map((c) => ({ value: String(c.id), label: c.subject_name })),
              ]}
              value={classFilter}
              onChange={setClassFilter}
            />
          </div>
          {details
            .filter((c) => classFilter === "all" || String(c.id) === classFilter)
            .map((c) => (
              <div key={c.id} className="flex items-center gap-space-md py-space-sm border-b border-surface-container-high last:border-0">
                <div className="flex-1 min-w-0">
                  <p className="font-label-md text-label-md text-on-surface truncate">{c.subject_name}</p>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    {c.section_name} · {c.rows?.length || 0} learners
                  </p>
                </div>
                <span className="font-data-tabular-lg text-data-tabular-lg text-on-surface shrink-0">
                  {c.avg ?? "—"}
                </span>
                {(c.locked_quarters || []).includes(quarter) ? (
                  <TrendPill tone="bad" icon="lock">Q{quarter} locked</TrendPill>
                ) : c.complete ? (
                  <TrendPill tone="good" icon="check_circle">complete</TrendPill>
                ) : (
                  <TrendPill tone="info">in progress</TrendPill>
                )}
                <Btn variant="secondary" icon="table_chart" onClick={() => navigate(`/gradebook/${c.id}?quarter=${quarter}`)}>
                  Open
                </Btn>
              </div>
            ))}
          {details.length === 0 && (
            <p className="font-body-md text-body-md text-on-surface-variant py-space-lg text-center">
              No classes assigned yet — contact the administrator.
            </p>
          )}
        </div>

        <div className="lg:col-span-5 flex flex-col gap-space-xl">
          <div className="flex flex-col bg-surface-container-lowest p-space-xl rounded-xl shadow-sm">
            <div className="pb-space-xs">
              <h2 className="font-headline-md text-headline-md text-on-surface">Needs Your Attention</h2>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Assessments with unencoded scores in Quarter {quarter}
              </p>
            </div>
            {attention.length === 0 ? (
              <div className="py-space-lg text-center">
                <span className="material-symbols-outlined text-3xl text-tertiary">task_alt</span>
                <p className="font-body-md text-body-md text-on-surface mt-space-sm">
                  All scores encoded for Quarter {quarter}.
                </p>
              </div>
            ) : (
              attention.map((c) => (
                <div key={c.id} className="flex items-center gap-space-md py-space-sm border-b border-surface-container-high last:border-0">
                  <div className="flex-1 min-w-0">
                    <p className="font-label-md text-label-md text-on-surface truncate">{c.subject_name}</p>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">
                      {c.totalBlanks} blank scores · {c.pending} assessments
                    </p>
                  </div>
                  <Btn icon="edit_note" onClick={() => navigate(`/gradebook/${c.id}?quarter=${quarter}`)}>
                    Encode
                  </Btn>
                </div>
              ))
            )}
          </div>

          <div className="flex flex-col bg-primary-container text-on-primary p-space-xl rounded-xl shadow-sm">
            <h2 className="font-headline-md text-headline-md">Section at a Glance</h2>
            <p className="font-body-sm text-body-sm opacity-80 mb-space-md">
              Transmuted quarterly averages, all classes
            </p>
            {details.map((c) => (
              <div key={c.id} className="mb-space-md last:mb-0">
                <div className="flex items-center justify-between font-label-sm text-label-sm mb-space-2xs">
                  <span className="truncate">{c.subject_name}</span>
                  <span className="font-data-tabular-sm text-data-tabular-sm opacity-90">{c.avg ?? "—"}</span>
                </div>
                <div className="w-full bg-surface-container-lowest/20 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-surface-container-lowest h-full rounded-full"
                    style={{ width: `${c.avg ?? 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

function AdminDashboard() {
  const navigate = useNavigate();
  const [students, setStudents] = useState(null);
  const [teachers, setTeachers] = useState(null);
  const [subjects, setSubjects] = useState(null);
  const [sections, setSections] = useState(null);
  const [assignments, setAssignments] = useState(null);
  const [audit, setAudit] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      api("/admin/students/?page_size=1"),
      api("/admin/users/?role=teacher&page_size=1"),
      api("/admin/subjects/?page_size=1"),
      api("/admin/sections/?page_size=1"),
      api("/admin/assignments/?page_size=200"),
      api("/admin/audit-log/?page_size=6"),
    ])
      .then(([s, t, sub, sec, a, al]) => {
        setStudents(s.count);
        setTeachers(t.count);
        setSubjects(sub.count);
        setSections(sec.count);
        setAssignments(a.results || []);
        setAudit(al.results || []);
      })
      .catch(setError);
  }, []);

  if (error) {
    return (
      <Card className="p-space-xl">
        <p className="font-body-md text-body-md text-on-error-container">{error.message}</p>
      </Card>
    );
  }
  if (students === null) return null;

  const lockedCount = (assignments || []).reduce((n, a) => n + (a.locked_quarters?.length || 0), 0);

  return (
    <>
      <section className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md bg-surface-container-lowest p-space-xl rounded-xl shadow-sm">
        <div className="flex flex-col gap-space-2xs">
          <div className="flex items-center gap-space-xs text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider">
            <span className="inline-block w-2 h-2 rounded-full bg-primary" />
            Administration / Academic Records
          </div>
          <h1 className="font-headline-xl text-headline-xl text-on-surface tracking-tight">
            Administration Overview
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            {students} learners · {teachers} teachers · {sections} sections · {subjects} subjects
          </p>
        </div>
        <div className="flex items-center gap-space-sm flex-wrap">
          <Btn variant="secondary" icon="history" onClick={() => navigate("/audit-log")}>
            Audit Log
          </Btn>
          <Btn icon="person_add" onClick={() => navigate("/students")}>
            Manage Learners
          </Btn>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-space-lg">
        <KpiCard label="Enrolled Learners" icon="school" value={students} />
        <KpiCard label="Faculty" icon="co_present" value={teachers} />
        <KpiCard
          label="Subjects Offered"
          icon="menu_book"
          value={subjects}
          footnote={`${sections} sections`}
        />
        <KpiCard
          label="Quarters Locked"
          icon="lock"
          value={lockedCount}
          trend={lockedCount > 0 ? "finalized" : "none yet"}
          trendTone={lockedCount > 0 ? "info" : "good"}
        />
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-12 gap-space-xl">
        <div className="lg:col-span-7 flex flex-col bg-surface-container-lowest p-space-xl rounded-xl shadow-sm">
          <div className="pb-space-xs">
            <h2 className="font-headline-md text-headline-md text-on-surface">Classes & Quarter Locks</h2>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              One responsible teacher per subject and section
            </p>
          </div>
          {(assignments || []).map((a) => (
            <div key={a.id} className="flex items-center gap-space-md py-space-sm border-b border-surface-container-high last:border-0">
              <div className="flex-1 min-w-0">
                <p className="font-label-md text-label-md text-on-surface truncate">{a.subject_name}</p>
                <p className="font-body-sm text-body-sm text-on-surface-variant">
                  {a.section_name} · {a.teacher_name}
                </p>
              </div>
              <div className="flex gap-space-2xs">
                {[1, 2, 3, 4].map((q) => (
                  <TrendPill key={q} tone={a.locked_quarters?.includes(q) ? "bad" : "neutral"}>
                    Q{q}
                  </TrendPill>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="lg:col-span-5 flex flex-col bg-surface-container-lowest p-space-xl rounded-xl shadow-sm">
          <div className="flex items-center justify-between pb-space-xs">
            <div>
              <h2 className="font-headline-md text-headline-md text-on-surface">Recent Activity</h2>
              <p className="font-body-sm text-body-sm text-on-surface-variant">Latest audit log entries</p>
            </div>
            <Btn variant="secondary" icon="open_in_new" onClick={() => navigate("/audit-log")}>
              Open
            </Btn>
          </div>
          {(audit || []).map((e) => (
            <div key={e.id} className="py-space-sm border-b border-surface-container-high last:border-0">
              <div className="flex items-center justify-between gap-space-sm">
                <p className="font-label-md text-label-md text-on-surface truncate">{e.action}</p>
                <span className="font-label-sm text-label-sm text-on-surface-variant whitespace-nowrap">
                  {new Date(e.timestamp).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              <p className="font-body-sm text-body-sm text-on-surface-variant truncate">
                {e.actor} · {e.entity}
                {e.entity_id ? ` #${e.entity_id}` : ""}
              </p>
            </div>
          ))}
          {audit?.length === 0 && (
            <p className="font-body-md text-body-md text-on-surface-variant py-space-lg text-center">
              No activity recorded yet.
            </p>
          )}
        </div>
      </section>
    </>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  if (user?.role === "admin") return <AdminDashboard />;
  return <TeacherDashboard user={user} />;
}
