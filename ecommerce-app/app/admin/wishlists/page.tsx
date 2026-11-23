"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AdminTabs from "@/components/AdminTabs";
import { useToasts } from "@/lib/toast-context";

interface AdminWishlistItem {
  id: string;
  createdAt: string;
  product: { name: string };
  user: { name: string; email: string };
}

export default function AdminWishlistsPage() {
  const router = useRouter();
  const { success, error } = useToasts();
  const [items, setItems] = useState<AdminWishlistItem[] | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const res = await fetch("/api/admin/wishlists");
    const data = await res.json();
    setItems(data.items);
  }

  async function handleDelete(id: string) {
    if (!confirm("Remove this wishlist entry?")) return;
    setBusy(true);

    const res = await fetch(`/api/admin/wishlists/${id}`, { method: "DELETE" });

    setBusy(false);

    if (!res.ok) {
      const data = await res.json();
      error(typeof data.error === "string" ? data.error : "Couldn't delete wishlist entry");
      return;
    }

    await load();
    router.refresh();
    success("Wishlist entry removed");
  }

  if (!items) {
    return (
      <main className="max-w-6xl mx-auto p-6 mt-12">
        <div className="h-64 glass-panel rounded-xl animate-pulse" />
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <h1 className="font-display text-3xl font-bold">WISHLISTS</h1>
        <AdminTabs active="/admin/wishlists" />
      </div>

      {items.length === 0 ? (
        <p className="text-text-muted">No wishlist entries yet.</p>
      ) : (
        <div className="glass-panel rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-muted border-b border-border">
                <th className="p-3 font-medium">User</th>
                <th className="p-3 font-medium">Product</th>
                <th className="p-3 font-medium">Saved</th>
                <th className="p-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.id} className="border-b border-border last:border-b-0">
                  <td className="p-3 text-text-muted">
                    {i.user.name}
                    <span className="block text-xs">{i.user.email}</span>
                  </td>
                  <td className="p-3 font-medium">{i.product.name}</td>
                  <td className="p-3 text-text-muted">
                    {new Date(i.createdAt).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => handleDelete(i.id)}
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
