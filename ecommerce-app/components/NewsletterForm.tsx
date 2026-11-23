"use client";

import { useState } from "react";
import { useToasts } from "@/lib/toast-context";

export default function NewsletterForm() {
  const { success, info, error } = useToasts();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    const res = await fetch("/api/newsletter", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    setBusy(false);
    if (res.ok) {
      const data = await res.json().catch(() => null);
      if (data?.already) info("You're already on the list.");
      else success("Subscribed — watch your inbox.");
      setEmail("");
    } else {
      const data = await res.json().catch(() => null);
      error(data?.error ?? "Could not subscribe");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        type="email"
        required
        placeholder="you@example.com"
        aria-label="Email for newsletter"
        className="input-field rounded-lg px-3 py-1.5 text-sm w-44 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <button
        type="submit"
        disabled={busy}
        className="btn-primary rounded-lg px-3 py-1.5 text-sm press-down disabled:opacity-50"
      >
        Join
      </button>
    </form>
  );
}
