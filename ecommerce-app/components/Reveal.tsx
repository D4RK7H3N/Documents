"use client";

import { useEffect, useRef, useState, ReactNode } from "react";

type Variant = "fade-up" | "fade-in" | "zoom-in" | "slide-left" | "slide-right";

export default function Reveal({
  children,
  variant = "fade-up",
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  variant?: Variant;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (typeof IntersectionObserver === "undefined") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setVisible(true);
      return;
    }

    if (el.getBoundingClientRect().top < window.innerHeight) {
      setVisible(true);
      return;
    }

    let io: IntersectionObserver | null = null;
    const makeVisible = () => {
      setVisible(true);
      io?.disconnect();
    };

    io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) makeVisible();
        }
      },
      { threshold: 0.05, rootMargin: "0px 0px -40px 0px" },
    );
    io.observe(el);

    const t = setTimeout(makeVisible, 2000);

    return () => {
      io?.disconnect();
      clearTimeout(t);
    };
  }, []);

  return (
    <div
      ref={ref}
      className={`reveal reveal--${variant} ${visible ? "is-visible" : ""} ${className}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}