import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import {
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  PageHeader,
  SectionCard,
  Spinner,
  TrendPill,
  inputClass,
  useToast,
} from "../components/ui";

function useList(path, query = "") {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const load = useCallback(async () => {
    try {
      setData(await api(`${path}${query}`));
    } catch (err) {
      setError(err);
    }
  }, [path, query]);
  useEffect(() => {
    load();
  }, [load]);
  return { data, error, reload: load };
}

function CreateForm({ fields, onSubmit, submitLabel = "Add" }) {
  const [values, setValues] = useState(() => Object.fromEntries(fields.map((f) => [f.name, f.default ?? ""])));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  return (
    <form
      className="flex flex-wrap items-end gap-space-md border-b border-surface-container-high pb-space-lg mb-space-md"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
          const payload = {};
          for (const f of fields) payload[f.name] = f.number ? Number(values[f.name]) : values[f.name];
          await onSubmit(payload);
          setValues(Object.fromEntries(fields.map((f) => [f.name, f.default ?? ""])));
        } catch (err) {
          setError(err);
        } finally {
          setBusy(false);
        }
      }}
    >
      {fields.map((f) => (
        <div key={f.name} className={f.wide ? "w-52" : "w-40"}>
          <Field label={f.label}>
            {f.options ? (
              <select
                className={inputClass}
                value={values[f.name]}
                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
                required
              >
                <option value="">Select…</option>
                {f.options.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                className={inputClass}
                value={values[f.name]}
                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
                required
              />
            )}
          </Field>
        </div>
      ))}
      <Btn type="submit" icon="add" disabled={busy}>
        {busy ? "Saving…" : submitLabel}
      </Btn>
      {error && <p className="w-full font-body-sm text-body-sm text-on-error-container">{error.message}</p>}
    </form>
  );
}

function DataTable({ headers, rows, empty }) {
  if (rows.length === 0) return <EmptyState icon="inventory_2" title={empty} />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b-2 border-surface-container-high">
            {headers.map((h) => (
              <th key={h} className="py-space-sm pr-space-md font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">
                {h}
              </th>
            ))}
            <th />
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  );
}

const DEPED_PRESETS = {
  core: { WW: "25", PT: "50", QA: "25" },
  applied: { WW: "25", PT: "45", "QA": "30" },
  specialized: { WW: "20", PT: "60", QA: "20" },
};

function SubjectWeightsEditor({ subject, onSaved, onClose }) {
  const [weights, setWeights] = useState(
    subject.weights_override || { WW: "", PT: "", QA: "" }
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const total = ["WW", "PT", "QA"].reduce((sum, k) => sum + (Number(weights[k]) || 0), 0);

  return (
    <div className="bg-surface-container-low rounded-xl p-space-md mt-space-xs">
      <div className="flex items-center justify-between mb-space-sm">
        <p className="font-label-md text-label-md text-on-surface">
          Weights for <b>{subject.name}</b>
          <span className="text-on-surface-variant"> · overrides the {subject.subject_type} default</span>
        </p>
        <div className="flex items-center gap-space-sm">
          <button
            type="button"
            className="font-label-md text-label-md text-primary hover:underline"
            onClick={() => setWeights(DEPED_PRESETS[subject.subject_type] || { WW: "", PT: "", QA: "" })}
          >
            Use DepEd {subject.subject_type} preset
          </button>
          <button
            type="button"
            className="font-label-md text-label-md text-on-surface-variant hover:underline"
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                await api(`/admin/subjects/${subject.id}/`, { method: "PATCH", body: { weights_override: null } });
                onSaved(null);
                onClose();
              } catch (err) {
                setError(err);
                setBusy(false);
              }
            }}
          >
            Clear override
          </button>
        </div>
      </div>
      <div className="flex flex-wrap items-end gap-space-md">
        {["WW", "PT", "QA"].map((k) => (
          <div key={k} className="w-24">
            <Field label={k}>
              <input
                className={inputClass}
                value={weights[k]}
                inputMode="decimal"
                onChange={(e) => setWeights({ ...weights, [k]: e.target.value })}
              />
            </Field>
          </div>
        ))}
        <TrendPill tone={total === 100 ? "good" : "bad"}>{total}% total</TrendPill>
        <Btn
          icon="check"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              const result = await api(`/admin/subjects/${subject.id}/`, {
                method: "PATCH",
                body: { weights_override: weights },
              });
              onSaved(result.weights_override);
              onClose();
            } catch (err) {
              setError(err);
            } finally {
              setBusy(false);
            }
          }}
        >
          Save weights
        </Btn>
        <Btn variant="ghost" onClick={onClose}>
          Cancel
        </Btn>
      </div>
      {error && <p className="mt-space-sm font-body-sm text-body-sm text-on-error-container">{error.message}</p>}
      <p className="mt-space-xs font-label-sm text-label-sm text-on-surface-variant">
        Saving recomputes this subject's grades on the next score save or config change.
      </p>
    </div>
  );
}

