"use client";

import Link from "next/link";
import { useState } from "react";
import { useCart } from "@/lib/cart-context";
import Reveal from "@/components/Reveal";

function formatPrice(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

function Thumb({ url, alt }: { url: string | null; alt: string }) {
  if (url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt={alt} className="w-16 h-16 rounded-lg object-cover shrink-0" />;
  }
  return (
    <div
      className="w-16 h-16 rounded-lg shrink-0"
      style={{
        background:
          "radial-gradient(circle at 30% 25%, var(--accent-purple) 0%, transparent 60%), radial-gradient(circle at 70% 60%, var(--accent-pink) 0%, transparent 60%), radial-gradient(circle at 45% 85%, var(--accent-cyan) 0%, transparent 60%), var(--surface)",
      }}
    />
  );
}

export default function CartPage() {
  const { items, subtotal, loading, loggedIn, refresh } = useCart();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function updateQuantity(itemId: string, quantity: number) {
    if (quantity < 1) return;
    setBusyId(itemId);
    setError(null);
    const res = await fetch(`/api/cart/${itemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.error ?? "Couldn't update quantity");
    }
    await refresh();
    setBusyId(null);
  }

  async function removeItem(itemId: string) {
    setBusyId(itemId);
    setError(null);
    const res = await fetch(`/api/cart/${itemId}`, { method: "DELETE" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.error ?? "Couldn't remove item");
    }
    await refresh();
    setBusyId(null);
  }

  if (loading) {
    return (
      <main className="max-w-4xl mx-auto p-6">
        <h1 className="font-display text-3xl font-bold mb-6">CART</h1>
        <div className="flex flex-col gap-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 glass-panel rounded-xl animate-pulse" />
          ))}
        </div>
      </main>
    );
  }

  if (!loggedIn) {
    return (
      <main className="max-w-4xl mx-auto p-6 flex flex-col items-center gap-4 text-center pt-16">
        <h1 className="font-display text-3xl font-bold">CART</h1>
        <p className="text-text-muted">Log in to see your cart.</p>
        <Link href="/login" className="btn-primary rounded-lg px-4 py-2 text-sm">
          Log in
        </Link>
      </main>
    );
  }

  if (items.length === 0) {
    return (
      <main className="max-w-4xl mx-auto p-6 flex flex-col items-center gap-4 text-center pt-16">
        <h1 className="font-display text-3xl font-bold">CART</h1>
        <p className="text-text-muted">Your cart is empty. The shop is still glowing — go grab something.</p>
        <Link href="/" className="btn-primary rounded-lg px-4 py-2 text-sm">
          Back to shop
        </Link>
      </main>
    );
  }

  return (
    <main className="max-w-4xl mx-auto p-6 flex flex-col gap-6">
      <Reveal>
        <h1 className="font-display text-3xl font-bold">CART</h1>
      </Reveal>

      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="flex flex-col gap-4">
        {items.map((item, i) => (
          <Reveal key={item.id} delay={i * 60}>
            <div className="glass-panel rounded-xl p-4 flex items-center gap-4">
            <Thumb url={item.product.imageUrl} alt={item.product.name} />

            <div className="flex-1 flex flex-col gap-1 min-w-0">
              <p className="font-display font-semibold truncate">{item.product.name}</p>
              <p className="font-mono-tabular text-sm text-text-muted">{formatPrice(item.product.price)} each</p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => updateQuantity(item.id, item.quantity - 1)}
                disabled={busyId === item.id || item.quantity <= 1}
                className="w-7 h-7 rounded-md border border-border text-text-muted hover:text-text hover:bg-surface-hover transition-colors disabled:opacity-40 press-down"
                aria-label="Decrease quantity"
              >
                −
              </button>
              <span className="font-mono-tabular text-sm min-w-6 text-center">{item.quantity}</span>
              <button
                onClick={() => updateQuantity(item.id, item.quantity + 1)}
                disabled={busyId === item.id}
                className="w-7 h-7 rounded-md border border-border text-text-muted hover:text-text hover:bg-surface-hover transition-colors disabled:opacity-40 press-down"
                aria-label="Increase quantity"
              >
                +
              </button>
            </div>

            <span className="font-mono-tabular font-medium text-accent-cyan w-24 text-right">
              {formatPrice(item.product.price * item.quantity)}
            </span>

            <button
              onClick={() => removeItem(item.id)}
              disabled={busyId === item.id}
              className="text-sm text-danger hover:opacity-80 transition-opacity disabled:opacity-40 press-down"
            >
              Remove
            </button>
          </div>
          </Reveal>
        ))}
      </div>

      <Reveal delay={120}>
        <div className="glass-panel rounded-xl p-4 flex items-center justify-between">
          <span className="text-sm text-text-muted">Subtotal</span>
          <span className="font-mono-tabular text-lg font-medium text-accent-cyan">{formatPrice(subtotal)}</span>
        </div>
      </Reveal>

      <Reveal delay={180}>
        <div className="flex justify-end">
          <Link href="/checkout" className="btn-primary rounded-lg px-5 py-2.5 text-sm">
            Proceed to checkout
          </Link>
        </div>
      </Reveal>
    </main>
  );
}
