"use client";

import { useState } from "react";
import Link from "next/link";
import { useCart } from "@/lib/cart-context";
import { useToasts } from "@/lib/toast-context";
import { isOnSale, effectivePrice, salePercent } from "@/lib/pricing";
import WishlistButton from "@/components/WishlistButton";
import CompareButton from "@/components/CompareButton";
import QuickViewModal from "@/components/QuickViewModal";
import { flyToCart } from "@/lib/fly-to-cart";

export interface ProductCardData {
  id: string;
  name: string;
  description: string;
  price: number;
  salePrice: number | null;
  saleEndsAt: string | null;
  imageUrl: string | null;
  stock: number;
}

export default function ProductCard({ product }: { product: ProductCardData }) {
  const { addItem, justAddedId } = useCart();
  const { success, error } = useToasts();
  const [adding, setAdding] = useState(false);
  const [quickView, setQuickView] = useState(false);

  const outOfStock = product.stock === 0;
  const justAdded = justAddedId === product.id;
  const onSale = isOnSale(product);
  const pct = salePercent(product);

  async function handleAdd(rect: DOMRect) {
    setAdding(true);
    const res = await addItem(product.id);
    setAdding(false);
    if (!res.ok) error(res.error ?? "Couldn't add to cart");
    else {
      success(`${product.name} added to cart`);
      flyToCart(rect, product.imageUrl);
    }
  }

  return (
    <div className="glow-card rounded-xl overflow-hidden flex flex-col">
      <div className="relative">
        <Link href={`/products/${product.id}`} className="block aspect-[4/3] overflow-hidden">
          {product.imageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={product.imageUrl} alt={product.name} className="w-full h-full object-cover transition-transform duration-300 hover:scale-105" />
          ) : (
            <div
              className="w-full h-full"
              style={{
                background:
                  "radial-gradient(circle at 30% 25%, var(--accent-purple) 0%, transparent 55%), radial-gradient(circle at 70% 60%, var(--accent-pink) 0%, transparent 55%), radial-gradient(circle at 45% 85%, var(--accent-cyan) 0%, transparent 55%), var(--surface)",
              }}
            />
          )}
        </Link>
        {onSale && pct !== null && (
          <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-accent-pink text-white text-[10px] font-bold tracking-wider">
            -{pct}%
          </span>
        )}
        <WishlistButton productId={product.id} compact />
        <div className="absolute bottom-2 right-2 flex gap-2">
          <CompareButton productId={product.id} compact />
          <button
            type="button"
            onClick={() => setQuickView(true)}
            aria-label={`Quick view ${product.name}`}
            className="p-2 rounded-lg border border-border text-text-muted hover:bg-surface-hover hover:text-text transition-colors press-down"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
        </div>
      </div>

      <div className="p-4 flex flex-col gap-2 flex-1">
        <Link href={`/products/${product.id}`}>
          <h2 className="font-display font-semibold text-lg hover:text-accent-cyan transition-colors">
            {product.name}
          </h2>
        </Link>
        <p className="text-sm text-text-muted line-clamp-2">{product.description}</p>

        <div className="mt-auto flex items-center justify-between pt-3">
          <div className="flex items-baseline gap-2">
            <span className="font-mono-tabular font-medium text-accent-cyan">
              ${(effectivePrice(product) / 100).toFixed(2)}
            </span>
            {onSale && (
              <span className="font-mono-tabular text-xs text-text-muted line-through">
                ${(product.price / 100).toFixed(2)}
              </span>
            )}
          </div>

          {outOfStock ? (
            <span className="btn-ghost rounded-lg px-3 py-1.5 text-sm opacity-50 cursor-not-allowed select-none">
              Out of stock
            </span>
          ) : justAdded ? (
            <span className="text-sm font-semibold text-success px-3 py-1.5">Added ✓</span>
          ) : (
            <button
              onClick={(e) => handleAdd(e.currentTarget.getBoundingClientRect())}
              disabled={adding}
              className="btn-primary rounded-lg px-3 py-1.5 text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {adding ? "Adding..." : "Add to cart"}
            </button>
          )}
        </div>
      </div>

      {quickView && <QuickViewModal product={product} onClose={() => setQuickView(false)} />}
    </div>
  );
}
