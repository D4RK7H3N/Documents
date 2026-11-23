"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useCompare } from "@/lib/compare-context";
import { useToasts } from "@/lib/toast-context";

interface CompareProduct {
  id: string;
  name: string;
  description: string;
  price: number;
  imageUrl: string | null;
  stock: number;
}

export default function CompareBar() {
  const { ids, remove, clear, max } = useCompare();
  const { info } = useToasts();
  const [products, setProducts] = useState<CompareProduct[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (ids.length === 0) return;
    fetch(`/api/products?ids=${encodeURIComponent(ids.join(","))}`)
      .then((res) => res.json())
      .then((data) => setProducts(data.products ?? []))
      .catch(() => setProducts([]));
  }, [ids]);

  if (ids.length === 0) return null;

  const rows = products.filter((p) => ids.includes(p.id));

  return (
    <>
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[90] glass-bar rounded-xl border border-border/60 shadow-lg anim-bar-up">
        <div className="flex items-center gap-3 px-4 py-2.5">
          <span className="font-display font-semibold tracking-widest text-xs text-text-muted">
            COMPARE ({rows.length}/{max})
          </span>
          <div className="flex items-center gap-2">
            {rows.map((p) => (
              <div key={p.id} className="relative group">
                {p.imageUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={p.imageUrl}
                    alt={p.name}
                    className="w-9 h-9 rounded-md object-cover border border-border"
                  />
                ) : (
                  <span className="w-9 h-9 rounded-md bg-surface-hover border border-border block" />
                )}
                <button
                  onClick={() => remove(p.id)}
                  aria-label={`Remove ${p.name} from compare`}
                  className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-danger text-white text-[10px] leading-none flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  ✕
                </button>
              </div>
            ))}
            {rows.length < ids.length &&
              ids
                .filter((id) => !rows.some((r) => r.id === id))
                .map((id) => <span key={id} className="w-9 h-9 rounded-md bg-surface-hover/60 border border-border/50" />)}
          </div>
          <button
            onClick={() => setOpen(true)}
            disabled={rows.length < 2}
            className="btn-primary rounded-lg px-3 py-1.5 text-sm disabled:opacity-40"
          >
            Compare
          </button>
          <button
            onClick={() => {
              clear();
              info("Compare list cleared");
            }}
            className="text-xs text-text-muted hover:text-text transition-colors press-down"
          >
            Clear
          </button>
        </div>
      </div>

      {open && (
        <>
          <div
            className="fixed inset-0 z-[95] bg-black/70 anim-backdrop-in"
            onClick={() => setOpen(false)}
          />
          <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[96] w-[min(92vw,860px)] max-h-[85vh] glass-panel rounded-xl p-6 flex flex-col gap-4 overflow-auto anim-modal-in">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-xl font-bold">COMPARE</h2>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close compare"
                className="text-text-muted hover:text-text transition-colors press-down"
              >
                ✕
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[560px]">
                <thead>
                  <tr>
                    <th className="text-left text-text-muted font-medium p-2 w-32" />
                    {rows.map((p) => (
                      <th key={p.id} className="p-2 font-semibold">
                        <Link
                          href={`/products/${p.id}`}
                          onClick={() => setOpen(false)}
                          className="hover:text-accent-cyan transition-colors"
                        >
                          {p.name}
                        </Link>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t border-border/60">
                    <td className="p-2 text-text-muted">Price</td>
                    {rows.map((p) => (
                      <td key={p.id} className="p-2 font-mono-tabular text-accent-cyan font-medium">
                        ${(p.price / 100).toFixed(2)}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-t border-border/60">
                    <td className="p-2 text-text-muted">Stock</td>
                    {rows.map((p) => (
                      <td key={p.id} className={`p-2 ${p.stock > 0 ? "text-success" : "text-danger"}`}>
                        {p.stock > 0 ? `${p.stock} available` : "Out of stock"}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-t border-border/60 align-top">
                    <td className="p-2 text-text-muted">Description</td>
                    {rows.map((p) => (
                      <td key={p.id} className="p-2 text-text-muted leading-relaxed">
                        {p.description}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}
