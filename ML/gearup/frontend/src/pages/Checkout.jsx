import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, cartChanged, peso } from "../api.js";

const PAYMENT_OPTIONS = [
  {
    value: "cod",
    title: "Cash on delivery",
    description: "Pay the courier when your order arrives.",
  },
  {
    value: "paymongo",
    title: "Card / GCash / Maya (PayMongo)",
    description: "Secure checkout via PayMongo test mode.",
  },
];

export default function Checkout() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [cart, setCart] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    payment_method: "cod",
    shipping_name: "",
    shipping_phone: "",
    shipping_address: "",
    shipping_city: "",
    shipping_postal_code: "",
    notes: "",
  });

  useEffect(() => {
    api("/cart/")
      .then(setCart)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (searchParams.get("canceled")) {
      setError("Payment was canceled — your order is still pending if it was created.");
    }
  }, [searchParams]);

  const update = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const data = await api("/checkout/", { method: "POST", body: form });
      cartChanged();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }
      navigate(`/orders/${data.order_number}?success=1`);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  if (!cart) {
    return <div className="mx-auto max-w-3xl px-4 py-20 text-center text-slate-400">Loading…</div>;
  }
  if (!cart.items?.length) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center text-slate-400">
        Your cart is empty — <a href="/products" className="text-emerald-400">browse products</a> first.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold">Checkout</h1>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <form onSubmit={submit} className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-5 lg:col-span-3">
          <h2 className="font-semibold">Shipping details</h2>
          {[
            ["shipping_name", "Full name", "Juan dela Cruz", true],
            ["shipping_phone", "Phone", "0917 123 4567", true],
            ["shipping_address", "Address", "123 Rizal Street, Barangay", true],
            ["shipping_city", "City", "Quezon City", true],
            ["shipping_postal_code", "Postal code", "1100", true],
            ["notes", "Delivery notes (optional)", "Leave at the guardhouse", false],
          ].map(([key, label, placeholder, required]) => (
            <div key={key}>
              <label className="mb-1 block text-sm text-slate-300" htmlFor={key}>
                {label}
              </label>
              <input
                id={key}
                value={form[key]}
                onChange={update(key)}
                placeholder={placeholder}
                required={required}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none placeholder-slate-600 focus:border-emerald-500"
              />
            </div>
          ))}

          <div>
            <h2 className="mb-2 font-semibold">Payment method</h2>
            <div className="space-y-2">
              {PAYMENT_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${
                    form.payment_method === option.value
                      ? "border-emerald-500 bg-emerald-500/5"
                      : "border-slate-700 hover:border-slate-500"
                  }`}
                >
                  <input
                    type="radio"
                    name="payment_method"
                    value={option.value}
                    checked={form.payment_method === option.value}
                    onChange={update("payment_method")}
                    className="mt-1 accent-emerald-500"
                  />
                  <span>
                    <span className="block text-sm font-medium">{option.title}</span>
                    <span className="block text-xs text-slate-500">{option.description}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>

          {error && (
            <p className="rounded-lg border border-rose-900 bg-rose-950/60 px-3 py-2 text-sm text-rose-300">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-emerald-500 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-40"
          >
            {submitting ? "Placing order…" : `Place order · ${peso(cart.total)}`}
          </button>
        </form>

        <aside className="h-fit rounded-2xl border border-slate-800 bg-slate-900 p-5 lg:col-span-2">
          <h2 className="font-semibold">Order summary</h2>
          <div className="mt-3 space-y-2">
            {cart.items.map((item) => (
              <div key={item.id} className="flex justify-between gap-3 text-sm">
                <span className="truncate text-slate-300">
                  {item.quantity}× {item.product_name}
                  {item.variant_label ? ` (${item.variant_label})` : ""}
                </span>
                <span className="whitespace-nowrap">{peso(item.line_total)}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 border-t border-slate-800 pt-3 text-sm text-slate-400">
            <div className="flex justify-between">
              <span>Shipping</span>
              <span>{peso(cart.shipping_fee)}</span>
            </div>
          </div>
          <div className="mt-2 flex justify-between font-bold">
            <span>Total</span>
            <span className="text-emerald-400">{peso(cart.total)}</span>
          </div>
        </aside>
      </div>
    </div>
  );
}
