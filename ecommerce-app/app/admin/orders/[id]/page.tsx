"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import CancelOrderButton from "@/components/CancelOrderButton";
import InvoiceDownloadButton from "@/components/InvoiceDownloadButton";
import { useToasts } from "@/lib/toast-context";

interface OrderItem {
  id: string;
  quantity: number;
  price: number;
  product: { name: string; imageUrl: string | null };
}

interface OrderEvent {
  id: string;
  status: string;
  note: string | null;
  createdAt: string;
}

interface Order {
  id: string;
  status: string;
  trackingNumber: string | null;
  totalAmount: number;
  shippingAddr: string;
  user: { email: string };
  items: OrderItem[];
  events: OrderEvent[];
}

const STATUSES = ["PENDING", "PAID", "SHIPPED", "DELIVERED", "CANCELLED"] as const;

export default function AdminOrderEditPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { success, error } = useToasts();
  const [order, setOrder] = useState<Order | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [status, setStatus] = useState<string>("PENDING");
  const [trackingNumber, setTrackingNumber] = useState("");
  const [shippingAddr, setShippingAddr] = useState("");
  const [phone, setPhone] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch(`/api/orders/${params.id}`)
      .then((res) => {
        if (!res.ok) {
          setNotFound(true);
          return null;
        }
        return res.json();
      })
      .then((data) => {
        if (!data) return;
        setOrder(data.order);
        setStatus(data.order.status);
        setTrackingNumber(data.order.trackingNumber ?? "");
        setShippingAddr(data.order.shippingAddr ?? "");
        setPhone(data.order.phone ?? "");
      });
  }, [params.id]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);

    const res = await fetch(`/api/orders/${params.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status,
        trackingNumber: trackingNumber || undefined,
        note: note || undefined,
        shippingAddr: shippingAddr || undefined,
        phone: phone || undefined,
      }),
    });

    setSaving(false);

    if (!res.ok) {
      const data = await res.json();
      error(typeof data.error === "string" ? data.error : "Couldn't save changes");
      return;
    }

    success("Order updated");
    router.push("/admin/orders");
    router.refresh();
  }

  if (notFound) {
    return (
      <main className="max-w-3xl mx-auto p-6 mt-12">
        <p className="text-text-muted">Order not found.</p>
      </main>
    );
  }

  if (!order) {
    return (
      <main className="max-w-3xl mx-auto p-6 mt-12">
        <div className="h-64 glass-panel rounded-xl animate-pulse" />
      </main>
    );
  }

  return (
    <main className="max-w-3xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="font-mono-tabular font-medium text-accent-cyan text-2xl">
            #{order.id.slice(0, 8)}
          </span>
          <span className="text-sm text-text-muted">{order.user.email}</span>
        </div>
        <InvoiceDownloadButton orderId={order.id} />
      </div>

      <form onSubmit={handleSubmit} className="glass-panel rounded-xl p-6 flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label htmlFor="status" className="text-sm font-medium text-text-muted">
            Status
          </label>
          <select
            id="status"
            className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s} disabled={s === "CANCELLED" && order.status !== "CANCELLED"}>
                {s}
              </option>
            ))}
          </select>
          <p className="text-xs text-text-muted">
            Orders move PENDING → PAID → SHIPPED → DELIVERED. Use the cancel button for cancellations.
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="trackingNumber" className="text-sm font-medium text-text-muted">
            Tracking number
          </label>
          <input
            id="trackingNumber"
            type="text"
            placeholder="Required when shipping"
            className="input-field font-mono-tabular rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={trackingNumber}
            onChange={(e) => setTrackingNumber(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="shippingAddr" className="text-sm font-medium text-text-muted">
            Shipping address
          </label>
          <textarea
            id="shippingAddr"
            rows={3}
            className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={shippingAddr}
            onChange={(e) => setShippingAddr(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="phone" className="text-sm font-medium text-text-muted">
            Phone
          </label>
          <input
            id="phone"
            type="tel"
            className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="note" className="text-sm font-medium text-text-muted">
            Note (shown on the tracking timeline, optional)
          </label>
          <input
            id="note"
            type="text"
            placeholder="e.g. Handed to carrier"
            className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>

        <button type="submit" disabled={saving} className="btn-primary rounded-lg px-4 py-2.5 text-sm disabled:opacity-50">
          {saving ? "Saving..." : "Save changes"}
        </button>

        {(order.status === "PENDING" || order.status === "PAID") && (
          <CancelOrderButton orderId={order.id} />
        )}
      </form>

      <section className="glass-panel rounded-xl p-6 flex flex-col gap-4">
        <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
          ITEMS · {order.items.reduce((sum, i) => sum + i.quantity, 0)}
        </h2>
        <ul className="flex flex-col gap-3">
          {order.items.map((item) => (
            <li key={item.id} className="flex items-center justify-between gap-3 text-sm">
              <span className="truncate text-text-muted">
                {item.product.name} <span className="text-text-muted/70">×{item.quantity}</span>
              </span>
              <span className="font-mono-tabular shrink-0">${(item.price / 100).toFixed(2)}</span>
            </li>
          ))}
        </ul>
        <div className="border-t border-border pt-3 flex items-center justify-between">
          <span className="text-sm text-text-muted">Total</span>
          <span className="font-mono-tabular font-medium text-accent-cyan">
            ${(order.totalAmount / 100).toFixed(2)}
          </span>
        </div>
      </section>

      <section className="glass-panel rounded-xl p-6 flex flex-col gap-2">
        <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
          TRACKING TIMELINE
        </h2>
        <ul className="flex flex-col gap-2">
          {order.events.map((event) => (
            <li key={event.id} className="flex items-center justify-between gap-3 text-sm">
              <span className="text-text-muted">
                {event.status}
                {event.note ? ` — ${event.note}` : ""}
              </span>
              <span className="font-mono-tabular text-xs text-text-muted">
                {new Date(event.createdAt).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="glass-panel rounded-xl p-6 flex flex-col gap-2">
        <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
          SHIPPING ADDRESS
        </h2>
        <p className="text-sm text-text whitespace-pre-wrap">{order.shippingAddr}</p>
      </section>
    </main>
  );
}