function SubjectsTab() {
  const { data, error, reload } = useList("/admin/subjects/?page_size=200");
  const [editingId, setEditingId] = useState(null);
  const rows = data?.results || [];
  return (
    <SectionCard title="Subjects" sub="The subject type sets the DepEd weight preset — configure per-subject overrides below.">
      <CreateForm
        fields={[
          { name: "name", label: "Subject name", wide: true },
          {
            name: "subject_type",
            label: "Type",
            options: [["core", "Core"], ["applied", "Applied"], ["specialized", "Specialized"]],
          },
        ]}
        onSubmit={async (payload) => {
          await api("/admin/subjects/", { method: "POST", body: payload });
          reload();
        }}
      />
      {error && <ErrorBanner error={error} />}
      <DataTable
        headers={["Name", "Type", "Weights"]}
        empty="No subjects yet"
        rows={rows.flatMap((s) => [
          <tr key={s.id} className="border-b border-surface-container-high/60">
            <td className="py-space-2xs pr-space-md font-body-md text-body-md text-on-surface">{s.name}</td>
            <td className="py-space-2xs pr-space-md">
              <TrendPill tone="info">{s.subject_type}</TrendPill>
            </td>
            <td className="py-space-2xs pr-space-md">
              {s.weights_override ? (
                <TrendPill tone="warn">
                  WW {s.weights_override.WW} · PT {s.weights_override.PT} · QA {s.weights_override.QA}
                </TrendPill>
              ) : (
                <TrendPill tone="neutral">
                  {(DEPED_PRESETS[s.subject_type] && `${DEPED_PRESETS[s.subject_type].WW}/${DEPED_PRESETS[s.subject_type].PT}/${DEPED_PRESETS[s.subject_type].QA}`) || "type default"}
                </TrendPill>
              )}
            </td>
            <td className="py-space-2xs text-right whitespace-nowrap">
              <button
                className="font-label-md text-label-md text-primary hover:underline mr-space-md"
                onClick={() => setEditingId(editingId === s.id ? null : s.id)}
              >
                Configure
              </button>
              <button
                className="font-label-md text-label-md text-error hover:underline"
                onClick={async () => {
                  if (!window.confirm(`Delete ${s.name}?`)) return;
                  try {
                    await api(`/admin/subjects/${s.id}/`, { method: "DELETE" });
                    reload();
                  } catch (err) {
                    alert(err.message);
                  }
                }}
              >
                Delete
              </button>
            </td>
          </tr>,
          editingId === s.id && (
            <tr key={`${s.id}-editor`} className="border-b border-surface-container-high/60">
              <td colSpan={4} className="py-space-xs pr-space-md">
                <SubjectWeightsEditor
                  subject={s}
                  onSaved={() => reload()}
                  onClose={() => setEditingId(null)}
                />
              </td>
            </tr>
          ),
        ])}
      />
    </SectionCard>
  );
}

function SectionsTab() {
  const { data, error, reload } = useList("/admin/sections/?page_size=200");
  const rows = data?.results || [];
  return (
    <SectionCard title="Sections" sub="Grade-level (SHS) learner groupings per school year.">
      <CreateForm
        fields={[
          { name: "name", label: "Section name", wide: true },
          {
            name: "grade_level",
            label: "Grade level",
            options: [["Grade 11", "Grade 11"], ["Grade 12", "Grade 12"]],
            default: "Grade 12",
          },
          { name: "school_year", label: "School year", default: "2026-2027" },
        ]}
        onSubmit={async (payload) => {
          await api("/admin/sections/", { method: "POST", body: payload });
          reload();
        }}
      />
      {error && <ErrorBanner error={error} />}
      <DataTable
        headers={["Name", "Grade level", "School year"]}
        empty="No sections yet"
        rows={rows.map((s) => (
          <tr key={s.id} className="border-b border-surface-container-high/60">
            <td className="py-space-2xs pr-space-md font-body-md text-body-md text-on-surface">{s.name}</td>
            <td className="py-space-2xs pr-space-md">
              <TrendPill tone="info">{s.grade_level}</TrendPill>
            </td>
            <td className="py-space-2xs pr-space-md font-body-sm text-body-sm text-on-surface-variant">{s.school_year}</td>
            <td className="py-space-2xs text-right">
              <button
                className="font-label-md text-label-md text-error hover:underline"
                onClick={async () => {
                  if (!window.confirm(`Delete section ${s.name}?`)) return;
                  try {
                    await api(`/admin/sections/${s.id}/`, { method: "DELETE" });
                    reload();
                  } catch (err) {
                    alert(err.message);
                  }
                }}
              >
                Delete
              </button>
            </td>
          </tr>
        ))}
      />
    </SectionCard>
  );
}

