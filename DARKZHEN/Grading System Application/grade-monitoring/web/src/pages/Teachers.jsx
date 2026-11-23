import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import {
  Btn,
  EmptyState,
  ErrorBanner,
  Field,
  PageHeader,
  SectionCard,
  Spinner,
  TempPasswordModal,
  TrendPill,
  inputClass,
  useToast,
} from "../components/ui";

function AssignClassForm({ teacher, subjects, sections, onDone, onCancel }) {
  const [form, setForm] = useState({ subject: "", section: "", school_year: "2026-2027" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  return (
    <form
      className="flex flex-wrap items-end gap-space-md bg-surface-container-low rounded-xl p-space-md mt-space-xs"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
          await api("/admin/assignments/", {
            method: "POST",
            body: {
              subject: Number(form.subject),
              section: Number(form.section),
              teacher: teacher.id,
              school_year: form.school_year,
            },
          });
          onDone();
        } catch (err) {
          setError(err);
        } finally {
          setBusy(false);
        }
      }}
    >
      <div className="w-48">
        <Field label="Subject">
          <select
            className={inputClass}
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
            required
          >
            <option value="">Select…</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="w-52">
        <Field label="Section">
          <select
            className={inputClass}
            value={form.section}
            onChange={(e) => setForm({ ...form, section: e.target.value })}
            required
          >
            <option value="">Select…</option>
            {sections.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.grade_level})
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="w-36">
        <Field label="School year">
          <input
            className={inputClass}
            value={form.school_year}
            onChange={(e) => setForm({ ...form, school_year: e.target.value })}
            required
          />
        </Field>
      </div>
      <Btn type="submit" icon="link" disabled={busy}>
        {busy ? "Assigning…" : "Assign"}
      </Btn>
      <Btn type="button" variant="ghost" onClick={onCancel}>
        Cancel
      </Btn>
      {error && <p className="w-full font-body-sm text-body-sm text-on-error-container">{error.message}</p>}
    </form>
  );
}

