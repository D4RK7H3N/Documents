import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, peso } from "../api.js";

const STATUS_STYLES = {
  pending: "border-amber-500/30 bg-amber-500/15 text-amber-400",
  paid: "border-sky-500/30 bg-sky-500/15 text-sky-400",
  processing: "border-indigo-500/30 bg-indigo-500/15 text-indigo-300",
  shipped: "border-violet-500/30 bg-violet-500/15 text-violet-300",
  delivered: "border-emerald-500/30 bg-emerald-500/15 text-emerald-400",
  cancelled: "border-rose-500/30 bg-rose-500/15 text-rose-400",
};

export { STATUS_STYLES };

export default function Orders() {
  const [orders, setOrders] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/orders/")
      .then(setOrders)
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center text-slate-400">{error}</div>
    );
  }
  if (!orders) {
    return <div className="mx-auto max-w-3xl px-4 py-20 text-center text-slate-400">Loading orders…</div>;
  }
  if (!orders.length) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center">
        <p className="text-lg font-semibold">No orders yet</p>
        <Link
          to="/products"
          className="mt-4 inline-block rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
        >
          Start shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold">Your orders</h1>
      <div className="mt-6 space-y-3">
        {orders.map((order) => (
          <Link
            key={order.number}
            to={`/orders/${order.number}`}
            className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900 p-4 transition hover:border-slate-600"
          >
            <div>
              <p className="font-mono text-sm font-semibold">{order.number}</p>
              <p className="text-xs text-slate-500">
                {new Date(order.created_at).toLocaleString()} · {order.item_count} item(s)
              </p>
            </div>
            <span
              className={`ml-auto rounded-full border px-2.5 py-1 text-xs capitalize ${STATUS_STYLES[order.status] || ""}`}
            >
              {order.status}
            </span>
            <span className="font-bold text-emerald-400">{peso(order.total)}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
