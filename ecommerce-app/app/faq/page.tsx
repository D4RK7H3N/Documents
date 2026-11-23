export const metadata = {
  title: "FAQ — Clickbound",
};

const FAQS = [
  {
    q: "How long does shipping take?",
    a: "Orders ship within 1–2 business days. Standard shipping takes 3–5 business days; express options are available at checkout with live pricing.",
  },
  {
    q: "Do you offer free shipping?",
    a: "Orders over a set threshold qualify for free standard shipping — the exact amount and available methods are shown at checkout before you pay.",
  },
  {
    q: "Can I cancel or change my order?",
    a: "Yes — orders can be cancelled as long as they haven't shipped yet. Go to your Orders page and use the cancel button. A refund is issued for paid orders.",
  },
  {
    q: "What if my order arrives damaged?",
    a: "Contact us through the contact page within 7 days of delivery with your order number and a photo. We'll replace the item or refund you in full.",
  },
  {
    q: "How do flash deals work?",
    a: "Products on sale show a discounted price with a countdown. The sale price applies at checkout while the countdown is active — once it ends, the regular price returns.",
  },
  {
    q: "Can I return a product?",
    a: "Unopened products can be returned within 30 days of delivery. Email us your order number to start the process.",
  },
  {
    q: "How do I track my order?",
    a: "Once your order ships, a tracking number appears on the order detail page. You can follow it from your Orders page at any time.",
  },
];

import Reveal from "@/components/Reveal";

export default function FaqPage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-10 flex flex-col gap-8">
      <Reveal>
        <div className="flex flex-col gap-2">
          <p className="font-mono-tabular text-xs tracking-[0.3em] text-accent-pink uppercase">
            Answers
          </p>
          <h1 className="font-display text-3xl md:text-4xl font-bold">
            Frequently asked questions
          </h1>
        </div>
      </Reveal>

      <Reveal delay={80}>
        <div className="flex flex-col gap-3">
        {FAQS.map((f) => (
          <details
            key={f.q}
            className="glass-panel rounded-xl overflow-hidden group"
          >
            <summary className="cursor-pointer list-none px-4 py-3 flex items-center justify-between gap-3 select-none">
              <span className="font-display font-semibold text-sm">{f.q}</span>
              <span className="text-text-muted group-open:rotate-45 transition-transform text-lg leading-none">
                +
              </span>
            </summary>
            <p className="px-4 pb-4 text-sm text-text-muted leading-relaxed">
              {f.a}
            </p>
          </details>
        ))}
        </div>
      </Reveal>

      <Reveal delay={160}>
        <p className="text-sm text-text-muted">
          Still stuck?{" "}
          <a href="/contact" className="text-accent-cyan hover:underline">
            Get in touch
          </a>{" "}
          and we&apos;ll sort it out.
        </p>
      </Reveal>
    </main>
  );
}
