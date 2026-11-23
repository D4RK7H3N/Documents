"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCart } from "@/lib/cart-context";
import NotificationBell from "@/components/NotificationBell";
import SearchBox from "@/components/SearchBox";

interface HeaderUser {
  name: string;
  email: string;
  role: "CUSTOMER" | "ADMIN";
}

export default function Header({ user }: { user: HeaderUser | null }) {
  const router = useRouter();
  const { itemCount, justAddedId, wishlist, logout: clearCart } = useCart();
  const [menuOpen, setMenuOpen] = useState(false);
  const [badgePulse, setBadgePulse] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const closeMenu = () => setMenuOpen(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 24);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  async function handleLogout() {
    setLoggingOut(true);
    await fetch("/api/auth/logout", { method: "POST" });
    clearCart();
    setLoggingOut(false);
    router.push("/");
    router.refresh();
  }

  useEffect(() => {
    if (!justAddedId) return;
    const t1 = setTimeout(() => setBadgePulse(true), 0);
    const t2 = setTimeout(() => setBadgePulse(false), 700);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [justAddedId]);

  return (
    <header
      className={`sticky top-0 z-50 glass-bar border-b border-border/60 header ${
        scrolled ? "header--scrolled" : ""
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 header-inner flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <svg viewBox="0 0 64 64" className="w-6 h-6" aria-hidden="true">
            <defs>
              <linearGradient id="bolt-g" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#00f5ff" />
                <stop offset="0.55" stopColor="#9d00ff" />
                <stop offset="1" stopColor="#ff2975" />
              </linearGradient>
            </defs>
            <rect x="2" y="2" width="60" height="60" rx="16" fill="#0b0618" />
            <rect
              x="2"
              y="2"
              width="60"
              height="60"
              rx="16"
              fill="none"
              stroke="url(#bolt-g)"
              strokeWidth="4"
            />
            <path d="M38 10 L14 36 h12 l-4 18 26-28 H35 l3-16z" fill="url(#bolt-g)" />
          </svg>
          <span className="font-display font-bold text-lg tracking-[0.2em] bg-gradient-to-r from-accent-cyan to-accent-pink bg-clip-text text-transparent">
            CLICKBOUND
          </span>
        </Link>

        <div className="hidden md:flex flex-1 justify-center px-4">
          <SearchBox className="w-full max-w-xs" />
        </div>

        <div className="flex items-center gap-5">
          <nav className="hidden md:flex items-center gap-5">
            {user ? (
              <>
                <span className="text-sm text-text-muted">{user.name}</span>
                <Link href="/orders" className="text-sm text-text-muted hover:text-text transition-colors">
                  Orders
                </Link>
                <Link href="/account" className="text-sm text-text-muted hover:text-text transition-colors">
                  Account
                </Link>
                {user.role === "ADMIN" && (
                  <Link href="/admin" className="text-sm text-text-muted hover:text-text transition-colors">
                    Admin
                  </Link>
                )}
                <button
                  onClick={handleLogout}
                  disabled={loggingOut}
                  className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors disabled:opacity-50"
                >
                  {loggingOut ? "Logging out..." : "Log out"}
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors"
              >
                Log in
              </Link>
            )}

            {user && <NotificationBell />}

            <Link
              href="/wishlist"
              className="relative p-1.5 text-text-muted hover:text-text transition-colors press-down"
              aria-label="Wishlist"
            >
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
              </svg>
              {wishlist.length > 0 && (
                <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-accent-purple text-white text-[10px] font-semibold flex items-center justify-center">
                  {wishlist.length}
                </span>
              )}
            </Link>

            <Link
              href="/cart"
              data-cart-target
              className="relative p-1.5 text-text-muted hover:text-text transition-colors press-down"
              aria-label="Cart"
            >
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" />
                <path d="M3 6h18" />
                <path d="M16 10a4 4 0 0 1-8 0" />
              </svg>
              {itemCount > 0 && (
                <span
                  className={`absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-accent-pink text-white text-[10px] font-semibold flex items-center justify-center transition-transform duration-200 ${
                    badgePulse ? "scale-125" : "scale-100"
                  }`}
                >
                  {itemCount}
                </span>
              )}
            </Link>
          </nav>

          <button
            className="md:hidden p-1.5 text-text-muted hover:text-text transition-colors press-down"
            onClick={() => setMenuOpen((o) => !o)}
            aria-label="Toggle menu"
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              {menuOpen ? <path d="M6 6l12 12M18 6 6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t border-border/60 bg-black/40 anim-slide-down">
          <div className="max-w-6xl mx-auto px-6 py-4 flex flex-col gap-3">
            <SearchBox />
            {user ? (
              <>
                <span className="text-sm text-text-muted">{user.name}</span>
                <Link href="/orders" onClick={closeMenu} className="text-sm text-text-muted hover:text-text transition-colors">
                  Orders
                </Link>
                <Link href="/account" onClick={closeMenu} className="text-sm text-text-muted hover:text-text transition-colors">
                  Account
                </Link>
                {user.role === "ADMIN" && (
                  <Link href="/admin" onClick={closeMenu} className="text-sm text-text-muted hover:text-text transition-colors">
                    Admin
                  </Link>
                )}
                <button
                  onClick={() => {
                    closeMenu();
                    handleLogout();
                  }}
                  disabled={loggingOut}
                  className="btn-ghost rounded-lg px-3 py-1.5 text-sm text-center hover:bg-surface-hover transition-colors disabled:opacity-50"
                >
                  {loggingOut ? "Logging out..." : "Log out"}
                </button>
              </>
            ) : (
              <Link
                href="/login"
                onClick={closeMenu}
                className="btn-ghost rounded-lg px-3 py-1.5 text-sm text-center hover:bg-surface-hover transition-colors"
              >
                Log in
              </Link>
            )}
            {user && (
              <span onClick={closeMenu} className="inline-flex -ml-1">
                <NotificationBell />
              </span>
            )}
            <Link href="/wishlist" onClick={closeMenu} className="flex items-center gap-2 text-sm text-text-muted hover:text-text transition-colors">
              Wishlist
              {wishlist.length > 0 && (
                <span className="min-w-[18px] h-[18px] px-1 rounded-full bg-accent-purple text-white text-[10px] font-semibold flex items-center justify-center">
                  {wishlist.length}
                </span>
              )}
            </Link>
            <Link href="/cart" data-cart-target onClick={closeMenu} className="flex items-center gap-2 text-sm text-text-muted hover:text-text transition-colors">
              Cart
              {itemCount > 0 && (
                <span className="min-w-[18px] h-[18px] px-1 rounded-full bg-accent-pink text-white text-[10px] font-semibold flex items-center justify-center">
                  {itemCount}
                </span>
              )}
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
