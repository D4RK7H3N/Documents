"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCart } from "@/lib/cart-context";
import { useToasts } from "@/lib/toast-context";

export default function WishlistButton({
  productId,
  compact = false,
}: {
  productId: string;
  compact?: boolean;
}) {
  const router = useRouter();
  const { wishlist, toggleWishlist, loggedIn } = useCart();
  const { success, error } = useToasts();
  const [busy, setBusy] = useState(false);

  const active = wishlist.includes(productId);

  async function handleToggle() {
    setBusy(true);
    const res = await toggleWishlist(productId);
    setBusy(false);
    if (!res.ok) {
      error(res.error ?? "Couldn't update wishlist");
      if (res.error?.includes("Log in")) router.push("/login");
      return;
    }
    success(active ? "Removed from wishlist" : "Added to wishlist");
    router.refresh();
  }

  const label = active ? "Remove from wishlist" : "Add to wishlist";

  return (
    <div className={compact ? "" : "flex flex-col gap-1"}>
      <button
        type="button"
        onClick={handleToggle}
        disabled={busy || !loggedIn}
        aria-label={label}
        aria-pressed={active}
        className={
          compact
            ? "absolute top-2 right-2 p-2 rounded-full bg-surface/80 backdrop-blur border border-border hover:scale-110 active:scale-95 transition-transform disabled:opacity-50"
            : "self-start p-2 rounded-lg border border-border hover:bg-surface-hover transition-colors disabled:opacity-50"
        }
      >
        <span key={active ? "on" : "off"} className={active ? "inline-block anim-pop" : "inline-block"}>
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill={active ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={active ? "text-accent-pink" : "text-text-muted"}
          >
            <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
          </svg>
        </span>
      </button>
    </div>
  );
}