function AssignmentsTab() {
  const assignments = useList("/admin/assignments/?page_size=200");
  const subjects = useList("/admin/subjects/?page_size=200");
  const sections = useList("/admin/sections/?page_size=200");
  const teachers = useList("/admin/users/?role=teacher&page_size=200");
  const rows = assignments.data?.results || [];

  async function toggleLock(id, quarter, locked) {
    try {
      await api(`/admin/classes/${id}/quarters/${quarter}/lock/`, { method: locked ? "POST" : "DELETE" });
      toast.success(`Quarter ${quarter} ${locked ? "locked" : "unlocked"} — teachers can no longer edit it.` );
      assignments.reload();
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <SectionCard title="Class assignments" sub="One responsible teacher per subject and section. Lock a quarter once grades are finalized.">
      <CreateForm
        fields={[
          { name: "subject", label: "Subject", options: (subjects.data?.results || []).map((s) => [s.id, s.name]), number: true },
          { name: "section", label: "Section", options: (sections.data?.results || []).map((s) => [s.id, `${s.name} (${s.school_year})`]), number: true },
          { name: "teacher", label: "Teacher", options: (teachers.data?.results || []).map((t) => [t.id, t.username]), number: true },
          { name: "school_year", label: "School year", default: "2026-2027" },
        ]}
        submitLabel="Assign"
        onSubmit={async (payload) => {
          await api("/admin/assignments/", { method: "POST", body: payload });
          assignments.reload();
        }}
      />
      {assignments.error && <ErrorBanner error={assignments.error} />}
      <DataTable
        headers={["Subject", "Section", "Teacher", "Quarter locks"]}
        empty="No assignments yet"
        rows={rows.map((a) => (
          <tr key={a.id} className="border-b border-surface-container-high/60">
            <td className="py-space-2xs pr-space-md font-body-md text-body-md text-on-surface">{a.subject_name}</td>
            <td className="py-space-2xs pr-space-md font-body-sm text-body-sm text-on-surface-variant">{a.section_name}</td>
            <td className="py-space-2xs pr-space-md font-body-sm text-body-sm text-on-surface-variant">{a.teacher_name}</td>
            <td className="py-space-2xs pr-space-md">
              <div className="flex gap-space-2xs">
                {[1, 2, 3, 4].map((q) => {
                  const locked = a.locked_quarters?.includes(q);
                  return (
                    <button
                      key={q}
                      onClick={() => toggleLock(a.id, q, !locked)}
                      className={`px-space-sm py-space-2xs rounded-lg font-label-sm text-label-sm font-semibold transition-colors ${
                        locked
                          ? "bg-error-container text-on-error-container hover:opacity-80"
                          : "bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest"
                      }`}
                    >
                      Q{q}
                    </button>
                  );
                })}
              </div>
            </td>
            <td className="py-space-2xs text-right">
              <button
                className="font-label-md text-label-md text-error hover:underline"
                onClick={async () => {
                  if (!window.confirm("Delete this assignment?")) return;
                  try {
                    await api(`/admin/assignments/${a.id}/`, { method: "DELETE" });
                    assignments.reload();
                  } catch (err) {
                    alert(err.message);
                  }
                }}
              >
                Delete
              </button>
            </td>
          </tr>
        ))}
      />
    </SectionCard>
  );
}

const TABS = [
  ["subjects", "Subjects", SubjectsTab],
  ["sections", "Sections", SectionsTab],
  ["assignments", "Assignments", AssignmentsTab],
];

export default function Academics() {
  const toast = useToast();
  const [tab, setTab] = useState("subjects");
  const Active = TABS.find(([key]) => key === tab)[2];
  return (
    <>
      <PageHeader
        eyebrow="Manage"
        title="Academics"
        sub="Subjects, sections and the teachers assigned to each class."
      />
      <div className="flex items-center gap-space-2xs bg-surface-container-low p-space-2xs rounded-xl w-fit">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-space-lg py-space-xs rounded-lg font-label-md text-label-md transition-colors ${
              tab === key
                ? "bg-surface-container-lowest text-on-surface shadow-sm font-semibold"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <Active />
    </>
  );
}
