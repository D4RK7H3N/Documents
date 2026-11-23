"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export interface HeroSlide {
  id: string;
  name: string;
  count: number;
  slug: string | null;
}

const GRADIENTS = [
  "from-accent-cyan to-accent-purple",
  "from-accent-pink to-accent-purple",
  "from-accent-cyan to-accent-pink",
];

export default function HeroSlideshow({ slides }: { slides: HeroSlide[] }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused || slides.length <= 1) return;
    const t = setInterval(() => {
      setIndex((i) => (i + 1) % slides.length);
    }, 4000);
    return () => clearInterval(t);
  }, [paused, slides.length]);

  return (
    <section
      className="glass-panel rounded-2xl overflow-hidden relative"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      aria-roledescription="carousel"
      aria-label="Featured categories"
    >
      <div className="relative h-44 md:h-56">
        {slides.map((s, i) => (
          <div
            key={s.id}
            className={`absolute inset-0 flex flex-col justify-center gap-2 px-6 md:px-12 transition-opacity duration-500 ${
              i === index ? "opacity-100" : "opacity-0 pointer-events-none"
            }`}
            aria-hidden={i !== index}
          >
            <span className="font-mono-tabular text-xs tracking-[0.3em] uppercase text-text-muted">
              {s.count > 0
                ? `${s.count} product${s.count > 1 ? "s" : ""} on the grid`
                : "Fresh category"}
            </span>
            <h2
              className={`font-display text-4xl md:text-5xl font-bold bg-gradient-to-r ${
                GRADIENTS[i % GRADIENTS.length]
              } bg-clip-text text-transparent`}
            >
              {s.name}
            </h2>
<Link
              href={s.slug ? `/category/${s.slug}` : "/"}
              className="btn-primary rounded-lg px-4 py-2 text-sm self-start mt-2"
            >
              Shop now →
            </Link>
          </div>
        ))}
      </div>

      {slides.length > 1 && (
        <>
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2">
            {slides.map((s, i) => (
              <button
                key={s.id}
                onClick={() => setIndex(i)}
                aria-label={`Go to slide ${i + 1}`}
                className={`h-1.5 rounded-full transition-all ${
                  i === index ? "w-6 bg-accent-cyan" : "w-1.5 bg-text-muted/40 hover:bg-text-muted"
                }`}
              />
            ))}
          </div>
          <button
            onClick={() => setIndex((i) => (i - 1 + slides.length) % slides.length)}
            aria-label="Previous slide"
            className="absolute left-2 top-1/2 -translate-y-1/2 p-1.5 rounded-full btn-ghost text-text-muted hover:text-text transition-colors"
          >
            ←
          </button>
          <button
            onClick={() => setIndex((i) => (i + 1) % slides.length)}
            aria-label="Next slide"
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-full btn-ghost text-text-muted hover:text-text transition-colors"
          >
            →
          </button>
        </>
      )}
    </section>
  );
}