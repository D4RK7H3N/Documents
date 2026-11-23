"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AdminTabs from "@/components/AdminTabs";
import { useToasts } from "@/lib/toast-context";

interface AdminReview {
  id: string;
  rating: number;
  comment: string | null;
  createdAt: string;
  product: { name: string };
  user: { name: string; email: string };
}

export default function AdminReviewsPage() {
  const router = useRouter();
  const { success, error } = useToasts();
  const [reviews, setReviews] = useState<AdminReview[] | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const res = await fetch("/api/admin/reviews");
    const data = await res.json();
    setReviews(data.reviews);
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this review?")) return;
    setBusy(true);

    const res = await fetch(`/api/admin/reviews/${id}`, { method: "DELETE" });

    setBusy(false);

    if (!res.ok) {
      const data = await res.json();
      error(typeof data.error === "string" ? data.error : "Couldn't delete review");
      return;
    }

    await load();
    router.refresh();
    success("Review deleted");
  }

  if (!reviews) {
    return (
      <main className="max-w-6xl mx-auto p-6 mt-12">
        <div className="h-64 glass-panel rounded-xl animate-pulse" />
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <h1 className="font-display text-3xl font-bold">REVIEWS</h1>
        <AdminTabs active="/admin/reviews" />
      </div>

      {reviews.length === 0 ? (
        <p className="text-text-muted">No reviews yet.</p>
      ) : (
        <div className="glass-panel rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-muted border-b border-border">
                <th className="p-3 font-medium">Product</th>
                <th className="p-3 font-medium">User</th>
                <th className="p-3 font-medium">Rating</th>
                <th className="p-3 font-medium">Comment</th>
                <th className="p-3 font-medium">Date</th>
                <th className="p-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((r) => (
                <tr key={r.id} className="border-b border-border last:border-b-0">
                  <td className="p-3 font-medium">{r.product.name}</td>
                  <td className="p-3 text-text-muted">
                    {r.user.name}
                    <span className="block text-xs">{r.user.email}</span>
                  </td>
                  <td className="p-3 text-accent-pink" aria-label={`${r.rating} out of 5 stars`}>
                    {"★".repeat(r.rating)}
                    <span className="text-text-muted">{"★".repeat(5 - r.rating)}</span>
                  </td>
                  <td className="p-3 text-text-muted max-w-xs truncate">{r.comment ?? "—"}</td>
                  <td className="p-3 text-text-muted">
                    {new Date(r.createdAt).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => handleDelete(r.id)}
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
