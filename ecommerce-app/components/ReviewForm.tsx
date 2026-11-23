"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useToasts } from "@/lib/toast-context";

export default function ReviewForm({ productId }: { productId: string }) {
  const router = useRouter();
  const { success, error } = useToasts();
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!rating) {
      error("Pick a star rating first");
      return;
    }
    setSubmitting(true);

    const res = await fetch(`/api/products/${productId}/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating, comment: comment.trim() || null }),
    });

    setSubmitting(false);

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const msg =
        typeof data.error === "string"
          ? data.error
          : data.error?.fieldErrors?.rating?.[0] ??
            data.error?.fieldErrors?.comment?.[0] ??
            "Couldn't submit review";
      error(msg);
      return;
    }

    success("Review submitted");
    setRating(0);
    setComment("");
    router.refresh();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="glass-panel rounded-xl p-4 flex flex-col gap-3 max-w-md"
    >
      <div className="flex items-center gap-1" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => setRating(n)}
            onMouseEnter={() => setHover(n)}
            onMouseLeave={() => setHover(0)}
            aria-label={`${n} star${n > 1 ? "s" : ""}`}
            className={`text-2xl transition-colors ${
              n <= (hover || rating) ? "text-accent-pink" : "text-text-muted"
            }`}
          >
            ★
          </button>
        ))}
        {rating > 0 && (
          <span className="font-mono-tabular text-sm text-text-muted ml-2">
            {rating}/5
          </span>
        )}
      </div>

      <textarea
        placeholder="What did you think? (optional)"
        rows={3}
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        maxLength={1000}
        className="input-field rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
      />

      <button
        type="submit"
        disabled={submitting}
        className="btn-primary rounded-lg px-4 py-2 text-sm self-start disabled:opacity-50"
      >
        {submitting ? "Submitting..." : "Submit review"}
      </button>
    </form>
  );
}
