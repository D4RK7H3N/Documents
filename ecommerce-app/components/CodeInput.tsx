"use client";

import { useRef } from "react";

export default function CodeInput({
  value,
  onChange,
  onComplete,
  disabled,
  invalid,
}: {
  value: string;
  onChange: (code: string) => void;
  onComplete?: (code: string) => void;
  disabled?: boolean;
  invalid?: boolean;
}) {
  const ref = useRef<HTMLInputElement | null>(null);

  return (
    <input
      ref={ref}
      inputMode="numeric"
      autoComplete="one-time-code"
      maxLength={6}
      pattern="\d{6}"
      placeholder="••••••"
      disabled={disabled}
      value={value}
      onChange={(e) => {
        const digits = e.target.value.replace(/\D/g, "").slice(0, 6);
        onChange(digits);
        if (digits.length === 6) onComplete?.(digits);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" && value.length === 6) {
          e.preventDefault();
          onComplete?.(value);
        }
      }}
      className={`input-field w-full rounded-lg px-3 py-2.5 text-center font-mono-tabular text-lg tracking-[0.4em] focus:outline-none focus:ring-2 disabled:opacity-50 ${
        invalid ? "border-rose-500/60 focus:ring-rose-500/40" : "focus:ring-accent-cyan/60"
      }`}
    />
  );
}