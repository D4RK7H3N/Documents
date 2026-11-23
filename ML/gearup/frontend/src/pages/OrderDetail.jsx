import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, peso } from "../api.js";
import { STATUS_STYLES } from "./Orders.jsx";

const TRACKING_STEPS = ["pending", "paid", "processing", "shipped", "delivered"];

export default function OrderDetail() {
  const { number } = useParams();
  const [searchParams] = useSearchParams();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/orders/${number}/`)
      .then(setOrder)
      .catch((err) => setError(err.message));
  }, [number]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center text-slate-400">{error}</div>
    );
  }
  if (!order) {
    return <div className="mx-auto max-w-3xl px-4 py-20 text-center text-slate-400">Loading order…</div>;
  }

  const cancelled = order.status === "cancelled";
  const currentIndex = TRACKING_STEPS.indexOf(order.status);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <p className="font-mono text-sm text-slate-500">{order.number}</p>
      <div className="mt-1 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">Order details</h1>
        <span
          className={`rounded-full border px-2.5 py-1 text-xs capitalize ${STATUS_STYLES[order.status] || ""}`}
        >
          {order.status}
        </span>
        <span className="text-xs text-slate-500">
          {order.payment_method === "cod" ? "Cash on delivery" : "PayMongo"} ·{" "}
          <span className="capitalize">{order.payment_status}</span>
        </span>
      </div>

      {searchParams.get("success") && (
        <p className="mt-4 rounded-xl border border-emerald-800 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-300">
          Order placed successfully. Thank you!
        </p>
      )}
      {searchParams.get("paid") && order.payment_status === "paid" && (
        <p className="mt-4 rounded-xl border border-emerald-800 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-300">
          Payment confirmed. Your order is being processed.
        </p>
      )}

      {!cancelled && currentIndex >= 0 && (
        <div className="mt-6 flex items-center rounded-2xl border border-slate-800 bg-slate-900 p-4">
          {TRACKING_STEPS.map((step, index) => (
            <div key={step} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center">
                <span
                  className={`flex h-7 w-7 items-center justify-center rounded-full border text-xs font-bold ${
                    index < currentIndex
                      ? "border-emerald-500 bg-emerald-500 text-slate-950"
                      : index === currentIndex
                        ? "border-emerald-400 text-emerald-300"
                        : "border-slate-700 text-slate-600"
                  }`}
                >
                  {index < currentIndex ? "✓" : index + 1}
                </span>
                <span className="mt-1 hidden text-[10px] capitalize text-slate-500 sm:block">
                  {step}
                </span>
              </div>
              {index < TRACKING_STEPS.length - 1 && (
                <div
                  className={`mx-1 h-0.5 flex-1 ${index < currentIndex ? "bg-emerald-500" : "bg-slate-800"}`}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {cancelled && (
        <p className="mt-4 rounded-xl border border-rose-900 bg-rose-950/50 px-4 py-3 text-sm text-rose-300">
          This order was cancelled.
        </p>
      )}

      <div className="mt-6 space-y-3">
        {order.items.map((item) => (
          <div key={item.id} className="flex items-center gap-4 rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <div className="h-14 w-14 shrink-0 overflow-hidden rounded-xl bg-slate-800">
              {item.image && <img src={item.image} alt={item.product_name} className="h-full w-full object-cover" />}
            </div>
            <div className="min-w-0 flex-1">
              <Link to={`/products/${item.product_slug}`} className="text-sm font-medium hover:text-emerald-400">
                {item.product_name}
              </Link>
              {item.variant_label && <p className="text-xs text-slate-500">{item.variant_label}</p>}
              <p className="text-xs text-slate-500">
                {item.quantity} × {peso(item.unit_price)}
              </p>
            </div>
            <p className="font-semibold">{peso(item.line_total)}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 text-sm">
          <h2 className="mb-2 font-semibold">Shipping to</h2>
          <p className="text-slate-300">{order.shipping_name}</p>
          <p className="text-slate-400">{order.shipping_phone}</p>
          <p className="text-slate-400">
            {order.shipping_address}, {order.shipping_city} {order.shipping_postal_code}
          </p>
          {order.notes && <p className="mt-2 text-xs text-slate-500">Note: {order.notes}</p>}
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 text-sm">
          <h2 className="mb-2 font-semibold">Payment summary</h2>
          <div className="flex justify-between text-slate-400">
            <span>Subtotal</span>
            <span>{peso(order.subtotal)}</span>
          </div>
          <div className="mt-1 flex justify-between text-slate-400">
            <span>Shipping fee</span>
            <span>{peso(order.shipping_fee)}</span>
          </div>
          <div className="mt-2 flex justify-between border-t border-slate-800 pt-2 font-bold">
            <span>Total</span>
            <span className="text-emerald-400">{peso(order.total)}</span>
          </div>
        </div>
      </div>

      <Link to="/orders" className="mt-6 inline-block text-sm text-emerald-400 hover:underline">
        Back to all orders
      </Link>
    </div>
  );
}
