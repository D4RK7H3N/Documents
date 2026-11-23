import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import {
  Btn,
  Card,
  ErrorBanner,
  PageHeader,
  SectionCard,
  Spinner,
  TempPasswordModal,
  TrendPill,
  inputClass,
  useToast,
} from "../components/ui";

const ROLE_FILTERS = [["", "All"], ["student", "Students"], ["teacher", "Teachers"], ["admin", "Administrators"]];

export default function Users() {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [role, setRole] = useState("");
  const [page, setPage] = useState(1);
  const [passwordModal, setPasswordModal] = useState(null);

  const load = useCallback(async () => {
    try {
      setData(await api(`/admin/users/?page=${page}${role ? `&role=${role}` : ""}`));
    } catch (err) {
      setError(err);
    }
  }, [page, role]);

  useEffect(() => {
    load();
  }, [load]);

  async function resetPassword(id, username) {
    if (!window.confirm(`Issue a new temporary password for ${username}?`)) return;
    try {
      const result = await api(`/admin/users/${id}/reset-password/`, { method: "POST", body: {} });
      setPasswordModal({
        title: "Password reset",
        username,
        role: "account",
        password: result.temporary_password,
      });
    } catch (err) {
      setError(err);
    }
  }

  async function setStatus(id, username, isActive) {
    try {
      await api(`/admin/users/${id}/status/`, { method: "POST", body: { is_active: isActive } });
      toast.success(`${username} ${isActive ? "activated" : "deactivated"}.`);
      load();
    } catch (err) {
      setError(err);
    }
  }

  if (!data) return error ? <ErrorBanner error={error} /> : <Spinner />;
  const results = data.results || [];

  return (
    <>
      <PageHeader
        eyebrow="Manage"
        title="User Accounts"
        sub="Reset passwords and activate or deactivate accounts. Deactivated users keep their records."
      />
      {error && <div className="mb-space-sm"><ErrorBanner error={error} /></div>}

      <SectionCard title="Accounts" sub={`${data.count} total`}>
        <div className="flex flex-wrap items-center gap-space-2xs bg-surface-container-low border border-outline-variant/70 p-space-2xs rounded-lg w-full sm:w-fit mb-space-md">
          {ROLE_FILTERS.map(([value, label]) => (
            <button
              key={value}
              onClick={() => {
                setRole(value);
                setPage(1);
              }}
              className={`min-h-11 px-space-md py-space-xs rounded-lg font-label-md text-label-md transition-colors ${
                role === value
                  ? "bg-surface-container-lowest text-on-surface shadow-sm font-semibold"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="overflow-x-auto max-md:overflow-visible">
          <table className="w-full text-left border-collapse max-md:block">
            <thead className="max-md:hidden">
              <tr className="border-b-2 border-surface-container-high">
                <th className="py-space-sm pr-space-md font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Username</th>
                <th className="py-space-sm pr-space-md font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Role</th>
                <th className="py-space-sm pr-space-md font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Password</th>
                <th className="py-space-sm font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Actions</th>
              </tr>
            </thead>
            <tbody className="max-md:flex max-md:flex-col max-md:gap-space-md">
              {results.map((u) => (
                <tr key={u.id} className="border-b border-surface-container-high/60 max-md:block max-md:rounded-xl max-md:border max-md:border-outline-variant max-md:bg-surface-container-low max-md:p-space-md">
                  <td data-label="Username" className="py-space-2xs pr-space-md font-data-tabular-sm text-data-tabular-sm text-on-surface max-md:flex max-md:items-center max-md:justify-between max-md:gap-space-md max-md:py-space-xs max-md:pr-0 max-md:text-right max-md:before:content-[attr(data-label)] max-md:before:font-label-sm max-md:before:text-label-sm max-md:before:text-on-surface-variant">
                    {u.username}
                  </td>
                  <td data-label="Role" className="py-space-2xs pr-space-md max-md:flex max-md:items-center max-md:justify-between max-md:gap-space-md max-md:py-space-xs max-md:pr-0 max-md:before:content-[attr(data-label)] max-md:before:font-label-sm max-md:before:text-label-sm max-md:before:text-on-surface-variant">
                    <TrendPill tone={u.role === "admin" ? "bad" : u.role === "teacher" ? "info" : "neutral"}>{u.role}</TrendPill>
                  </td>
                  <td data-label="Password" className="py-space-2xs pr-space-md max-md:flex max-md:items-center max-md:justify-between max-md:gap-space-md max-md:py-space-xs max-md:pr-0 max-md:before:content-[attr(data-label)] max-md:before:font-label-sm max-md:before:text-label-sm max-md:before:text-on-surface-variant">
                    {u.must_change_password ? (
                      <TrendPill tone="warn" icon="lock_reset">change pending</TrendPill>
                    ) : (
                      <TrendPill tone="good" icon="check_circle">set</TrendPill>
                    )}
                  </td>
                  <td className="py-space-2xs max-md:mt-space-xs max-md:border-t max-md:border-outline-variant max-md:pt-space-sm max-md:pr-0">
                    <div className="flex gap-space-xs max-md:flex-wrap">
                      <Btn variant="secondary" icon="key" onClick={() => resetPassword(u.id, u.username)}>
                        Reset
                      </Btn>
                      <Btn variant="ghost" icon="block" onClick={() => setStatus(u.id, u.username, false)}>
                        Deactivate
                      </Btn>
                      <Btn variant="ghost" icon="check_circle" onClick={() => setStatus(u.id, u.username, true)}>
                        Activate
                      </Btn>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-space-md flex flex-wrap items-center justify-center gap-space-sm sm:justify-end">
          <Btn variant="secondary" icon="chevron_left" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </Btn>
          <Btn variant="secondary" icon="chevron_right" disabled={!data.next} onClick={() => setPage(page + 1)}>
            Next
          </Btn>
        </div>
      </SectionCard>

      <TempPasswordModal
        open={Boolean(passwordModal)}
        title={passwordModal?.title}
        username={passwordModal?.username}
        role={passwordModal?.role}
        password={passwordModal?.password}
        onClose={() => setPasswordModal(null)}
      />
    </>
  );
}
