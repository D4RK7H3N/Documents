import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Btn, Card, Field, TrendPill, inputClass } from "../components/ui";

const QUARTERS = [1, 2, 3, 4];
const COMPONENT_META = {
  WW: { label: "Written Work", dot: "bg-primary" },
  PT: { label: "Performance Task", dot: "bg-tertiary-container" },
  QA: { label: "Quarterly Assessment", dot: "bg-error" },
};

function cellState(text, hps) {
  if (text === "" || text === undefined || text === null) return "blank";
  const num = Number(text);
  if (!Number.isFinite(num) || num < 0 || num > hps) return "invalid";
  return "ok";
}

function ScorePill({ value, state, hps, onChange, onKeyDown, onPaste, inputRef, disabled }) {
  const styles = {
    invalid: "bg-error-container text-on-error-container ring-1 ring-error",
    dirty: "bg-tertiary-fixed text-on-tertiary-fixed ring-1 ring-tertiary",
    blank: "bg-surface-container-low border border-dashed border-outline-variant/60 text-on-surface-variant/50",
    ok: "bg-surface-container-high text-on-surface",
  };
  return (
    <input
      ref={inputRef}
      value={value}
      disabled={disabled}
      inputMode="decimal"
      onChange={onChange}
      onKeyDown={onKeyDown}
      onPaste={onPaste}
      placeholder="—"
      title={`Max ${hps}`}
      className={`w-[72px] py-1 px-2 rounded-lg text-right font-data-tabular-sm text-data-tabular-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 ${styles[state]}`}
    />
  );
}

