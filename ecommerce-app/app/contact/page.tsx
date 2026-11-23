"use client";

import { useState } from "react";
import { useToasts } from "@/lib/toast-context";
import Reveal from "@/components/Reveal";

export default function ContactPage() {
  const { success, error } = useToasts();
  const [form, setForm] = useState({ name: "", email: "", message: "" });
  const [busy, setBusy] = useState(false);

  function setField(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    const res = await fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setBusy(false);
    if (res.ok) {
      success("Message sent — we'll reply soon.");
      setForm({ name: "", email: "", message: "" });
    } else {
      const data = await res.json().catch(() => null);
      error(data?.error ?? "Could not send your message");
    }
  }

  return (
    <main className="max-w-3xl mx-auto px-6 py-10 flex flex-col gap-8">
      <Reveal>
        <div className="flex flex-col gap-2">
          <p className="font-mono-tabular text-xs tracking-[0.3em] text-accent-pink uppercase">
            Talk to us
          </p>
          <h1 className="font-display text-3xl md:text-4xl font-bold">Contact</h1>
          <p className="text-text-muted">
            Questions about an order, a product, or your gear setup? Drop a
            message and we&apos;ll get back to you within one business day.
          </p>
        </div>
      </Reveal>

      <Reveal delay={80}>
        <div className="grid gap-6 md:grid-cols-[1fr_280px] items-start">
        <form onSubmit={handleSubmit} className="glass-panel rounded-xl p-5 flex flex-col gap-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label htmlFor="contact-name" className="text-xs tracking-widest text-text-muted uppercase">
                Name
              </label>
              <input
                id="contact-name"
                type="text"
                required
                placeholder="Your name"
                className="input-field rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
                value={form.name}
                onChange={(e) => setField("name", e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="contact-email" className="text-xs tracking-widest text-text-muted uppercase">
                Email
              </label>
              <input
                id="contact-email"
                type="email"
                required
                placeholder="you@example.com"
                className="input-field rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
                value={form.email}
                onChange={(e) => setField("email", e.target.value)}
              />
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="contact-message" className="text-xs tracking-widest text-text-muted uppercase">
              Message
            </label>
            <textarea
              id="contact-message"
              required
              rows={5}
              placeholder="What's on your mind?"
              className="input-field rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
              value={form.message}
              onChange={(e) => setField("message", e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="btn-primary rounded-lg px-4 py-2 text-sm press-down disabled:opacity-50 self-start"
          >
            Send message
          </button>
        </form>

        <aside className="flex flex-col gap-3">
          <div className="glass-panel rounded-xl p-4 flex flex-col gap-1">
            <span className="text-xs tracking-widest text-text-muted uppercase">Email</span>
            <a href="mailto:support@clickbound.dev" className="text-sm text-accent-cyan hover:underline">
              support@clickbound.dev
            </a>
          </div>
          <div className="glass-panel rounded-xl p-4 flex flex-col gap-1">
            <span className="text-xs tracking-widest text-text-muted uppercase">Hours</span>
            <span className="text-sm">Mon–Fri, 9:00–18:00</span>
            <span className="text-sm">Sat, 10:00–14:00</span>
          </div>
          <div className="glass-panel rounded-xl p-4 flex flex-col gap-1">
            <span className="text-xs tracking-widest text-text-muted uppercase">Returns</span>
            <span className="text-sm">30 days, unopened — see the FAQ.</span>
          </div>
        </aside>
        </div>
      </Reveal>
    </main>
  );
}
