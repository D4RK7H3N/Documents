import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";
import ProductBuyPanel from "@/components/ProductBuyPanel";
import ProductCard, { type ProductCardData } from "@/components/ProductCard";
import ReviewForm from "@/components/ReviewForm";
import WishlistButton from "@/components/WishlistButton";
import { isOnSale, effectivePrice, salePercent } from "@/lib/pricing";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const product = await prisma.product.findUnique({ where: { id } });
  if (!product) return { title: "Product not found | Clickbound Commerce" };
  return {
    title: `${product.name} | Clickbound Commerce`,
    description: product.description,
  };
}

export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const product = await prisma.product.findUnique({
    where: { id },
    include: { category: true },
  });

  if (!product) notFound();

  const relatedRaw = await prisma.product.findMany({
    where: { categoryId: product.categoryId, id: { not: product.id } },
    take: 3,
    orderBy: { createdAt: "desc" },
  });

  const fallback = await prisma.product.findMany({
    where: { id: { not: product.id } },
    take: 3,
    orderBy: { createdAt: "desc" },
  });

  const related = [...relatedRaw, ...fallback]
    .filter((p, i, arr) => arr.findIndex((x) => x.id === p.id) === i)
    .slice(0, 3);

  const [reviews, auth] = await Promise.all([
    prisma.review.findMany({
      where: { productId: product.id },
      orderBy: { createdAt: "desc" },
      select: {
        id: true,
        rating: true,
        comment: true,
        createdAt: true,
        userId: true,
        user: { select: { name: true } },
      },
    }),
    cookies()
      .then((cs) => cs.get("token")?.value ?? null)
      .then((token) => (token ? verifyToken(token) : null)),
  ]);

  const currentUserId = auth?.userId ?? null;
  const canReview =
    currentUserId !== null && !reviews.some((r) => r.userId === currentUserId);

  const onSale = isOnSale(product);
  const pct = salePercent(product);

  return (
    <main className="max-w-6xl mx-auto px-6 py-8 flex flex-col gap-12">
      <nav className="flex items-center gap-2 text-sm text-text-muted">
        <Link href="/" className="hover:text-text transition-colors">
          Shop
        </Link>
        {product.category && (
          <>
            <span>/</span>
            <Link
              href={`/?category=${product.category.slug}`}
              className="hover:text-text transition-colors"
            >
              {product.category.name}
            </Link>
          </>
        )}
        <span>/</span>
        <span className="text-text truncate">{product.name}</span>
      </nav>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-10">
        <div className="aspect-square rounded-xl overflow-hidden border border-border">
          {product.imageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={product.imageUrl}
              alt={product.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div
              className="w-full h-full"
              style={{
                background:
                  "radial-gradient(circle at 30% 25%, var(--accent-purple) 0%, transparent 55%), radial-gradient(circle at 70% 60%, var(--accent-pink) 0%, transparent 55%), radial-gradient(circle at 45% 85%, var(--accent-cyan) 0%, transparent 55%), var(--surface)",
              }}
            />
          )}
        </div>

        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-4">
            {product.category ? (
              <Link
                href={`/?category=${product.category.slug}`}
                className="font-mono-tabular text-xs tracking-[0.25em] uppercase text-accent-pink hover:opacity-80 transition-opacity"
              >
                {product.category.name}
              </Link>
            ) : (
              <span />
            )}
            <WishlistButton productId={product.id} />
          </div>

          <h1 className="font-display text-3xl md:text-4xl font-bold">{product.name}</h1>

          <div className="flex items-baseline gap-3">
            <p className="font-mono-tabular text-2xl font-medium text-accent-cyan">
              ${(effectivePrice(product) / 100).toFixed(2)}
            </p>
            {onSale && (
              <>
                <p className="font-mono-tabular text-lg text-text-muted line-through">
                  ${(product.price / 100).toFixed(2)}
                </p>
                {pct !== null && (
                  <span className="px-2 py-0.5 rounded-full bg-accent-pink/15 border border-accent-pink/40 text-accent-pink text-xs font-bold">
                    -{pct}% flash deal
                  </span>
                )}
              </>
            )}
          </div>

          <p className={product.stock > 0 ? "text-sm text-success" : "text-sm text-danger"}>
            {product.stock > 0
              ? `In stock (${product.stock} available)`
              : "Out of stock"}
          </p>

          <p className="text-text-muted leading-relaxed">{product.description}</p>

          <div className="pt-2">
            <ProductBuyPanel productId={product.id} stock={product.stock} imageUrl={product.imageUrl} />
          </div>
        </div>
      </section>

      {reviews.length > 0 || canReview ? (
        <section className="flex flex-col gap-6 max-w-2xl">
          <h2 className="font-display text-2xl font-bold">Reviews</h2>

          {canReview && <ReviewForm productId={product.id} />}

          {reviews.length === 0 ? (
            <p className="text-text-muted">No reviews yet.</p>
          ) : (
            <ul className="flex flex-col gap-4">
              {reviews.map((r) => (
                <li key={r.id} className="glass-panel rounded-xl p-4 flex flex-col gap-1">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">
                      {r.user.name}
                      {r.userId === currentUserId && (
                        <span className="font-mono-tabular text-xs text-accent-cyan ml-2">you</span>
                      )}
                    </span>
                    <span className="text-accent-pink" aria-label={`${r.rating} out of 5 stars`}>
                      {"★".repeat(r.rating)}
                      <span className="text-text-muted">{"★".repeat(5 - r.rating)}</span>
                    </span>
                  </div>
                  <p className="font-mono-tabular text-xs text-text-muted">
                    {new Date(r.createdAt).toLocaleDateString()}
                  </p>
                  {r.comment && <p className="text-sm text-text-muted mt-1">{r.comment}</p>}
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : (
        <section className="flex flex-col gap-2 max-w-2xl">
          <h2 className="font-display text-2xl font-bold">Reviews</h2>
          <p className="text-text-muted">No reviews yet.</p>
        </section>
      )}

      {related.length > 0 && (
        <section className="flex flex-col gap-6">
          <h2 className="font-display text-2xl font-bold">Related gear</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            {related.map((p) => (
              <ProductCard
                key={p.id}
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
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
