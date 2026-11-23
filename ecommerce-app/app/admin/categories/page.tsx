"use client";

import { useEffect, useState } from "react";
import AdminTabs from "@/components/AdminTabs";
import { useToasts } from "@/lib/toast-context";

interface Category {
  id: string;
  name: string;
  slug: string;
  _count: { products: number };
}

export default function AdminCategoriesPage() {
  const { success, error } = useToasts();
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const res = await fetch("/api/categories");
    const data = await res.json();
    setCategories(data.categories);
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, []);

  async function createCategory(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    const res = await fetch("/api/categories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName }),
    });
    setBusy(false);
    if (!res.ok) {
      const data = await res.json();
      error(typeof data.error === "string" ? data.error : "Couldn't create category");
      return;
    }
    setNewName("");
    success("Category created");
    load();
  }

  async function renameCategory(id: string) {
    setBusy(true);
    const res = await fetch(`/api/categories/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: editName }),
    });
    setBusy(false);
    if (!res.ok) {
      const data = await res.json();
      error(typeof data.error === "string" ? data.error : "Couldn't rename category");
      return;
    }
    setEditingId(null);
    success("Category renamed");
    load();
  }

  async function deleteCategory(id: string) {
    if (!confirm("Delete this category?")) return;
    setBusy(true);
    const res = await fetch(`/api/categories/${id}`, { method: "DELETE" });
    setBusy(false);
    if (!res.ok) {
      const data = await res.json();
      error(typeof data.error === "string" ? data.error : "Couldn't delete category");
      return;
    }
    success("Category deleted");
    load();
  }

  if (!categories) {
    return (
      <main className="max-w-3xl mx-auto p-6 mt-12">
        <div className="h-64 glass-panel rounded-xl animate-pulse" />
      </main>
    );
  }

  return (
    <main className="max-w-3xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <h1 className="font-display text-3xl font-bold">CATEGORIES</h1>
        <AdminTabs active="/admin/categories" />
      </div>

      <form onSubmit={createCategory} className="glass-panel rounded-xl p-6 flex flex-col gap-4">
        <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">NEW CATEGORY</h2>
        <input
          type="text"
          placeholder="Category name"
          className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          required
        />
        <button type="submit" disabled={busy} className="btn-primary rounded-lg px-4 py-2 text-sm disabled:opacity-50">
          {busy ? "Creating..." : "Create category"}
        </button>
      </form>

      {categories.length === 0 ? (
        <p className="text-text-muted">No categories yet.</p>
      ) : (
        <div className="glass-panel rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-muted border-b border-border">
                <th className="p-3 font-medium">Name</th>
                <th className="p-3 font-medium">Slug</th>
                <th className="p-3 font-medium">Products</th>
                <th className="p-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((c) => (
                <tr key={c.id} className="border-b border-border last:border-b-0">
                  <td className="p-3 font-semibold">
                    {editingId === c.id ? (
                      <input
                        type="text"
                        className="input-field rounded-lg px-2 py-1 text-sm w-full focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        autoFocus
                      />
                    ) : (
                      c.name
                    )}
                  </td>
                  <td className="p-3 font-mono-tabular text-text-muted">{c.slug}</td>
                  <td className="p-3 text-text-muted">{c._count.products}</td>
                  <td className="p-3 flex justify-end gap-2">
                    {editingId === c.id ? (
                      <button
                        onClick={() => renameCategory(c.id)}
                        disabled={busy}
                        className="btn-primary rounded-lg px-3 py-1.5 text-sm disabled:opacity-50"
                      >
                        Save
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          setEditingId(c.id);
                          setEditName(c.name);
                        }}
                        className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors"
                      >
                        Rename
                      </button>
                    )}
                    <button
                      onClick={() => deleteCategory(c.id)}
                      disabled={busy}
                      className="rounded-lg px-3 py-1.5 text-sm text-danger border border-danger/30 hover:bg-danger/10 transition-colors disabled:opacity-50 press-down"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
