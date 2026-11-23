import Link from "next/link";

export default function NotFound() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-24 flex flex-col items-center gap-4 text-center">
      <h1 className="font-display text-6xl md:text-8xl font-bold bg-gradient-to-r from-accent-cyan to-accent-pink bg-clip-text text-transparent">
        404
      </h1>
      <p className="font-mono-tabular text-sm tracking-[0.3em] text-text-muted uppercase">
        signal lost
      </p>
      <p className="text-text-muted">This page has drifted off the grid.</p>
      <Link href="/" className="btn-primary rounded-lg px-4 py-2 text-sm">
        Back to shop
      </Link>
    </main>
  );
}