export default function Teachers() {
  const toast = useToast();
  const [teachers, setTeachers] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [sections, setSections] = useState([]);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ username: "", role: "teacher", last_name: "", first_name: "" });
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [assigningId, setAssigningId] = useState(null);
  const [passwordModal, setPasswordModal] = useState(null);
  const [setPwId, setSetPwId] = useState(null);
  const [pwForm, setPwForm] = useState("");

  const load = useCallback(async () => {
    try {
      const [t, sub, sec] = await Promise.all([
        api("/admin/teachers/"),
        api("/admin/subjects/?page_size=200"),
        api("/admin/sections/?page_size=200"),
      ]);
      setTeachers(t);
      setSubjects(sub.results || sub);
      setSections(sec.results || sec);
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function createTeacher(e) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const result = await api("/admin/users/create/", {
        method: "POST",
        body: {
          username: form.username.trim(),
          role: form.role,
          last_name: form.last_name.trim(),
          first_name: form.first_name.trim(),
        },
      });
      setPasswordModal({
        title: "Account created",
        name: result.display_name,
        username: result.username,
        role: result.role,
        password: result.temporary_password,
      });
      setForm({ username: "", role: form.role, last_name: "", first_name: "" });
      load();
    } catch (err) {
      setError(err);
    } finally {
      setCreating(false);
    }
  }

  async function resetPassword(displayName, id) {
    if (!window.confirm(`Issue a new temporary password for ${displayName}?`)) return;
    try {
      const result = await api(`/admin/users/${id}/reset-password/`, { method: "POST", body: {} });
      setPasswordModal({
        title: "Password reset",
        name: displayName,
        username: displayName,
        role: "account",
        password: result.temporary_password,
      });
    } catch (err) {
      setError(err);
    }
  }

  async function setStatus(teacher, isActive) {
    try {
      await api(`/admin/users/${teacher.id}/status/`, { method: "POST", body: { is_active: isActive } });
      toast.success(`${teacher.username} ${isActive ? "activated" : "deactivated"}.`);
      load();
    } catch (err) {
      setError(err);
    }
  }

  async function setPassword(teacher) {
    setBusy(true);
    setError(null);
    try {
      const result = await api(`/admin/users/${teacher.id}/set-password/`, {
        method: "POST",
        body: { password: pwForm },
      });
      toast.success(result.detail);
      setSetPwId(null);
      setPwForm("");
      load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function unassign(assignment, teacherUsername) {
    if (!window.confirm(`Remove ${assignment.subject} — ${assignment.section} from ${teacherUsername}?`)) return;
    try {
      await api(`/admin/assignments/${assignment.id}/`, { method: "DELETE" });
      load();
    } catch (err) {
      alert(err.message);
    }
  }

  if (!teachers) return error ? <ErrorBanner error={error} /> : <Spinner />;

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Teacher Configuration"
        sub="Create teacher accounts, assign their classes, and manage their access."
      />
      {error && <div className="mb-space-sm"><ErrorBanner error={error} /></div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg items-start">
        <SectionCard title="Add an account" sub="Names are recorded lastname-first, as in the class record. A temporary password is issued and must be changed at first login.">
          <form onSubmit={createTeacher} className="flex flex-col gap-space-md">
            <div className="grid grid-cols-2 gap-space-md">
              <Field label="Last name">
                <input
                  className={inputClass}
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  required
                />
              </Field>
              <Field label="First name">
                <input
                  className={inputClass}
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  required
                />
              </Field>
            </div>
            <Field label="Username">
              <input
                className={inputClass}
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                minLength={3}
                required
              />
            </Field>
            <Field label="Role">
              <select
                className={inputClass}
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
              >
                <option value="teacher">Teacher</option>
                <option value="admin">Administrator</option>
              </select>
            </Field>
            <Btn type="submit" icon="person_add" className="justify-center" disabled={creating}>
              {creating ? "Creating…" : "Create account"}
            </Btn>
          </form>
        </SectionCard>

        <SectionCard
          className="lg:col-span-2"
          title="Teachers"
          sub={`${teachers.length} teacher account${teachers.length === 1 ? "" : "s"}`}
        >
          {teachers.length === 0 ? (
            <EmptyState icon="co_present" title="No teachers yet" sub="Create the first account on the left." />
          ) : (
            <div className="flex flex-col gap-space-md">
              {teachers.map((t) => (
                <div key={t.id} className="bg-surface-container-low rounded-xl p-space-md">
                  <div className="flex flex-wrap items-center gap-space-md">
                    <div className="w-9 h-9 rounded-full bg-primary-container text-on-primary flex items-center justify-center font-label-md font-semibold shrink-0">
                      {t.username.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="font-label-md text-label-md text-on-surface">{t.display_name}</p>
                      <p className="font-data-tabular-sm text-data-tabular-sm text-on-surface-variant">{t.username}</p>
                      <div className="flex items-center gap-space-2xs mt-space-2xs flex-wrap">
                        {t.is_active ? (
                          <TrendPill tone="good" icon="check_circle">active</TrendPill>
                        ) : (
                          <TrendPill tone="bad" icon="block">deactivated</TrendPill>
                        )}
                        {t.must_change_password && <TrendPill tone="warn" icon="lock_reset">password change pending</TrendPill>}
                        <TrendPill tone="info">
                          {t.assignments.length} class{t.assignments.length === 1 ? "" : "es"}
                        </TrendPill>
                      </div>
                    </div>
                    <div className="ml-auto flex items-center gap-space-xs flex-wrap">
                      <Btn variant="secondary" icon="key" onClick={() => resetPassword(t.display_name, t.id)}>
                        Reset
                      </Btn>
                      {t.is_active ? (
                        <Btn variant="ghost" icon="block" onClick={() => setStatus(t, false)}>
                          Deactivate
                        </Btn>
                      ) : (
                        <Btn variant="ghost" icon="check_circle" onClick={() => setStatus(t, true)}>
                          Activate
                        </Btn>
                      )}
                      <Btn
                        variant="secondary"
                        icon="vpn_key"
                        onClick={() => {
                          setSetPwId(setPwId === t.id ? null : t.id);
                          setPwForm("");
                        }}
                      >
                        Set password
                      </Btn>
                      <Btn
                        variant="secondary"
                        icon="add_link"
                        onClick={() => setAssigningId(assigningId === t.id ? null : t.id)}
                      >
                        Assign class
                      </Btn>
                    </div>
                  </div>

                  {t.assignments.length > 0 && (
                    <div className="flex flex-wrap gap-space-2xs mt-space-sm">
                      {t.assignments.map((a) => (
                        <span
                          key={a.id}
                          className="inline-flex items-center gap-space-2xs bg-surface-container-high text-on-surface font-label-sm text-label-sm px-space-sm py-space-2xs rounded-full"
                        >
                          {a.subject} · {a.section} ({a.grade_level})
                          <button
                            title="Unassign"
                            onClick={() => unassign(a, t.username)}
                            className="text-error hover:text-on-error-container"
                          >
                            <span className="material-symbols-outlined text-xs">close</span>
                          </button>
                        </span>
                      ))}
                    </div>
                  )}

                  {setPwId === t.id && (
                    <form
                      className="flex flex-wrap items-end gap-space-md bg-surface-container-low rounded-xl p-space-md mt-space-sm"
                      onSubmit={(e) => {
                        e.preventDefault();
                        setPassword(t);
                      }}
                    >
                      <div className="flex-1 min-w-[220px]">
                        <Field
                          label={`New password for ${t.display_name}`}
                          hint="Min 8 characters, not similar to the username, not a common password."
                        >
                          <input
                            className={inputClass}
                            type="text"
                            value={pwForm}
                            onChange={(e) => setPwForm(e.target.value)}
                            autoComplete="new-password"
                            required
                          />
                        </Field>
                      </div>
                      <Btn type="submit" icon="vpn_key" disabled={busy}>
                        Save password
                      </Btn>
                      <Btn type="button" variant="ghost" onClick={() => setSetPwId(null)}>
                        Cancel
                      </Btn>
                    </form>
                  )}

                  {assigningId === t.id && (
                    <AssignClassForm
                      teacher={t}
                      subjects={subjects}
                      sections={sections}
                      onDone={() => {
                        setAssigningId(null);
                        load();
                      }}
                      onCancel={() => setAssigningId(null)}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      <TempPasswordModal
        open={Boolean(passwordModal)}
        title={passwordModal?.title}
        username={passwordModal?.name}
        role={passwordModal?.role}
        password={passwordModal?.password}
        onClose={() => setPasswordModal(null)}
      />
    </>
  );
}