function AssessmentForm({ initial, onSubmit, onCancel, busy, error }) {
  const [form, setForm] = useState(initial || { component: "WW", title: "", highest_possible_score: "" });
  return (
    <Card className="p-space-lg">
      <h3 className="font-headline-sm text-headline-sm text-on-surface mb-space-md">
        {initial ? "Edit assessment" : "New assessment"}
      </h3>
      <form
        className="flex flex-wrap items-end gap-space-md"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit({ ...form, highest_possible_score: Number(form.highest_possible_score) });
        }}
      >
        <div className="w-48">
          <select
            className={inputClass}
            value={form.component}
            onChange={(e) => setForm({ ...form, component: e.target.value })}
          >
            {Object.entries(COMPONENT_META).map(([value, meta]) => (
              <option key={value} value={value}>
                {meta.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-[180px]">
          <input
            className={inputClass}
            placeholder="Assessment title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
        </div>
        <div className="w-32">
          <input
            className={inputClass}
            placeholder="HPS"
            inputMode="decimal"
            value={form.highest_possible_score}
            onChange={(e) => setForm({ ...form, highest_possible_score: e.target.value })}
            required
          />
        </div>
        <Btn type="submit" icon="check" disabled={busy}>
          {initial ? "Save" : "Add"}
        </Btn>
        <Btn type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Btn>
      </form>
      {error && <p className="mt-space-sm font-body-sm text-body-sm text-on-error-container">{error.message}</p>}
    </Card>
  );
}

export default function Gradebook() {
  const { classId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const quarter = Number(searchParams.get("quarter") || 1);

  const [classInfo, setClassInfo] = useState(null);
  const [grades, setGrades] = useState(null);
  const [assessments, setAssessments] = useState([]);
  const [scoreMaps, setScoreMaps] = useState({});
  const [values, setValues] = useState({});
  const [initial, setInitial] = useState({});
  const [rowFilter, setRowFilter] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [savedFlash, setSavedFlash] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [formBusy, setFormBusy] = useState(false);
  const [formError, setFormError] = useState(null);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [submitForm, setSubmitForm] = useState({ to_teacher_id: "", note: "" });
  const [teachers, setTeachers] = useState([]);
  const [submitBusy, setSubmitBusy] = useState(false);
  const [submitNotice, setSubmitNotice] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const refs = useRef({});

  const loadAll = useCallback(async () => {
    try {
      const [gradesData, assessmentsData] = await Promise.all([
        api(`/classes/${classId}/grades/?quarter=${quarter}`),
        api(`/classes/${classId}/assessments/?quarter=${quarter}`),
      ]);
      setGrades(gradesData);
      setClassInfo(gradesData.class);
      setAssessments(assessmentsData || []);
      const maps = {};
      await Promise.all(
        (assessmentsData || []).map(async (a) => {
          const data = await api(`/assessments/${a.id}/scores/`);
          maps[a.id] = data.students || [];
        })
      );
      setScoreMaps(maps);
      const v = {};
      const init = {};
      for (const a of assessmentsData || []) {
        for (const s of maps[a.id] || []) {
          const key = `${s.student_id}:${a.id}`;
          v[key] = s.raw === null || s.raw === undefined ? "" : String(s.raw);
          init[key] = v[key];
        }
      }
      setValues(v);
      setInitial(init);
      setSavedFlash(false);
      return true;
    } catch (err) {
      setLoadError(err);
      return false;
    }
  }, [classId, quarter]);

  useEffect(() => {
    setLoadError(null);
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (!submitOpen) return;
    api("/teachers/")
      .then((data) => setTeachers((data.results || data).filter((t) => t.id !== user?.id)))
      .catch(() => setTeachers([]));
  }, [submitOpen, user?.id]);

  async function submitForReview(e) {
    e.preventDefault();
    setSubmitBusy(true);
    setSaveError(null);
    try {
      const result = await api(`/classes/${classId}/submissions/`, {
        method: "POST",
        body: {
          quarter,
          to_teacher_id: Number(submitForm.to_teacher_id),
          note: submitForm.note,
        },
      });
      setSubmitNotice(`Submitted Quarter ${result.quarter} grades to ${result.submitted_to}.`);
      setSubmitOpen(false);
      setSubmitForm({ to_teacher_id: "", note: "" });
    } catch (err) {
      setSaveError(err);
    } finally {
      setSubmitBusy(false);
    }
  }

  const students = grades?.students || [];
  const filteredStudents = useMemo(() => {
    const q = rowFilter.trim().toLowerCase();
    if (!q) return students;
    return students.filter(
      (s) => s.full_name.toLowerCase().includes(q) || s.lrn.includes(q)
    );
  }, [students, rowFilter]);

  const isLocked = (classInfo?.locked_quarters || []).includes(quarter) && user?.role === "teacher";
  const lockedSet = useMemo(() => new Set(classInfo?.locked_quarters || []), [classInfo]);

  const dirtyKeys = useMemo(
    () => Object.keys(values).filter((k) => values[k] !== initial[k]),
    [values, initial]
  );
  const anyInvalid = Object.keys(values).some(
    (k) => {
      const assessment = assessments.find((a) => String(a.id) === k.split(":")[1]);
      return assessment && cellState(values[k], Number(assessment.highest_possible_score)) === "invalid";
    }
  );

  const gradeMap = useMemo(() => {
    const map = {};
    for (const r of students) map[r.student_id] = r;
    return map;
  }, [students]);

  useEffect(() => {
    if (dirtyKeys.length === 0) return;
    const handler = (e) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirtyKeys.length]);

  function setValue(key, text) {
    setValues((prev) => ({ ...prev, [key]: text }));
  }

  function focusCell(rowIndex, colIndex) {
    const row = filteredStudents[rowIndex];
    const col = assessments[colIndex];
    if (row && col) refs.current[`${row.student_id}:${col.id}`]?.focus();
  }

  function onKeyDown(e, rowIndex, colIndex) {
    const moves = {
      ArrowDown: [1, 0],
      Enter: [1, 0],
      ArrowUp: [-1, 0],
      ArrowRight: [0, 1],
      ArrowLeft: [0, -1],
    };
    const move = moves[e.key];
    if (move) {
      e.preventDefault();
      focusCell(rowIndex + move[0], colIndex + move[1]);
    }
  }

  function onPaste(e, rowIndex, colIndex) {
    const text = e.clipboardData.getData("text");
    if (!text) return;
    const lines = text.split(/\r?\n/).filter((l, i, arr) => l.trim() !== "" || i < arr.length - 1);
    if (lines.length <= 1) return;
    e.preventDefault();
    const col = assessments[colIndex];
    if (!col) return;
    setValues((prev) => {
      const next = { ...prev };
      lines.forEach((line, i) => {
        const row = filteredStudents[rowIndex + i];
        if (!row) return;
        const clean = line.trim().replace(/^"(.*)"$/, "$1");
        if (clean === "" || Number.isFinite(Number(clean))) next[`${row.student_id}:${col.id}`] = clean;
      });
      return next;
    });
  }

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      const byAssessment = {};
      for (const key of dirtyKeys) {
        const [sid, aid] = key.split(":");
        byAssessment[aid] = byAssessment[aid] || [];
        byAssessment[aid].push({ student_id: Number(sid), raw: values[key] === "" ? null : Number(values[key]) });
      }
      for (const [aid, entries] of Object.entries(byAssessment)) {
        const all = scoreMaps[aid] || [];
        const payload = all.length
          ? all.map((s) => {
              const changed = entries.find((e) => String(e.student_id) === String(s.student_id));
              return changed || { student_id: s.student_id, raw: s.raw ?? null };
            })
          : entries;
        await api(`/assessments/${aid}/scores/`, { method: "PUT", body: { scores: payload } });
      }
      await loadAll();
      setSavedFlash(true);
    } catch (err) {
      setSaveError(err);
    } finally {
      setSaving(false);
    }
  }

  async function createAssessment(payload) {
    setFormBusy(true);
    setFormError(null);
    try {
      await api(`/classes/${classId}/assessments/`, { method: "POST", body: { ...payload, quarter } });
      setFormOpen(false);
      await loadAll();
    } catch (err) {
      setFormError(err);
    } finally {
      setFormBusy(false);
    }
  }

  async function updateAssessment(id, payload) {
    setFormBusy(true);
    setFormError(null);
    try {
      await api(`/assessments/${id}/`, { method: "PATCH", body: payload });
      setEditing(null);
      await loadAll();
    } catch (err) {
      setFormError(err);
    } finally {
      setFormBusy(false);
    }
  }

  async function deleteAssessment(id, title) {
    if (!window.confirm(`Delete "${title}" and its scores? Grades will be recomputed.`)) return;
    try {
      await api(`/assessments/${id}/`, { method: "DELETE" });
      await loadAll();
    } catch (err) {
      alert(err.message);
    }
  }

  if (loadError) {
    return (
      <Card className="p-space-xl">
        <p className="font-body-md text-body-md text-on-error-container">{loadError.message}</p>
      </Card>
    );
  }
  if (!grades) return null;

  return (
    <div className="flex flex-col w-full gap-space-lg">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md bg-surface-container-lowest p-space-lg rounded-xl shadow-sm">
        <div className="flex flex-col gap-space-2xs">
          <div className="flex items-center gap-space-sm flex-wrap">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-primary bg-primary-fixed px-space-xs py-space-2xs rounded-lg font-semibold">
              Live Registry Matrix
            </span>
            <span className="inline-flex items-center gap-space-xs text-on-surface-variant font-label-md text-label-md">
              <span className="w-2 h-2 rounded-full bg-tertiary-fixed-dim inline-block" />
              Quarter {quarter} {lockedSet.has(quarter) ? "· 🔒 Locked" : ""} · {students.length} learners
            </span>
          </div>
          <div className="flex items-center gap-space-md mt-space-2xs flex-wrap">
            <div className="relative">
              <select
                className="appearance-none bg-surface-container-low text-on-surface font-headline-sm text-headline-sm font-bold pl-space-md pr-space-xl py-space-xs rounded-xl focus:outline-none cursor-pointer hover:bg-surface-container transition-colors"
                value={String(quarter)}
                onChange={(e) => setSearchParams({ quarter: e.target.value })}
              >
                {QUARTERS.map((q) => (
                  <option key={q} value={q}>
                    Quarter {q}
                    {lockedSet.has(q) ? " — Locked" : ""}
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
              Faculty Lead: <strong className="text-on-surface font-semibold ml-1">{classInfo?.subject}</strong>
            </span>
            <span className="flex items-center gap-space-xs hidden md:inline-flex">
              <span className="material-symbols-outlined text-sm text-on-surface-variant">balance</span>
              Weights: WW 25% · PT 45% · QA 30% <span className="text-on-surface-variant/60">(per Grading Config)</span>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-space-sm flex-wrap self-start lg:self-center">
          <div className="flex items-center bg-surface-container-low px-space-md py-space-xs rounded-xl text-on-surface-variant">
            <span className="material-symbols-outlined text-base mr-space-xs">search</span>
            <input
              value={rowFilter}
              onChange={(e) => setRowFilter(e.target.value)}
              className="bg-transparent w-36 font-body-sm text-body-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none"
              placeholder="Find learner…"
            />
          </div>
          <Btn
            variant="secondary"
            icon="summarize"
            onClick={() => navigate(`/classes/${classId}/report?semester=${quarter <= 2 ? 1 : 2}`)}
          >
            Class Report
          </Btn>
          {user?.role !== "student" && (
            <Btn
              variant="secondary"
              icon="note_add"
              onClick={() => {
                setFormOpen(true);
                setEditing(null);
              }}
            >
              Add Assessment
            </Btn>
          )}
          <Btn
            variant="secondary"
            icon="outgoing_mail"
            onClick={() => setSubmitOpen((v) => !v)}
          >
            Submit for review
          </Btn>
          <Btn icon="save" onClick={save} disabled={dirtyKeys.length === 0 || anyInvalid || saving || isLocked}>
            {saving ? "Saving…" : `Save${dirtyKeys.length ? ` (${dirtyKeys.length})` : ""}`}
          </Btn>
        </div>
      </div>

      {(formOpen || editing) && (
        <AssessmentForm
          initial={
            editing
              ? {
                  component: editing.component,
                  title: editing.title,
                  highest_possible_score: String(editing.highest_possible_score),
                }
              : null
          }
          busy={formBusy}
          error={formError}
          onCancel={() => {
            setFormOpen(false);
            setEditing(null);
          }}
          onSubmit={(payload) => (editing ? updateAssessment(editing.id, payload) : createAssessment(payload))}
        />
      )}

      {isLocked && (
        <div className="rounded-xl bg-error-container/30 text-on-error-container px-space-md py-space-sm font-label-md text-label-md flex items-center gap-space-xs">
          <span className="material-symbols-outlined text-base">lock</span>
          This quarter is locked — ask an administrator to unlock it to make changes.
        </div>
      )}
      {submitOpen && (
        <Card className="p-space-lg">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-space-sm">
            Submit Quarter {quarter} grades for review
          </h3>
          <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-md">
            A snapshot of the current quarterly grades is sent to the teacher you choose. They can approve
            it or return it with a note — find it under Submissions.
          </p>
          <form className="flex flex-wrap items-end gap-space-md" onSubmit={submitForReview}>
            <div className="w-56">
              <Field label="Send to teacher">
                <select
                  className={inputClass}
                  value={submitForm.to_teacher_id}
                  onChange={(e) => setSubmitForm({ ...submitForm, to_teacher_id: e.target.value })}
                  required
                >
                  <option value="">Select teacher…</option>
                  {teachers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.username}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <div className="flex-1 min-w-[200px]">
              <Field label="Note (optional)">
                <input
                  className={inputClass}
                  value={submitForm.note}
                  onChange={(e) => setSubmitForm({ ...submitForm, note: e.target.value })}
                  placeholder="e.g. Q1 grades ready for checking"
                />
              </Field>
            </div>
            <Btn type="submit" icon="send" disabled={submitBusy}>
              {submitBusy ? "Submitting…" : "Send"}
            </Btn>
            <Btn type="button" variant="ghost" onClick={() => setSubmitOpen(false)}>
              Cancel
            </Btn>
          </form>
        </Card>
      )}

      {saveError && (
        <div className="rounded-xl bg-error-container text-on-error-container px-space-md py-space-sm text-body-sm">
          {saveError.message}
        </div>
      )}
      {!saveError && savedFlash && dirtyKeys.length === 0 && (
        <div className="rounded-xl bg-tertiary-fixed/30 border border-tertiary-container/40 text-[#005336] px-space-md py-space-sm text-body-sm flex items-center gap-space-xs">
          <span className="material-symbols-outlined text-base">check_circle</span>
          Scores saved — quarterly grades recomputed and visible to learners.
        </div>
      )}
      {submitNotice && (
        <div className="rounded-xl bg-tertiary-fixed/30 border border-tertiary-container/40 text-[#005336] px-space-md py-space-sm text-body-sm flex items-center gap-space-xs">
          <span className="material-symbols-outlined text-base">outgoing_mail</span>
          {submitNotice}
        </div>
      )}

      <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-xl shadow-[0_1px_2px_rgba(23,35,45,0.04)] overflow-hidden">
        <p className="flex items-center gap-space-xs border-b border-outline-variant/70 px-space-md py-space-sm font-label-sm text-label-sm text-on-surface-variant md:hidden">
          <span className="material-symbols-outlined text-base">swipe</span>
          Swipe horizontally to review all assessment columns.
        </p>
        <div className="overflow-x-auto max-h-[60vh]">
          <table className="w-full text-left border-collapse select-none font-data-tabular-md text-data-tabular-md">
            <thead className="bg-surface-container-low sticky top-0 z-30">
              <tr className="text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider">
                <th className="py-3 px-4 min-w-[220px] sticky left-0 z-40 bg-surface-container-low shadow-[2px_0_4px_rgba(0,0,0,0.03)]">
                  <div className="flex items-center justify-between">
                    <span>Student Record</span>
                  </div>
                </th>
                <th className="py-3 px-4 min-w-[140px] text-right bg-secondary-container/40">
                  <div className="flex items-center justify-end gap-1">
                    <span className="text-primary font-bold">Quarterly Grade</span>
                  </div>
                </th>
                {assessments.map((a) => (
                  <th key={a.id} className="py-3 px-3 min-w-[130px] text-right group/header">
                    <div className="flex flex-col items-end">
                      <div className="flex items-center gap-1">
                        <span className={`w-1.5 h-1.5 rounded-full ${COMPONENT_META[a.component]?.dot || "bg-primary"}`} />
                        <span className="text-on-surface font-semibold normal-case">{a.title}</span>
                      </div>
                      <span className="text-on-surface-variant font-data-tabular-sm text-data-tabular-sm normal-case">
                        {COMPONENT_META[a.component]?.label} · Max {a.highest_possible_score}
                      </span>
                    </div>
                    {!isLocked && (
                      <div className="hidden group-hover/header:flex max-md:flex items-center justify-end gap-1 mt-1">
                        <button
                          title="Edit assessment"
                          onClick={() => {
                            setEditing(a);
                            setFormOpen(false);
                          }}
                          className="p-0.5 rounded hover:bg-surface-container-high max-md:flex max-md:h-11 max-md:w-11 max-md:items-center max-md:justify-center"
                        >
                          <span className="material-symbols-outlined text-xs text-on-surface-variant">edit</span>
                        </button>
                        <button
                          title="Delete assessment"
                          onClick={() => deleteAssessment(a.id, a.title)}
                          className="p-0.5 rounded hover:bg-error-container max-md:flex max-md:h-11 max-md:w-11 max-md:items-center max-md:justify-center"
                        >
                          <span className="material-symbols-outlined text-xs text-error">delete</span>
                        </button>
                      </div>
                    )}
                  </th>
                ))}
                {assessments.length === 0 && (
                  <th className="py-3 px-4 text-right">No assessments yet</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-low">
              {filteredStudents.map((s, rowIndex) => {
                const g = gradeMap[s.student_id];
                return (
                  <tr key={s.student_id} className="hover:bg-surface-container-low/70 transition-colors group">
                    <td className="p-3 sticky left-0 z-20 bg-surface-container-lowest group-hover:bg-surface-container-low/70 shadow-[2px_0_4px_rgba(0,0,0,0.03)]">
                      <div className="flex items-center gap-space-sm">
                        <div className="w-8 h-8 rounded-full bg-primary-container/15 text-primary flex items-center justify-center font-label-md font-semibold shrink-0">
                          {s.full_name.split(" ").map((w) => w[0]).slice(0, 2).join("")}
                        </div>
                        <div className="flex flex-col">
                          <span className="font-headline-sm text-headline-sm font-semibold text-on-surface">
                            {s.full_name}
                          </span>
                          <span className="font-data-tabular-sm text-data-tabular-sm text-on-surface-variant">
                            {s.lrn}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-right bg-secondary-container/20">
                      {g?.grade !== null && g?.grade !== undefined ? (
                        <span className="inline-flex items-center font-bold text-tertiary-container bg-surface-container-high px-2 py-0.5 rounded-full text-data-tabular-sm">
                          {g.grade}
                        </span>
                      ) : (
                        <span className="text-on-surface-variant/50">—</span>
                      )}
                    </td>
                    {assessments.map((a, colIndex) => {
                      const key = `${s.student_id}:${a.id}`;
                      const state = cellState(values[key], Number(a.highest_possible_score));
                      const isDirty = values[key] !== initial[key];
                      const shown = isDirty && state !== "invalid" ? "dirty" : state;
                      const colBlanks = (scoreMaps[a.id] || []).filter(
                        (r) => r.raw === null || r.raw === undefined
                      ).length;
                      return (
                        <td key={a.id} className="p-1.5 text-right" title={colBlanks ? `${colBlanks} blank` : ""}>
                          <ScorePill
                            inputRef={(el) => (refs.current[key] = el)}
                            value={values[key] ?? ""}
                            state={shown}
                            hps={a.highest_possible_score}
                            disabled={isLocked}
                            onChange={(e) => setValue(key, e.target.value)}
                            onKeyDown={(e) => onKeyDown(e, rowIndex, colIndex)}
                            onPaste={(e) => onPaste(e, rowIndex, colIndex)}
                          />
                        </td>
                      );
                    })}
                    {assessments.length === 0 && <td className="p-3 text-right text-on-surface-variant">—</td>}
                  </tr>
                );
              })}
              {filteredStudents.length === 0 && (
                <tr>
                  <td colSpan={assessments.length + 2} className="p-space-xl text-center font-body-md text-body-md text-on-surface-variant">
                    No learners match “{rowFilter}”.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="px-space-md py-space-xs font-label-sm text-label-sm text-on-surface-variant border-t border-surface-container-high">
          ↑ ↓ ← → or Enter to move · paste a spreadsheet column into any cell · blank = not yet encoded ·
          {dirtyKeys.length > 0 ? ` ${dirtyKeys.length} unsaved change${dirtyKeys.length > 1 ? "s" : ""}` : " all changes saved"}
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-sm p-space-xl">
        <div className="pb-space-xs">
          <h2 className="font-headline-md text-headline-md text-on-surface">Quarterly Grades — Computed</h2>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Produced by the grade engine · learners see these immediately after you save
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-space-md">
          {students.map((s) => (
            <div key={s.student_id} className="flex items-center gap-space-md bg-surface-container-low rounded-xl px-space-md py-space-sm">
              <div className="flex-1 min-w-0">
                <p className="font-label-md text-label-md text-on-surface truncate">{s.full_name}</p>
                <p className="font-body-sm text-body-sm text-on-surface-variant">
                  Initial {s.initial_grade ?? "—"} · {s.blanks > 0 ? `${s.blanks} blank score${s.blanks > 1 ? "s" : ""}` : "complete"}
                </p>
              </div>
              {s.grade !== null ? (
                <TrendPill tone="good" icon="workspace_premium">{s.grade}</TrendPill>
              ) : (
                <TrendPill tone="neutral">pending</TrendPill>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
