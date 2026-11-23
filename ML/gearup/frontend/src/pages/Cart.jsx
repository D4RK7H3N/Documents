import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, cartChanged, peso } from "../api.js";

export default function Cart() {
  const [cart, setCart] = useState(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const navigate = useNavigate();

  const load = async () => {
    try {
      setCart(await api("/cart/"));
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const setQuantity = async (item, quantity) => {
    setBusyId(item.id);
    try {
      await api(`/cart/items/${item.id}/`, { method: "PATCH", body: { quantity } });
      cartChanged();
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const removeItem = async (item) => {
    setBusyId(item.id);
    try {
      await api(`/cart/items/${item.id}/`, { method: "DELETE" });
      cartChanged();
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  if (!cart && !error) {
    return <div className="mx-auto max-w-3xl px-4 py-20 text-center text-slate-400">Loading cart…</div>;
  }

  if (!cart?.items?.length) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center">
        <p className="text-lg font-semibold">Your cart is empty</p>
        <p className="mt-2 text-sm text-slate-400">Time to upgrade the battle station.</p>
        <Link
          to="/products"
          className="mt-6 inline-block rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
        >
          Browse products
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold">Your cart</h1>
      {error && (
        <p className="mt-4 rounded-lg border border-rose-900 bg-rose-950/60 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      )}

      <div className="mt-6 space-y-3">
        {cart.items.map((item) => (
          <div
            key={item.id}
            className="flex flex-wrap items-center gap-4 rounded-2xl border border-slate-800 bg-slate-900 p-4"
          >
            <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-slate-800">
              {item.image && (
                <img src={item.image} alt={item.product_name} className="h-full w-full object-cover" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <Link to={`/products/${item.product_slug}`} className="font-medium hover:text-emerald-400">
                {item.product_name}
              </Link>
              {item.variant_label && (
                <p className="text-xs text-slate-500">{item.variant_label}</p>
              )}
              <p className="text-sm text-slate-400">{peso(item.unit_price)} each</p>
            </div>
            <div className="flex items-center rounded-xl border border-slate-700">
              <button
                type="button"
                disabled={busyId === item.id || item.quantity <= 1}
                onClick={() => setQuantity(item, item.quantity - 1)}
                className="px-3 py-1.5 text-slate-300 hover:text-white disabled:opacity-30"
                aria-label="Decrease quantity"
              >
                −
              </button>
              <span className="w-8 text-center text-sm">{item.quantity}</span>
              <button
                type="button"
                disabled={busyId === item.id}
                onClick={() => setQuantity(item, item.quantity + 1)}
                className="px-3 py-1.5 text-slate-300 hover:text-white disabled:opacity-30"
                aria-label="Increase quantity"
              >
                +
              </button>
            </div>
            <p className="w-24 text-right font-semibold">{peso(item.line_total)}</p>
            <button
              type="button"
              disabled={busyId === item.id}
              onClick={() => removeItem(item)}
              className="text-sm text-rose-400 transition hover:text-rose-300 disabled:opacity-30"
            >
              Remove
            </button>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-5">
        <div className="flex justify-between text-sm text-slate-400">
          <span>Subtotal</span>
          <span>{peso(cart.subtotal)}</span>
        </div>
        <div className="mt-1 flex justify-between text-sm text-slate-400">
          <span>Shipping fee</span>
          <span>{peso(cart.shipping_fee)}</span>
        </div>
        <div className="mt-3 flex justify-between border-t border-slate-800 pt-3 font-bold">
          <span>Total</span>
          <span className="text-emerald-400">{peso(cart.total)}</span>
        </div>
        <button
          type="button"
          onClick={() => navigate("/checkout")}
          className="mt-4 w-full rounded-xl bg-emerald-500 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
        >
          Proceed to checkout
        </button>
      </div>
    </div>
  );
}
