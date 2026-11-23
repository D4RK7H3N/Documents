"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useCart } from "@/lib/cart-context";
import { SHIPPING_METHODS, calcShippingCost } from "@/lib/shipping";
import Reveal from "@/components/Reveal";

interface StockConflictItem {
  name: string;
  requested: number;
  available: number;
}

function formatPrice(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

export default function CheckoutPage() {
  const router = useRouter();
  const { items, subtotal, loading, refresh } = useCart();
  const [shippingAddr, setShippingAddr] = useState("");
  const [phone, setPhone] = useState("");
  const [shippingMethod, setShippingMethod] = useState<string>("STANDARD");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [stockConflicts, setStockConflicts] = useState<StockConflictItem[]>([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && items.length === 0) router.replace("/cart");
  }, [loading, items.length, router]);

  useEffect(() => {
    if (loading) return;
    fetch("/api/me")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data?.user) return;
        const u = data.user;
        if (u.phone) setPhone(u.phone);
        const parts = [u.addressLine, u.city, u.zipCode].filter(
          (p: string | null) => p && p.trim().length > 0,
        );
        if (parts.length > 0) setShippingAddr(parts.join(", "));
      });
  }, [loading]);

  const shipping = useMemo(
    () => SHIPPING_METHODS.find((m) => m.id === shippingMethod) ?? SHIPPING_METHODS[0],
    [shippingMethod],
  );
  const shippingCost = calcShippingCost(shipping, subtotal);
  const total = subtotal + shippingCost;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFieldError(null);
    setPhoneError(null);
    setFormError(null);
    setStockConflicts([]);
    setSubmitting(true);

    const res = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ shippingAddr, phone, shippingMethod }),
    });

    setSubmitting(false);

    if (!res.ok) {
      const data = await res.json();
      if (Array.isArray(data.items)) {
        setFormError(data.error ?? "Some items are out of stock");
        setStockConflicts(data.items);
      } else if (data.error?.fieldErrors?.shippingAddr) {
        setFieldError(data.error.fieldErrors.shippingAddr[0]);
      } else if (data.error?.fieldErrors?.phone) {
        setPhoneError(data.error.fieldErrors.phone[0]);
      } else {
        setFormError(typeof data.error === "string" ? data.error : "Something went wrong");
      }
      return;
    }

    const data = await res.json();
    await refresh();

    if (data.sessionUrl) {
      window.location.href = data.sessionUrl;
    } else {
      router.push("/orders?success=true");
    }
  }

  if (loading) {
    return (
      <main className="max-w-5xl mx-auto p-6">
        <h1 className="font-display text-3xl font-bold mb-6">CHECKOUT</h1>
        <div className="grid md:grid-cols-[1fr_320px] gap-8">
          <div className="h-64 glass-panel rounded-xl animate-pulse" />
          <div className="h-64 glass-panel rounded-xl animate-pulse" />
        </div>
      </main>
    );
  }

  if (items.length === 0) return null;

  return (
    <main className="max-w-5xl mx-auto p-6">
      <Reveal>
        <h1 className="font-display text-3xl font-bold mb-8">CHECKOUT</h1>
      </Reveal>

      <Reveal delay={80}>
        <div className="grid md:grid-cols-[1fr_320px] gap-8 items-start">
        <form onSubmit={handleSubmit} className="glass-panel rounded-xl p-6 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label htmlFor="shippingAddr" className="text-sm font-medium text-text-muted">
              Shipping address
            </label>
            <textarea
              id="shippingAddr"
              rows={4}
              placeholder="Where should we send your gear?"
              className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
              value={shippingAddr}
              onChange={(e) => setShippingAddr(e.target.value)}
            />
            {fieldError && <p className="text-xs text-danger">{fieldError}</p>}
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="phone" className="text-sm font-medium text-text-muted">
              Phone number
            </label>
            <input
              id="phone"
              type="tel"
              placeholder="For courier contact"
              className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
            {phoneError && <p className="text-xs text-danger">{phoneError}</p>}
          </div>

          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-text-muted">Shipping method</span>
            <div className="grid gap-2">
              {SHIPPING_METHODS.map((m) => {
                const cost =
                  m.freeThreshold !== null && subtotal >= m.freeThreshold
                    ? 0
                    : m.cost;
                const selected = m.id === shippingMethod;
                return (
                  <label
                    key={m.id}
                    className={`flex items-center justify-between gap-3 rounded-xl border p-3 cursor-pointer transition-colors ${
                      selected
                        ? "border-accent-cyan bg-accent-cyan/10"
                        : "border-border hover:bg-surface-hover"
                    }`}
                  >
                    <span className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="shippingMethod"
                        value={m.id}
                        checked={selected}
                        onChange={() => setShippingMethod(m.id)}
                        className="accent-[var(--accent-cyan)]"
                      />
                      <span className="flex flex-col">
                        <span className="text-sm font-medium">{m.label}</span>
                        <span className="text-xs text-text-muted">{m.eta}</span>
                      </span>
                    </span>
                    <span className={`font-mono-tabular text-sm ${cost === 0 ? "text-success" : "text-accent-cyan"}`}>
                      {cost === 0 ? "Free" : formatPrice(cost)}
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          {formError && <p className="text-sm text-danger">{formError}</p>}

          {stockConflicts.length > 0 && (
            <ul className="flex flex-col gap-1 text-sm text-danger">
              {stockConflicts.map((c) => (
                <li key={c.name}>
                  {c.name}: only {c.available} left, you asked for {c.requested}.
                </li>
              ))}
            </ul>
          )}

          <button
            type="submit"
            disabled={submitting || !shippingAddr.trim()}
            className="btn-primary rounded-lg px-4 py-2.5 text-sm disabled:opacity-50"
          >
            {submitting ? "Connecting to payment..." : "Place order"}
          </button>
          <p className="text-xs text-text-muted">
            You&apos;ll be taken to Stripe to complete the payment.
          </p>
        </form>

        <aside className="glass-panel rounded-xl p-5 h-fit flex flex-col gap-3">
          <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
            ORDER SUMMARY
          </h2>
          <ul className="flex flex-col gap-2">
            {items.map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 text-sm">
                <span className="truncate text-text-muted">
                  {item.product.name} <span className="text-text-muted/70">×{item.quantity}</span>
                </span>
                <span className="font-mono-tabular shrink-0">
                  {formatPrice(item.product.price * item.quantity)}
                </span>
              </li>
            ))}
          </ul>
          <div className="border-t border-border pt-3 flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-muted">Subtotal</span>
              <span className="font-mono-tabular">{formatPrice(subtotal)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-muted">
                Shipping ({shipping.label})
              </span>
              <span className={`font-mono-tabular ${shippingCost === 0 ? "text-success" : ""}`}>
                {shippingCost === 0 ? "Free" : formatPrice(shippingCost)}
              </span>
            </div>
            <div className="flex items-center justify-between pt-1">
              <span className="text-sm text-text-muted">Total</span>
              <span className="font-mono-tabular text-lg font-medium text-accent-cyan">
                {formatPrice(total)}
              </span>
            </div>
          </div>
        </aside>
        </div>
      </Reveal>
    </main>
  );
}
