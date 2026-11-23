"use client";

import { useCompare } from "@/lib/compare-context";
import { useToasts } from "@/lib/toast-context";

export default function CompareButton({
  productId,
  compact = false,
}: {
  productId: string;
  compact?: boolean;
}) {
  const { isComparing, toggle } = useCompare();
  const { success, error } = useToasts();
  const active = isComparing(productId);

  function handleClick() {
    const res = toggle(productId);
    if (!res.ok && res.reason === "limit") {
      error("Compare limit reached — max 4 products");
      return;
    }
    success(active ? "Removed from compare" : "Added to compare");
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-pressed={active}
      className={
        compact
          ? `p-2 rounded-lg border transition-colors press-down ${
              active
                ? "border-accent-cyan/60 text-accent-cyan bg-accent-cyan/10"
                : "border-border text-text-muted hover:bg-surface-hover"
            }`
          : `self-start p-2 rounded-lg border transition-colors press-down ${
              active
                ? "border-accent-cyan/60 text-accent-cyan bg-accent-cyan/10"
                : "border-border text-text-muted hover:bg-surface-hover"
            }`
      }
      aria-label={active ? "Remove from compare" : "Add to compare"}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M8 3H5a2 2 0 0 0-2 2v3" />
        <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
        <path d="M3 16v3a2 2 0 0 0 2 2h3" />
        <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
        <path d="M7 12h10" />
        <path d="m10 9-3 3 3 3" />
        <path d="m14 9 3 3-3 3" />
      </svg>
    </button>
  );
}
