"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";

interface FlyItem {
  id: number;
  x: number;
  y: number;
  image: string | null;
  target: { x: number; y: number };
}

function getCartTarget(): { x: number; y: number } | null {
  const els = document.querySelectorAll<HTMLElement>("[data-cart-target]");
  for (const el of els) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) {
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    }
  }
  return null;
}

export default function CartFlyLayer() {
  const [flies, setFlies] = useState<FlyItem[]>([]);

  useEffect(() => {
    function onFly(e: Event) {
      const d = (e as CustomEvent).detail as {
        x: number;
        y: number;
        image?: string | null;
      };
      const target = getCartTarget();
      if (!target) return;
      const id = Date.now() + Math.random();
      setFlies((f) => [...f, { id, x: d.x, y: d.y, image: d.image ?? null, target }]);
      window.setTimeout(
        () => setFlies((f) => f.filter((item) => item.id !== id)),
        850,
      );
    }
    window.addEventListener("fly-to-cart", onFly);
    return () => window.removeEventListener("fly-to-cart", onFly);
  }, []);

  if (flies.length === 0) return null;

  return (
    <div className="fixed inset-0 pointer-events-none z-[98]" aria-hidden="true">
      {flies.map((f) => {
        const dx = f.target.x - f.x;
        const dy = f.target.y - f.y;
        return (
          <motion.div
            key={f.id}
            className="absolute"
            initial={{ x: f.x, y: f.y, scale: 1, opacity: 1 }}
            animate={{
              x: [f.x, f.x + dx * 0.5, f.target.x],
              y: [f.y, f.y + dy - 140, f.target.y],
              scale: [1, 0.7, 0.25],
              opacity: [1, 1, 0.55],
            }}
            transition={{ duration: 0.75, times: [0, 0.55, 1], ease: "easeInOut" }}
          >
            <div className="-translate-x-1/2 -translate-y-1/2">
              {f.image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={f.image}
                  alt=""
                  className="w-10 h-10 rounded-md object-cover border border-accent-cyan/70 shadow-[0_0_18px_rgba(0,245,255,0.5)]"
                />
              ) : (
                <span className="block w-5 h-5 rounded-full bg-accent-pink shadow-[0_0_16px_rgba(255,41,117,0.85)]" />
              )}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
