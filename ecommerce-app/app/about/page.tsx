export const metadata = {
  title: "About — Clickbound",
};

import Reveal from "@/components/Reveal";

export default function AboutPage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-10 flex flex-col gap-8">
      <Reveal>
        <div className="flex flex-col gap-2">
          <p className="font-mono-tabular text-xs tracking-[0.3em] text-accent-pink uppercase">
            Our story
          </p>
          <h1 className="font-display text-3xl md:text-4xl font-bold">
            About Clickbound
          </h1>
        </div>
      </Reveal>

      <Reveal delay={80}>
        <section className="flex flex-col gap-3">
        <p className="text-text-muted leading-relaxed">
          Clickbound started with a simple frustration: great tech accessories
          were either boring, expensive, or both. We set out to build a shop for
          gear that looks like it belongs on a flagship setup — neon-accented,
          performance-first, and honest about what it costs.
        </p>
        <p className="text-text-muted leading-relaxed">
          Every product we stock goes through real testing: battery claims are
          checked with a timer, not a brochure. If a product doesn&apos;t survive,
          it doesn&apos;t get listed. That&apos;s the whole brand.
        </p>
      </section>
      </Reveal>

      <Reveal delay={160}>
        <section className="flex flex-col gap-3">
          <h2 className="font-display text-xl font-bold">Why the grid aesthetic?</h2>
          <p className="text-text-muted leading-relaxed">
            The grid is everywhere — city blocks, circuit boards, pixel screens.
            Our design language borrows from all three: sharp corners, glowing
            accents, and typography that reads like a HUD. It&apos;s a reminder that
            gear should feel exciting to own, not just functional.
          </p>
        </section>
      </Reveal>

      <Reveal delay={240}>
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { k: "01", t: "Tested before listed", d: "Hands-on verification for every SKU we carry." },
            { k: "02", t: "Real stock, real stock", d: "Inventory counts are live — no phantom pre-orders." },
            { k: "03", t: "Support that answers", d: "Reach us via the contact page and get a reply within a day." },
          ].map((v) => (
            <div key={v.k} className="glass-panel rounded-xl p-4 flex flex-col gap-2">
              <span className="font-mono-tabular text-xs text-accent-cyan">{v.k}</span>
              <span className="font-display font-semibold">{v.t}</span>
              <span className="text-sm text-text-muted">{v.d}</span>
            </div>
          ))}
        </section>
      </Reveal>
    </main>
  );
}
