"use client";

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";

const MAX_COMPARE = 4;
const STORAGE_KEY = "compare-ids";

interface CompareContextValue {
  ids: string[];
  max: number;
  isComparing: (productId: string) => boolean;
  toggle: (productId: string) => { ok: boolean; reason?: "limit" };
  remove: (productId: string) => void;
  clear: () => void;
}

const CompareContext = createContext<CompareContextValue | null>(null);

export function CompareProvider({ children }: { children: ReactNode }) {
  const [ids, setIds] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    } catch {
      // storage unavailable — ignore
    }
  }, [ids]);

  const isComparing = useCallback((productId: string) => ids.includes(productId), [ids]);

  const toggle = useCallback(
    (productId: string) => {
      let outcome: { ok: boolean; reason?: "limit" } = { ok: true };
      setIds((cur) => {
        if (cur.includes(productId)) return cur.filter((id) => id !== productId);
        if (cur.length >= MAX_COMPARE) {
          outcome = { ok: false, reason: "limit" };
          return cur;
        }
        return [...cur, productId];
      });
      return outcome;
    },
    [],
  );

  const remove = useCallback((productId: string) => {
    setIds((cur) => cur.filter((id) => id !== productId));
  }, []);

  const clear = useCallback(() => setIds([]), []);

  return (
    <CompareContext.Provider value={{ ids, max: MAX_COMPARE, isComparing, toggle, remove, clear }}>
      {children}
    </CompareContext.Provider>
  );
}

export function useCompare() {
  const ctx = useContext(CompareContext);
  if (!ctx) throw new Error("useCompare must be used within a CompareProvider");
  return ctx;
}
