"use client";

import { useState } from "react";
import { useCart } from "@/lib/cart-context";
import { useToasts } from "@/lib/toast-context";
import { flyToCart } from "@/lib/fly-to-cart";

export default function ProductBuyPanel({
  productId,
  stock,
  imageUrl = null,
}: {
  productId: string;
  stock: number;
  imageUrl?: string | null;
}) {
  const { addItem, justAddedId } = useCart();
  const { error } = useToasts();
  const [qty, setQty] = useState(1);
  const [adding, setAdding] = useState(false);

  const outOfStock = stock === 0;
  const justAdded = justAddedId === productId;

  async function handleAdd(rect: DOMRect) {
    setAdding(true);
    const res = await addItem(productId, qty);
    setAdding(false);
    if (!res.ok) error(res.error ?? "Couldn't add to cart");
    else flyToCart(rect, imageUrl);
  }

  if (outOfStock) {
    return (
      <div>
        <span className="text-sm text-danger font-semibold">Out of stock</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
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
            onClick={() => setQty((n) => Math.min(stock, n + 1))}
            disabled={qty >= stock}
            className="px-3 py-2 text-text-muted hover:text-text hover:bg-surface-hover transition-colors disabled:opacity-40 press-down"
            aria-label="Increase quantity"
          >
            +
          </button>
        </div>

        {justAdded ? (
          <span className="text-sm font-semibold text-success">Added ✓</span>
        ) : (
          <button
            onClick={(e) => handleAdd(e.currentTarget.getBoundingClientRect())}
            disabled={adding}
            className="btn-primary rounded-lg px-5 py-2 text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {adding ? "Adding..." : "Add to cart"}
          </button>
        )}
      </div>
    </div>
  );
}
