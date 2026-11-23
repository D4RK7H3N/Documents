"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useToasts } from "@/lib/toast-context";

export interface AdminProductRow {
  id: string;
  name: string;
  price: number;
  salePrice: number | null;
  stock: number;
  categoryName: string | null;
}

const LOW_STOCK_THRESHOLD = 10;

export default function AdminProductsTable({
  products,
  lowStockOnly,
}: {
  products: AdminProductRow[];
  lowStockOnly: boolean;
}) {
  const router = useRouter();
  const { success, error } = useToasts();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [stockInput, setStockInput] = useState("");
  const [showStock, setShowStock] = useState(false);

  function toggle(id: string) {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((s) => (s.size === products.length ? new Set() : new Set(products.map((p) => p.id))));
  }

  async function removeOne(p: AdminProductRow) {
    if (!window.confirm(`Delete "${p.name}"? This cannot be undone.`)) return;
    setBusy(true);
    const res = await fetch(`/api/products/${p.id}`, { method: "DELETE" });
    setBusy(false);
    if (res.ok) {
      success(`Deleted "${p.name}"`);
      router.refresh();
    } else {
      const data = await res.json().catch(() => null);
      error(data?.error ?? "Could not delete product");
    }
  }

  async function bulkDelete() {
    if (!window.confirm(`Delete ${selected.size} selected product(s)? This cannot be undone.`)) return;
    setBusy(true);
    const res = await fetch("/api/admin/products/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "delete", ids: [...selected] }),
    });
    setBusy(false);
    if (res.ok) {
      success(`Deleted ${selected.size} product(s)`);
      setSelected(new Set());
      router.refresh();
    } else {
      const data = await res.json().catch(() => null);
      error(data?.error ?? "Could not delete selected products");
    }
  }

  async function bulkSetStock() {
    const stock = parseInt(stockInput, 10);
    if (!Number.isFinite(stock) || stock < 0) return;
    setBusy(true);
    const res = await fetch("/api/admin/products/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "setStock", ids: [...selected], stock }),
    });
    setBusy(false);
    if (res.ok) {
      success(`Set stock to ${stock} on ${selected.size} product(s)`);
      setSelected(new Set());
      setStockInput("");
      setShowStock(false);
      router.refresh();
    } else {
      const data = await res.json().catch(() => null);
      error(data?.error ?? "Could not update stock");
    }
  }

  const effective = lowStockOnly
    ? products.filter((p) => p.stock <= LOW_STOCK_THRESHOLD)
    : products;

  return (
    <div className="flex flex-col gap-3">
      {selected.size > 0 && (
        <div className="glass-panel rounded-xl p-3 flex flex-wrap items-center gap-3">
          <span className="text-sm font-semibold">
            {selected.size} selected
          </span>
          <button
            onClick={bulkDelete}
            disabled={busy}
            className="rounded-lg px-3 py-1.5 text-sm text-danger border border-danger/30 hover:bg-danger/10 transition-colors press-down disabled:opacity-50"
          >
            Delete selected
          </button>
          <button
            onClick={() => setShowStock((s) => !s)}
            disabled={busy}
            className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors press-down disabled:opacity-50"
          >
            Set stock
          </button>
          {showStock && (
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                value={stockInput}
                onChange={(e) => setStockInput(e.target.value)}
                placeholder="New stock"
                className="input-field rounded-lg px-3 py-1.5 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
              />
              <button
                onClick={bulkSetStock}
                disabled={busy || !stockInput}
                className="btn-primary rounded-lg px-3 py-1.5 text-sm press-down disabled:opacity-50"
              >
                Apply
              </button>
            </div>
          )}
          <button
            onClick={() => setSelected(new Set())}
            className="ml-auto text-sm text-text-muted hover:text-text transition-colors"
          >
            Clear
          </button>
        </div>
      )}

      {effective.length === 0 ? (
        <p className="text-text-muted">
          {lowStockOnly ? "No low-stock products." : "No products yet."}
        </p>
      ) : (
        <div className="glass-panel rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-muted border-b border-border">
                <th className="p-3 font-medium w-10">
                  <input
                    type="checkbox"
                    aria-label="Select all"
                    checked={selected.size === effective.length && effective.length > 0}
                    onChange={toggleAll}
                    className="accent-accent-cyan"
                  />
                </th>
                <th className="p-3 font-medium">Name</th>
                <th className="p-3 font-medium">Price</th>
                <th className="p-3 font-medium">Stock</th>
                <th className="p-3 font-medium">Category</th>
                <th className="p-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {effective.map((p) => {
                const onSale = p.salePrice != null;
                return (
                  <tr
                    key={p.id}
                    className={`border-b border-border last:border-b-0 ${
                      p.stock <= LOW_STOCK_THRESHOLD ? "bg-danger/5" : ""
                    }`}
                  >
                    <td className="p-3">
                      <input
                        type="checkbox"
                        aria-label={`Select ${p.name}`}
                        checked={selected.has(p.id)}
                        onChange={() => toggle(p.id)}
                        className="accent-accent-cyan"
                      />
                    </td>
                    <td className="p-3 font-semibold">{p.name}</td>
                    <td className="p-3 font-mono-tabular">
                      {onSale && (
                        <>
                          <span className="text-accent-pink">
                            ${(p.salePrice! / 100).toFixed(2)}
                          </span>{" "}
                          <span className="line-through text-text-muted">
                            ${(p.price / 100).toFixed(2)}
                          </span>
                        </>
                      )}
                      {!onSale && <span>${(p.price / 100).toFixed(2)}</span>}
                    </td>
                    <td className="p-3">
                      <span
                        className={
                          p.stock === 0
                            ? "text-danger font-semibold"
                            : p.stock <= LOW_STOCK_THRESHOLD
                              ? "text-amber-500 font-semibold"
                              : "text-text-muted"
                        }
                      >
                        {p.stock}
                        {p.stock === 0 && " · OUT"}
                        {p.stock > 0 && p.stock <= LOW_STOCK_THRESHOLD && " · LOW"}
                      </span>
                    </td>
                    <td className="p-3 text-text-muted">{p.categoryName ?? "—"}</td>
                    <td className="p-3 flex justify-end gap-2">
                      <Link
                        href={`/admin/products/${p.id}/edit`}
                        className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors"
                      >
                        Edit
                      </Link>
                      <button
                        onClick={() => removeOne(p)}
                        disabled={busy}
                        className="rounded-lg px-3 py-1.5 text-sm text-danger border border-danger/30 hover:bg-danger/10 transition-colors press-down disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
