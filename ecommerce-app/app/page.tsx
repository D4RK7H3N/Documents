import Link from "next/link";
import { prisma } from "@/lib/prisma";
import ProductCard, { type ProductCardData } from "@/components/ProductCard";
import HeroSlideshow, { type HeroSlide } from "@/components/HeroSlideshow";
import ShopControls from "@/components/ShopControls";
import CountdownTimer from "@/components/CountdownTimer";
import Reveal from "@/components/Reveal";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 9;

type SortKey = "newest" | "price-asc" | "price-desc" | "name";

const ORDER_BY: Record<SortKey, object> = {
  newest: { createdAt: "desc" },
  "price-asc": { price: "asc" },
  "price-desc": { price: "desc" },
  name: { name: "asc" },
};

function buildHref(
  category?: string,
  q?: string,
  page = 1,
  sort: SortKey = "newest",
  inStock = false,
) {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (q) params.set("q", q);
  if (sort !== "newest") params.set("sort", sort);
  if (inStock) params.set("inStock", "1");
  if (page > 1) params.set("page", String(page));
  const s = params.toString();
  return s ? `/?${s}` : "/";
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string; q?: string; page?: string; sort?: string; inStock?: string }>;
}) {
  const sp = await searchParams;
  const category = sp.category;
  const q = sp.q?.trim();
  const sort: SortKey =
    sp.sort === "price-asc" || sp.sort === "price-desc" || sp.sort === "name"
      ? sp.sort
      : "newest";
  const inStock = sp.inStock === "1";

  const categories = await prisma.category.findMany({
    orderBy: { name: "asc" },
    include: { _count: { select: { products: true } } },
  });
  const selected = categories.find((c) => c.slug === category);

  const heroSlides: HeroSlide[] =
    categories.length > 0
      ? categories.map((c) => ({
          id: c.id,
          name: c.name,
          count: c._count.products,
          slug: c.slug,
        }))
      : [
          { id: "fashion", name: "Fashion", count: 0, slug: null },
          { id: "gadgets", name: "Gadgets", count: 0, slug: null },
          { id: "technology", name: "Technology", count: 0, slug: null },
          { id: "more", name: "More on the way", count: 0, slug: null },
        ];

  const where = {
    AND: [
      ...(selected ? [{ categoryId: selected.id }] : []),
      ...(q
        ? [{ name: { contains: q, mode: "insensitive" as const } }]
        : []),
      ...(inStock ? [{ stock: { gt: 0 } }] : []),
    ],
  };

  const total = await prisma.product.count({ where });
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const page = Math.min(
    Math.max(parseInt(sp.page ?? "1", 10) || 1, 1),
    totalPages,
  );

  const products = await prisma.product.findMany({
    where,
    orderBy: ORDER_BY[sort],
    skip: PAGE_SIZE * (page - 1),
    take: PAGE_SIZE,
  });

  const flashDeals = await prisma.product.findMany({
    where: {
      salePrice: { not: null },
      OR: [{ saleEndsAt: null }, { saleEndsAt: { gt: new Date() } }],
    },
    take: 4,
  });
  flashDeals.sort(
    (a, b) =>
      (b.price - (b.salePrice ?? b.price)) -
      (a.price - (a.salePrice ?? a.price)),
  );

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-8">
      <Reveal variant="fade-up">
        <section className="flex flex-col gap-2 pt-4">
          <p className="font-mono-tabular text-xs tracking-[0.3em] text-accent-pink uppercase">
            Neon-grade gear · synthwave standard
          </p>
          <h1 className="font-display text-4xl md:text-5xl font-bold">
            Shop the{" "}
            <span className="bg-gradient-to-r from-accent-cyan to-accent-pink bg-clip-text text-transparent">
              grid
            </span>
          </h1>
          {q && (
            <p className="text-sm text-text-muted">
              Results for <span className="text-accent-cyan">“{q}”</span> ·{" "}
              <Link href="/" className="underline hover:text-text transition-colors">
                Clear search
              </Link>
            </p>
          )}
        </section>
      </Reveal>

      <Reveal variant="fade-in" delay={80}>
        <HeroSlideshow slides={heroSlides} />
      </Reveal>

      {flashDeals.length > 0 && (
        <Reveal>
          <section className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <span className="text-xl">⚡</span>
              <h2 className="font-display text-2xl font-bold">Flash deals</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
              {flashDeals.map((p) => {
                const pct = p.price > 0 ? Math.round((1 - (p.salePrice ?? p.price) / p.price) * 100) : 0;
                return (
                  <div key={p.id} className="glow-card rounded-xl overflow-hidden flex flex-col">
                  <Link href={`/products/${p.id}`} className="block aspect-[4/3] overflow-hidden">
                    {p.imageUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={p.imageUrl} alt={p.name} className="w-full h-full object-cover transition-transform duration-300 hover:scale-105" />
                    ) : (
                      <div
                        className="w-full h-full"
                        style={{
                          background:
                            "radial-gradient(circle at 30% 25%, var(--accent-purple) 0%, transparent 55%), radial-gradient(circle at 70% 60%, var(--accent-pink) 0%, transparent 55%), radial-gradient(circle at 45% 85%, var(--accent-cyan) 0%, transparent 55%), var(--surface)",
                        }}
                      />
                    )}
                  </Link>
                  <div className="p-4 flex flex-col gap-2 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="px-2 py-0.5 rounded-full bg-accent-pink text-white text-[10px] font-bold tracking-wider">
                        -{pct}% OFF
                      </span>
                      {p.saleEndsAt && <CountdownTimer endsAt={p.saleEndsAt.toISOString()} />}
                    </div>
                    <Link href={`/products/${p.id}`}>
                      <h3 className="font-display font-semibold hover:text-accent-cyan transition-colors">
                        {p.name}
                      </h3>
                    </Link>
                    <div className="flex items-baseline gap-2 mt-auto pt-2">
                      <span className="font-mono-tabular font-medium text-accent-pink">
                        ${((p.salePrice ?? p.price) / 100).toFixed(2)}
                      </span>
                      <span className="font-mono-tabular text-xs text-text-muted line-through">
                        ${(p.price / 100).toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          </section>
        </Reveal>
      )}

      {categories.length > 0 && (
        <Reveal variant="fade-in" delay={120}>
          <div className="flex flex-wrap gap-2">
          <Link
            href={q ? buildHref(undefined, q, 1, sort, inStock) : buildHref(undefined, undefined, 1, sort, inStock)}
            className={`rounded-full px-3 py-1 text-sm transition-colors ${
              !selected
                ? "btn-primary"
                : "btn-ghost text-text-muted hover:bg-surface-hover"
            }`}
          >
            All
          </Link>
          {categories.map((c) => (
            <Link
              key={c.id}
              href={
                selected?.id === c.id
                  ? buildHref(undefined, q, 1, sort, inStock)
                  : buildHref(c.slug, q, 1, sort, inStock)
              }
              className={`rounded-full px-3 py-1 text-sm transition-colors ${
                selected?.id === c.id
                  ? "btn-primary"
                  : "btn-ghost text-text-muted hover:bg-surface-hover"
              }`}
            >
              {c.name}
            </Link>
          ))}
          </div>
        </Reveal>
      )}

      <Reveal variant="fade-in" delay={100}>
        <ShopControls
          sort={sort}
          inStock={inStock}
          category={category}
          q={q}
          total={total}
        />
      </Reveal>

      {products.length === 0 ? (
        <p className="text-text-muted">
          {q
            ? "No products match that search."
            : selected
              ? `Nothing in ${selected.name} yet.`
              : "No products yet. Add some via the admin API."}
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {products.map((p, i) => (
            <Reveal key={p.id} delay={(i % 9) * 60} className="h-full">
              <ProductCard
                product={
                  {
                    id: p.id,
                    name: p.name,
                    description: p.description,
                    price: p.price,
                    salePrice: p.salePrice,
                    saleEndsAt: p.saleEndsAt ? p.saleEndsAt.toISOString() : null,
                    imageUrl: p.imageUrl,
                    stock: p.stock,
                  } satisfies ProductCardData
                }
              />
            </Reveal>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <nav className="flex items-center justify-center gap-6">
          <Link
            href={buildHref(category, q, page - 1, sort, inStock)}
            className={`btn-ghost rounded-lg px-4 py-2 text-sm transition-colors ${
              page <= 1
                ? "opacity-40 pointer-events-none"
                : "hover:bg-surface-hover"
            }`}
          >
            ← Prev
          </Link>
          <span className="font-mono-tabular text-sm text-text-muted">
            Page {page} of {totalPages}
          </span>
          <Link
            href={buildHref(category, q, page + 1, sort, inStock)}
            className={`btn-ghost rounded-lg px-4 py-2 text-sm transition-colors ${
              page >= totalPages
                ? "opacity-40 pointer-events-none"
                : "hover:bg-surface-hover"
            }`}
          >
            Next →
          </Link>
        </nav>
      )}
    </main>
  );
}
