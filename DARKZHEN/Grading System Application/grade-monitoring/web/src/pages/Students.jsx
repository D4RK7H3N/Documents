import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import {
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  NoticeBanner,
  PageHeader,
  SectionCard,
  Spinner,
  TempPasswordModal,
  TrendPill,
  inputClass,
  useToast,
} from "../components/ui";

export default function Students() {
  const toast = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [sections, setSections] = useState([]);
  const [form, setForm] = useState({ lrn: "", full_name: "", section: "" });
  const [creating, setCreating] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [page, setPage] = useState(1);
  const [rowFilter, setRowFilter] = useState(searchParams.get("q") || "");
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ full_name: "", section: "" });
  const [editBusy, setEditBusy] = useState(false);
  const [pwStudentId, setPwStudentId] = useState(null);
  const [pwValue, setPwValue] = useState("");
  const [pwBusy, setPwBusy] = useState(false);
  const [passwordModal, setPasswordModal] = useState(null);
  const fileRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const [list, secs] = await Promise.all([
        api(`/admin/students/?page=${page}`),
        api("/admin/sections/?page_size=200"),
      ]);
      setData(list);
      setSections(secs.results || secs);
    } catch (err) {
      setError(err);
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  async function createStudent(e) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const result = await api("/admin/students/", {
        method: "POST",
        body: { lrn: form.lrn.trim(), full_name: form.full_name.trim(), section: Number(form.section) },
      });
      setPasswordModal({
        title: "Learner created",
        name: result.full_name,
        username: result.lrn,
        role: "student",
        password: result.temporary_password,
      });
      setForm({ lrn: "", full_name: "", section: "" });
      load();
    } catch (err) {
      setError(err);
    } finally {
      setCreating(false);
    }
  }

  async function importCsv(file) {
    setError(null);
    setImportResult(null);
    const body = new FormData();
    body.append("file", file, file.name);
    const access = localStorage.getItem("access");
    const res = await fetch("/api/v1/admin/students/import/", {
      method: "POST",
      headers: { Authorization: `Bearer ${access}` },
      body,
    });
    const payload = await res.json().catch(() => null);
    if (!res.ok) {
      setError({ message: payload?.error?.message || "Import failed." });
      return;
    }
    setImportResult(payload);
    load();
  }

  async function saveEdit(id) {
    setEditBusy(true);
    setError(null);
    try {
      await api(`/admin/students/${id}/`, {
        method: "PATCH",
        body: {
          ...(editForm.full_name ? { full_name: editForm.full_name } : {}),
          ...(editForm.section ? { section: Number(editForm.section) } : {}),
        },
      });
      setEditingId(null);
      toast.success("Learner updated.");
      load();
    } catch (err) {
      setError(err);
    } finally {
      setEditBusy(false);
    }
  }

  async function saveStudentPassword(s) {
    setPwBusy(true);
    setError(null);
    try {
      const result = await api(`/admin/users/${s.user}/set-password/`, {
        method: "POST",
        body: { password: pwValue },
      });
      setPwStudentId(null);
      setPwValue("");
      setPasswordModal({
        title: "Password set",
        name: s.full_name,
        username: s.lrn,
        role: "student",
        password: pwValue,
      });
      load();
    } catch (err) {
      setError(err);
    } finally {
      setPwBusy(false);
    }
  }

  if (!data) return error ? <ErrorBanner error={error} /> : <Spinner />;

  const q = rowFilter.trim().toLowerCase();
  const results = (data.results || []).filter(
    (s) => !q || s.full_name.toLowerCase().includes(q) || s.lrn.includes(q)
  );

  return (
    <>
      <PageHeader
        eyebrow="Manage"
        title="Students"
        sub="Enrolled learners. Create them one by one or import a CSV with columns: lrn, name, section."
      />
      {error && <div className="mb-space-sm"><ErrorBanner error={error} /></div>}
      {importResult && (
        <div className="mb-space-sm">
          <NoticeBanner>
            <p className="font-label-md text-label-md font-semibold">
              Imported {importResult.imported.length} learner{importResult.imported.length === 1 ? "" : "s"}
            </p>
            {importResult.imported.length > 0 && (
              <div className="mt-space-xs max-h-40 overflow-auto font-data-tabular-sm text-data-tabular-sm">
                {importResult.imported.map((s) => (
                  <div key={s.lrn} className="flex justify-between gap-space-md">
                    <span>{s.lrn} · {s.full_name}</span>
                    <span className="font-semibold">{s.temporary_password}</span>
                  </div>
                ))}
              </div>
            )}
            {importResult.errors?.length > 0 && (
              <div className="mt-space-xs pt-space-xs border-t border-on-tertiary-container/20 font-body-sm text-body-sm">
                {importResult.errors.map((e, i) => (
                  <div key={i}>Row {e.row}: {e.error}</div>
                ))}
              </div>
            )}
          </NoticeBanner>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg items-start">
        <div className="flex flex-col gap-space-lg">
          <SectionCard title="Add a learner">
            <form onSubmit={createStudent} className="flex flex-col gap-space-md">
              <Field label="LRN" hint="Exactly 12 digits">
                <input
                  className={inputClass}
                  value={form.lrn}
                  onChange={(e) => setForm({ ...form, lrn: e.target.value })}
                  pattern="\d{12}"
                  required
                />
              </Field>
              <Field label="Full name">
                <input
                  className={inputClass}
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  required
                />
              </Field>
              <Field label="Section">
                <select
                  className={inputClass}
                  value={form.section}
                  onChange={(e) => setForm({ ...form, section: e.target.value })}
                  required
                >
                  <option value="">Select section</option>
                  {sections.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.school_year})
                    </option>
                  ))}
                </select>
              </Field>
              <Btn type="submit" icon="person_add" className="justify-center" disabled={creating}>
                {creating ? "Creating…" : "Create learner"}
              </Btn>
            </form>
          </SectionCard>

          <SectionCard title="Import from CSV" sub="Header row required: lrn, name, section">
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                if (e.target.files[0]) importCsv(e.target.files[0]);
                e.target.value = "";
              }}
            />
            <Btn variant="secondary" icon="upload_file" className="w-full justify-center" onClick={() => fileRef.current?.click()}>
              Choose CSV file
            </Btn>
          </SectionCard>
        </div>

        <SectionCard
          className="lg:col-span-2"
          title="Enrolled learners"
          sub={`${data.count} total`}
        >
          <div className="flex min-h-11 items-center bg-surface-container-low border border-outline-variant/70 px-space-md py-space-xs rounded-lg w-full max-w-sm mb-space-md text-on-surface-variant">
            <span className="material-symbols-outlined text-base mr-space-xs">search</span>
            <input
              value={rowFilter}
              onChange={(e) => setRowFilter(e.target.value)}
              className="bg-transparent min-h-8 w-full font-body-sm text-body-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none"
              placeholder="Filter by name or LRN…"
              aria-label="Filter learners by name or LRN"
            />
          </div>
          {results.length === 0 ? (
            <EmptyState icon="group" title="No learners yet" sub="Add one or import a CSV." />
          ) : (
            <div className="overflow-x-auto max-md:overflow-visible">
              <table className="w-full text-left border-collapse max-md:block">
              <thead className="max-md:hidden">
                <tr className="border-b-2 border-surface-container-high">
                  <th className="py-space-sm pr-space-md font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">LRN</th>
                  <th className="py-space-sm pr-space-md font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Name</th>
                  <th className="py-space-sm pr-space-md font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Section</th>
                  <th className="py-space-sm pr-space-md font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Grade</th>
                  <th className="py-space-sm pr-space-md font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Status</th>
                  <th className="py-space-sm font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="max-md:flex max-md:flex-col max-md:gap-space-md">
                {results.map((s) => (
                  <Fragment key={s.id}>
                    <tr key={s.id} className="border-b border-surface-container-high/60 max-md:block max-md:rounded-xl max-md:border max-md:border-outline-variant max-md:bg-surface-container-low max-md:p-space-md">
                      <td data-label="LRN" className="py-space-2xs pr-space-md font-data-tabular-sm text-data-tabular-sm text-on-surface-variant max-md:flex max-md:items-center max-md:justify-between max-md:gap-space-md max-md:py-space-xs max-md:pr-0 max-md:text-right max-md:before:content-[attr(data-label)] max-md:before:font-label-sm max-md:before:text-label-sm max-md:before:text-on-surface-variant">
                        {s.lrn}
                      </td>
                      <td data-label="Name" className="py-space-2xs pr-space-md font-body-md text-body-md text-on-surface max-md:flex max-md:items-center max-md:justify-between max-md:gap-space-md max-md:py-space-xs max-md:pr-0 max-md:text-right max-md:before:content-[attr(data-label)] max-md:before:font-label-sm max-md:before:text-label-sm max-md:before:text-on-surface-variant">
                        {s.full_name}
                      </td>
                      <td data-label="Section" className="py-space-2xs pr-space-md font-body-sm text-body-sm text-on-surface-variant max-md:flex max-md:items-center max-md:justify-between max-md:gap-space-md max-md:py-space-xs max-md:pr-0 max-md:text-right max-md:before:content-[attr(data-label)] max-md:before:font-label-sm max-md:before:text-label-sm max-md:before:text-on-surface-variant">
                        {s.section_name}
                      </td>
                      <td data-label="Grade" className="py-space-2xs pr-space-md max-md:flex max-md:items-center max-md:justify-between max-md:gap-space-md max-md:py-space-xs max-md:pr-0 max-md:before:content-[attr(data-label)] max-md:before:font-label-sm max-md:before:text-label-sm max-md:before:text-on-surface-variant">
                        <TrendPill tone="info">{s.grade_level}</TrendPill>
                      </td>
                      <td data-label="Status" className="py-space-2xs pr-space-md max-md:flex max-md:items-center max-md:justify-between max-md:gap-space-md max-md:py-space-xs max-md:pr-0 max-md:before:content-[attr(data-label)] max-md:before:font-label-sm max-md:before:text-label-sm max-md:before:text-on-surface-variant">
                        {s.is_active ? (
                          <TrendPill tone="good" icon="check_circle">active</TrendPill>
                        ) : (
                          <TrendPill tone="bad" icon="block">deactivated</TrendPill>
                        )}
                      </td>
                      <td className="py-space-2xs text-right whitespace-nowrap max-md:mt-space-xs max-md:flex max-md:flex-wrap max-md:gap-space-xs max-md:border-t max-md:border-outline-variant max-md:pt-space-sm max-md:pr-0 max-md:text-left max-md:whitespace-normal">
                        {editingId === s.id ? (
                          <Btn variant="ghost" icon="close" onClick={() => setEditingId(null)}>
                            Cancel
                          </Btn>
                        ) : (
                          <>
                            <Btn
                              variant="ghost"
                              icon="description"
                              onClick={() => navigate(`/students/${s.id}/record`)}
                            >
                              Record
                            </Btn>
                            <Btn
                              variant="secondary"
                              icon="edit"
                              onClick={() => {
                                setEditingId(s.id);
                                setEditForm({ full_name: s.full_name, section: String(s.section) });
                                setPwStudentId(null);
                              }}
                            >
                              Edit
                            </Btn>
                          </>
                        )}
                        <Btn
                          variant="ghost"
                          icon="vpn_key"
                          onClick={() => {
                            setPwStudentId(pwStudentId === s.id ? null : s.id);
                            setPwValue("");
                            setEditingId(null);
                          }}
                        >
                          Password
                        </Btn>
                      </td>
                    </tr>
                    {pwStudentId === s.id && (
                      <tr key={`${s.id}-pw`} className="bg-surface-container-low max-md:block max-md:rounded-xl max-md:border max-md:border-outline-variant">
                        <td colSpan={6} className="py-space-sm px-space-md max-md:block">
                          <form
                            className="flex flex-wrap items-end gap-space-md"
                            onSubmit={(e) => {
                              e.preventDefault();
                              saveStudentPassword(s);
                            }}
                          >
                            <div className="w-full min-w-0 flex-1 sm:min-w-[240px]">
                              <Field
                                label={`New password for ${s.full_name}`}
                                hint="Min 8 characters, not similar to the LRN, not a common password."
                              >
                                <input
                                  className={inputClass}
                                  type="text"
                                  value={pwValue}
                                  onChange={(e) => setPwValue(e.target.value)}
                                  autoComplete="new-password"
                                  required
                                />
                              </Field>
                            </div>
                            <Btn type="submit" icon="vpn_key" disabled={pwBusy}>
                              {pwBusy ? "Saving…" : "Save password"}
                            </Btn>
                            <Btn type="button" variant="ghost" onClick={() => setPwStudentId(null)}>
                              Cancel
                            </Btn>
                          </form>
                        </td>
                      </tr>
                    )}
                    {editingId === s.id && (
                      <tr key={`${s.id}-edit`} className="bg-surface-container-low max-md:block max-md:rounded-xl max-md:border max-md:border-outline-variant">
                        <td colSpan={6} className="py-space-sm px-space-md max-md:block">
                          <div className="flex flex-wrap items-end gap-space-md">
                            <div className="w-full sm:w-64">
                              <Field label="Full name">
                                <input
                                  className={inputClass}
                                  value={editForm.full_name}
                                  onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                                />
                              </Field>
                            </div>
                            <div className="w-full sm:w-56">
                              <Field label="Section">
                                <select
                                  className={inputClass}
                                  value={editForm.section}
                                  onChange={(e) => setEditForm({ ...editForm, section: e.target.value })}
                                >
                                  {sections.map((sec) => (
                                    <option key={sec.id} value={sec.id}>
                                      {sec.name} ({sec.grade_level})
                                    </option>
                                  ))}
                                </select>
                              </Field>
                            </div>
                            <Btn icon="check" disabled={editBusy} onClick={() => saveEdit(s.id)}>
                              {editBusy ? "Saving…" : "Save changes"}
                            </Btn>
                          </div>
                        </td>
                      </tr>
                     )}
                   </Fragment>
                 ))}
              </tbody>
              </table>
            </div>
          )}
          <div className="mt-space-md flex flex-wrap items-center justify-center gap-space-sm sm:justify-end">
            <Btn variant="secondary" icon="chevron_left" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              Previous
            </Btn>
            <span className="font-label-sm text-label-sm text-on-surface-variant">
              Page {page} of {Math.max(1, Math.ceil(data.count / 50))}
            </span>
            <Btn variant="secondary" icon="chevron_right" disabled={!data.next} onClick={() => setPage(page + 1)}>
              Next
            </Btn>
          </div>
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
