"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface SearchResult {
  id: string;
  name: string;
  price: number;
  imageUrl: string | null;
}

export default function SearchBox({ className = "" }: { className?: string }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const blurTimer = useRef<number | null>(null);

  useEffect(() => {
    if (blurTimer.current) window.clearTimeout(blurTimer.current);
    const q = query.trim();
    if (!q) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setResults([]);
      setOpen(false);
      setLoading(false);
      return;
    }

    setLoading(true);
    const t = window.setTimeout(async () => {
      const res = await fetch(`/api/products?q=${encodeURIComponent(q)}&limit=6`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.products ?? []);
        setOpen(true);
      }
      setLoading(false);
    }, 250);

    return () => window.clearTimeout(t);
  }, [query]);

  function submit() {
    const q = query.trim();
    setOpen(false);
    router.push(q ? `/?q=${encodeURIComponent(q)}` : "/");
    router.refresh();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      submit();
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={boxRef} className={`relative ${className}`}>
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <input
          type="search"
          placeholder="Search products..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.trim() && setOpen(true)}
          onBlur={() => {
            blurTimer.current = window.setTimeout(() => setOpen(false), 150);
          }}
          onKeyDown={handleKeyDown}
          className="input-field rounded-lg px-3 py-1.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
        />
      </form>

      {loading && (
        <div className="absolute left-0 right-0 top-full mt-1.5">
          <div className="glass-panel rounded-xl px-4 py-3 text-sm text-text-muted">
            Searching…
          </div>
        </div>
      )}

      {open && !loading && results.length > 0 && (
        <div className="absolute left-0 right-0 top-full mt-1.5 z-50 glass-panel rounded-xl overflow-hidden">
          <ul className="flex flex-col max-h-80 overflow-y-auto">
            {results.map((p) => (
              <li key={p.id} className="border-b border-border/50 last:border-b-0">
                <Link
                  href={`/products/${p.id}`}
                  onClick={() => setOpen(false)}
                  onMouseDown={(e) => e.preventDefault()}
                  className="flex items-center gap-3 px-3 py-2 hover:bg-surface-hover transition-colors"
                >
                  {p.imageUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={p.imageUrl}
                      alt={p.name}
                      className="w-9 h-9 rounded-md object-cover shrink-0"
                    />
                  ) : (
                    <span className="w-9 h-9 rounded-md shrink-0 bg-surface-hover" />
                  )}
                  <span className="flex-1 text-sm truncate">{p.name}</span>
                  <span className="font-mono-tabular text-sm text-accent-cyan">
                    ${(p.price / 100).toFixed(2)}
                  </span>
                </Link>
              </li>
            ))}
            <li className="border-t border-border/60">
              <button
                onClick={submit}
                className="w-full px-3 py-2 text-sm text-text-muted hover:text-text hover:bg-surface-hover transition-colors text-center"
              >
                See all results for “{query.trim()}” →
              </button>
            </li>
          </ul>
        </div>
      )}

      {open && !loading && query.trim() && results.length === 0 && (
        <div className="absolute left-0 right-0 top-full mt-1.5 z-50 glass-panel rounded-xl px-4 py-3 text-sm text-text-muted">
          No matches.{" "}
          <button onClick={submit} className="text-accent-cyan hover:underline">
            See all results →
          </button>
        </div>
      )}
    </div>
  );
}
