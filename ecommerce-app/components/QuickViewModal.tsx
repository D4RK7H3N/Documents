"use client";

import { useState } from "react";
import Link from "next/link";
import { useCart } from "@/lib/cart-context";
import { useToasts } from "@/lib/toast-context";
import { isOnSale, effectivePrice, salePercent } from "@/lib/pricing";
import WishlistButton from "@/components/WishlistButton";
import CompareButton from "@/components/CompareButton";
import { flyToCart } from "@/lib/fly-to-cart";

interface QuickViewProduct {
  id: string;
  name: string;
  description: string;
  price: number;
  salePrice: number | null;
  saleEndsAt: string | null;
  imageUrl: string | null;
  stock: number;
}

export default function QuickViewModal({
  product,
  onClose,
}: {
  product: QuickViewProduct;
  onClose: () => void;
}) {
  const { addItem } = useCart();
  const { success, error } = useToasts();
  const [qty, setQty] = useState(1);
  const [adding, setAdding] = useState(false);

  const outOfStock = product.stock === 0;
  const onSale = isOnSale(product);
  const pct = salePercent(product);

  async function handleAdd(rect: DOMRect) {
    setAdding(true);
    const res = await addItem(product.id, qty);
    setAdding(false);
    if (!res.ok) error(res.error ?? "Couldn't add to cart");
    else {
      success(`${product.name} added to cart`);
      flyToCart(rect, product.imageUrl);
      onClose();
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-[95] bg-black/70 anim-backdrop-in" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Quick view of ${product.name}`}
        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[96] w-[min(92vw,760px)] max-h-[88vh] glass-panel rounded-xl p-6 flex flex-col gap-5 overflow-auto anim-modal-in"
      >
        <div className="flex items-center justify-between">
          <span className="font-display font-semibold tracking-widest text-xs text-text-muted">
            QUICK VIEW
          </span>
          <button
            onClick={onClose}
            aria-label="Close quick view"
            className="text-text-muted hover:text-text transition-colors press-down"
          >
            ✕
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="aspect-square rounded-xl overflow-hidden border border-border">
            {product.imageUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={product.imageUrl}
                alt={product.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div
                className="w-full h-full"
                style={{
                  background:
                    "radial-gradient(circle at 30% 25%, var(--accent-purple) 0%, transparent 55%), radial-gradient(circle at 70% 60%, var(--accent-pink) 0%, transparent 55%), radial-gradient(circle at 45% 85%, var(--accent-cyan) 0%, transparent 55%), var(--surface)",
                }}
              />
            )}
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-display text-xl font-bold leading-tight">{product.name}</h2>
              <div className="flex gap-2 shrink-0">
                <WishlistButton productId={product.id} />
                <CompareButton productId={product.id} />
              </div>
            </div>

            <div className="flex items-baseline gap-2">
              <p className="font-mono-tabular text-xl font-medium text-accent-cyan">
                ${(effectivePrice(product) / 100).toFixed(2)}
              </p>
              {onSale && (
                <p className="font-mono-tabular text-sm text-text-muted line-through">
                  ${(product.price / 100).toFixed(2)}
                </p>
              )}
              {onSale && pct !== null && (
                <p className="text-xs font-bold text-accent-pink">-{pct}%</p>
              )}
            </div>

            <p className={product.stock > 0 ? "text-sm text-success" : "text-sm text-danger"}>
              {product.stock > 0
                ? `In stock (${product.stock} available)`
                : "Out of stock"}
            </p>

            <p className="text-sm text-text-muted leading-relaxed line-clamp-4">
              {product.description}
            </p>

            {!outOfStock && (
              <div className="flex items-center gap-3 pt-1">
                <div className="flex items-center border border-border rounded-lg overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setQty((n) => Math.max(1, n - 1))}
                    disabled={qty <= 1}
                    className="px-3 py-2 text-text-muted hover:text-text hover:bg-surface-hover transition-colors disabled:opacity-40 press-down"
                    aria-label="Decrease quantity"
                  >
                    −
                  </button>
                  <span className="font-mono-tabular w-10 text-center text-sm">{qty}</span>
                  <button
                    type="button"
                    onClick={() => setQty((n) => Math.min(product.stock, n + 1))}
                    disabled={qty >= product.stock}
                    className="px-3 py-2 text-text-muted hover:text-text hover:bg-surface-hover transition-colors disabled:opacity-40 press-down"
                    aria-label="Increase quantity"
                  >
                    +
                  </button>
                </div>
                <button
                  onClick={(e) => handleAdd(e.currentTarget.getBoundingClientRect())}
                  disabled={adding}
                  className="btn-primary rounded-lg px-5 py-2 text-sm disabled:opacity-50"
                >
                  {adding ? "Adding..." : "Add to cart"}
                </button>
              </div>
            )}

            <Link
              href={`/products/${product.id}`}
              onClick={onClose}
              className="text-sm text-text-muted hover:text-text underline underline-offset-4 transition-colors"
            >
              View full details →
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
