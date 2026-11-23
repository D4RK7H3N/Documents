"use client";

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import { effectivePrice } from "@/lib/pricing";

export interface CartProduct {
  id: string;
  name: string;
  price: number;
  salePrice: number | null;
  saleEndsAt: string | null;
  imageUrl: string | null;
  stock: number;
}

export interface CartItem {
  id: string;
  productId: string;
  quantity: number;
  product: CartProduct;
}

interface CartContextValue {
  items: CartItem[];
  itemCount: number;
  subtotal: number;
  loading: boolean;
  loggedIn: boolean;
  addItem: (productId: string, quantity?: number) => Promise<{ ok: boolean; error?: string }>;
  refresh: () => Promise<void>;
  logout: () => void;
  justAddedId: string | null;
  wishlist: string[];
  toggleWishlist: (productId: string) => Promise<{ ok: boolean; error?: string }>;
}

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loggedIn, setLoggedIn] = useState(false);
  const [justAddedId, setJustAddedId] = useState<string | null>(null);
  const [wishlist, setWishlist] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/cart");
      if (res.status === 401) {
        setLoggedIn(false);
        setItems([]);
        setWishlist([]);
        return;
      }
      const data = await res.json();
      if (!data.cart) {
        setLoggedIn(false);
        setItems([]);
        setWishlist([]);
        return;
      }
      setLoggedIn(true);
      setItems(data.cart?.items ?? []);
      const wishRes = await fetch("/api/wishlist");
      if (wishRes.ok) {
        const wishData = await wishRes.json();
        setWishlist(wishData.ids ?? []);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);

  const addItem = useCallback(
    async (productId: string, quantity = 1) => {
      const res = await fetch("/api/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ productId, quantity }),
      });

      if (res.status === 401) {
        return { ok: false, error: "Log in to add items to your cart" };
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        return { ok: false, error: data.error ?? "Couldn't add to cart" };
      }

      setJustAddedId(productId);
      setTimeout(() => setJustAddedId((cur) => (cur === productId ? null : cur)), 1200);

      await refresh();
      return { ok: true };
    },
    [refresh]
  );

  const itemCount = items.reduce((sum, i) => sum + i.quantity, 0);
  const subtotal = items.reduce(
    (sum, i) =>
      sum + effectivePrice(i.product) * i.quantity,
    0,
  );

  const toggleWishlist = useCallback(async (productId: string) => {
    const shouldAdd = !wishlist.includes(productId);
    setWishlist((w) =>
      shouldAdd ? [...w, productId] : w.filter((id) => id !== productId),
    );

    const res = await fetch("/api/wishlist", {
      method: shouldAdd ? "POST" : "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ productId }),
    });

    if (!res.ok) {
      setWishlist((w) =>
        shouldAdd ? w.filter((id) => id !== productId) : [...w, productId],
      );
      if (res.status === 401) {
        return { ok: false, error: "Log in to save products" };
      }
      const data = await res.json().catch(() => ({}));
      return { ok: false, error: data.error ?? "Couldn't update wishlist" };
    }

    return { ok: true };
  }, [wishlist]);

  const logout = useCallback(() => {
    setItems([]);
    setLoggedIn(false);
    setWishlist([]);
  }, []);

  return (
    <CartContext.Provider
      value={{
        items,
        itemCount,
        subtotal,
        loading,
        loggedIn,
        addItem,
        refresh,
        logout,
        justAddedId,
        wishlist,
        toggleWishlist,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within a CartProvider");
  return ctx;
}
