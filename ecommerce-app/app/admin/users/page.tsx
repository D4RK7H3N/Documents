"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AdminTabs from "@/components/AdminTabs";
import { useToasts } from "@/lib/toast-context";

interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: "CUSTOMER" | "ADMIN";
  createdAt: string;
  _count: { orders: number; reviews: number };
}

type FormErrors = Record<string, string>;

function extractErrors(error: unknown): FormErrors {
  if (typeof error === "string") return { form: error };
  if (error && typeof error === "object" && "fieldErrors" in error) {
    const e = error as { fieldErrors?: Record<string, string[]>; formErrors?: string[] };
    const out: FormErrors = {};
    for (const [key, messages] of Object.entries(e.fieldErrors ?? {})) {
      if (messages.length > 0) out[key] = messages[0];
    }
    if (e.formErrors?.length) out.form = e.formErrors[0];
    return out;
  }
  return { form: "Something went wrong" };
}

export default function AdminUsersPage() {
  const router = useRouter();
  const { success, error } = useToasts();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [editForm, setEditForm] = useState({ name: "", email: "", role: "CUSTOMER" });
  const [editErrors, setEditErrors] = useState<FormErrors>({});

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const res = await fetch("/api/admin/users");
    const data = await res.json();
    setUsers(data.users);
  }

  function openEdit(u: AdminUser) {
    setEditErrors({});
    setEditing(u);
    setEditForm({ name: u.name, email: u.email, role: u.role });
  }

  async function handleEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setEditErrors({});
    setBusy(true);

    const res = await fetch(`/api/admin/users/${editing.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(editForm),
    });

    setBusy(false);

    if (!res.ok) {
      const data = await res.json();
      setEditErrors(extractErrors(data.error));
      return;
    }

    setEditing(null);
    await load();
    router.refresh();
    success("User updated");
  }

  async function handleDelete(u: AdminUser) {
    if (!confirm(`Delete user ${u.name}?`)) return;
    setBusy(true);

    const res = await fetch(`/api/admin/users/${u.id}`, { method: "DELETE" });

    setBusy(false);

    if (!res.ok) {
      const data = await res.json();
      error(typeof data.error === "string" ? data.error : "Couldn't delete user");
      return;
    }

    await load();
    router.refresh();
    success("User deleted");
  }

  if (!users) {
    return (
      <main className="max-w-6xl mx-auto p-6 mt-12">
        <div className="h-64 glass-panel rounded-xl animate-pulse" />
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <h1 className="font-display text-3xl font-bold">USERS</h1>
        <AdminTabs active="/admin/users" />
      </div>

      {users.length === 0 ? (
        <p className="text-text-muted">No users yet.</p>
      ) : (
        <div className="glass-panel rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-muted border-b border-border">
                <th className="p-3 font-medium">User</th>
                <th className="p-3 font-medium">Role</th>
                <th className="p-3 font-medium">Orders</th>
                <th className="p-3 font-medium">Reviews</th>
                <th className="p-3 font-medium">Joined</th>
                <th className="p-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-border last:border-b-0">
                  <td className="p-3">
                    <span className="font-medium">{u.name}</span>
                    <span className="text-text-muted block">{u.email}</span>
                  </td>
                  <td className="p-3">
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                        u.role === "ADMIN"
                          ? "bg-accent-pink/10 text-accent-pink border border-accent-pink/30"
                          : "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/30"
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="p-3 font-mono-tabular">{u._count.orders}</td>
                  <td className="p-3 font-mono-tabular">{u._count.reviews}</td>
                  <td className="p-3 text-text-muted">
                    {new Date(u.createdAt).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </td>
                  <td className="p-3">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => openEdit(u)}
                        className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(u)}
                        disabled={busy}
                        className="rounded-lg px-3 py-1.5 text-sm text-danger border border-danger/30 hover:bg-danger/10 transition-colors disabled:opacity-50 press-down"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <form
            onSubmit={handleEdit}
            className="glass-panel rounded-xl p-6 flex flex-col gap-4 w-full max-w-sm"
          >
            <h2 className="font-display text-xl font-bold">EDIT USER</h2>

            <div className="flex flex-col gap-2">
              <label htmlFor="edit-name" className="text-sm font-medium text-text-muted">
                Name
              </label>
              <input
                id="edit-name"
                type="text"
                className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                required
              />
              {editErrors.name && <p className="text-xs text-danger">{editErrors.name}</p>}
            </div>

            <div className="flex flex-col gap-2">
              <label htmlFor="edit-email" className="text-sm font-medium text-text-muted">
                Email
              </label>
              <input
                id="edit-email"
                type="email"
                className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
                value={editForm.email}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                required
              />
              {editErrors.email && <p className="text-xs text-danger">{editErrors.email}</p>}
            </div>

            <div className="flex flex-col gap-2">
              <label htmlFor="edit-role" className="text-sm font-medium text-text-muted">
                Role
              </label>
              <select
                id="edit-role"
                className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
                value={editForm.role}
                onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
              >
                <option value="CUSTOMER">CUSTOMER</option>
                <option value="ADMIN">ADMIN</option>
              </select>
              {editErrors.role && <p className="text-xs text-danger">{editErrors.role}</p>}
            </div>

            {editErrors.form && <p className="text-sm text-danger">{editErrors.form}</p>}

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="btn-ghost rounded-lg px-4 py-2 text-sm hover:bg-surface-hover transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={busy}
                className="btn-primary rounded-lg px-4 py-2 text-sm disabled:opacity-50"
              >
                {busy ? "Saving..." : "Save"}
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}
