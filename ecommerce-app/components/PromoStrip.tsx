"use client";

import { useState } from "react";

export default function PromoStrip() {
  const [visible, setVisible] = useState(() => {
    if (typeof window === "undefined") return true;
    return sessionStorage.getItem("promo-dismissed") !== "1";
  });

  if (!visible) return null;

  function dismiss() {
    sessionStorage.setItem("promo-dismissed", "1");
    setVisible(false);
  }

  return (
    <div className="relative text-center text-xs font-medium py-1.5 px-10 bg-gradient-to-r from-accent-purple/25 via-accent-pink/25 to-accent-cyan/25 border-b border-border/60">
      <span className="tracking-[0.25em] uppercase text-text-muted">
        ✦ Free standard shipping over $75 ✦
      </span>
      <button
        onClick={dismiss}
        aria-label="Dismiss promo banner"
        className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text transition-colors press-down"
      >
        ✕
      </button>
    </div>
  );
}
