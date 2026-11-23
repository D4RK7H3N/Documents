import Link from "next/link";
import NewsletterForm from "@/components/NewsletterForm";

export default function Footer() {
  return (
    <footer className="glass-bar border-t-0 mt-16">
      <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col md:flex-row items-center md:items-start justify-between gap-8">
        <div className="flex flex-col gap-2 text-center md:text-left">
          <span className="flex items-center gap-2 justify-center md:justify-start">
            <svg viewBox="0 0 64 64" className="w-5 h-5" aria-hidden="true">
              <rect x="2" y="2" width="60" height="60" rx="16" fill="#0b0618" />
              <rect
                x="2"
                y="2"
                width="60"
                height="60"
                rx="16"
                fill="none"
                stroke="url(#footer-ring)"
                strokeWidth="4"
              />
              <defs>
                <linearGradient id="footer-ring" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0" stopColor="#00f5ff" />
                  <stop offset="1" stopColor="#ff2975" />
                </linearGradient>
                <linearGradient id="footer-bolt" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stopColor="#00f5ff" />
                  <stop offset="0.55" stopColor="#9d00ff" />
                  <stop offset="1" stopColor="#ff2975" />
                </linearGradient>
              </defs>
              <path d="M38 10 L14 36 h12 l-4 18 26-28 H35 l3-16z" fill="url(#footer-bolt)" />
            </svg>
            <span className="font-display font-bold tracking-[0.2em] bg-gradient-to-r from-accent-cyan to-accent-pink bg-clip-text text-transparent">
              CLICKBOUND
            </span>
          </span>
          <p className="text-sm text-text-muted">Neon-grade gear for the grid.</p>
          <div className="mt-2 flex justify-center md:justify-start">
            <NewsletterForm />
          </div>
        </div>

        <nav className="flex flex-col md:flex-row items-center gap-3 md:gap-8 text-sm">
          <Link href="/" className="text-text-muted hover:text-text transition-colors">
            Shop
          </Link>
          <Link href="/orders" className="text-text-muted hover:text-text transition-colors">
            Orders
          </Link>
          <Link href="/account" className="text-text-muted hover:text-text transition-colors">
            Account
          </Link>
          <Link href="/about" className="text-text-muted hover:text-text transition-colors">
            About
          </Link>
          <Link href="/faq" className="text-text-muted hover:text-text transition-colors">
            FAQ
          </Link>
          <Link href="/contact" className="text-text-muted hover:text-text transition-colors">
            Contact
          </Link>
        </nav>

        <p className="font-mono-tabular text-xs text-text-muted">
          © {new Date().getFullYear()} Clickbound Commerce
        </p>
      </div>
    </footer>
  );
}
