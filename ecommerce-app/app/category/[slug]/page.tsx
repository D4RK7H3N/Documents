import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { prisma } from "@/lib/prisma";
import ProductCard, { type ProductCardData } from "@/components/ProductCard";
import Reveal from "@/components/Reveal";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const category = await prisma.category.findUnique({ where: { slug } });
  if (!category) return { title: "Category not found | Clickbound Commerce" };
  return {
    title: `${category.name} | Clickbound Commerce`,
    description: `Shop ${category.name} gear on the grid.`,
  };
}

export default async function CategoryPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const category = await prisma.category.findUnique({
    where: { slug },
    include: { _count: { select: { products: true } } },
  });
  if (!category) notFound();

  const products = await prisma.product.findMany({
    where: { categoryId: category.id },
    orderBy: { createdAt: "desc" },
    include: { category: true },
  });

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-8">
      <nav className="flex items-center gap-2 text-sm text-text-muted pt-4">
        <Link href="/" className="hover:text-text transition-colors">
          Shop
        </Link>
        <span>/</span>
        <span className="text-text">{category.name}</span>
      </nav>

      <section className="glass-panel rounded-2xl p-8 flex flex-col gap-2">
        <p className="font-mono-tabular text-xs tracking-[0.3em] uppercase text-accent-pink">
          {category._count.products > 0
            ? `${category._count.products} product${category._count.products > 1 ? "s" : ""} on the grid`
            : "Fresh category"}
        </p>
        <h1 className="font-display text-4xl md:text-5xl font-bold bg-gradient-to-r from-accent-cyan to-accent-pink bg-clip-text text-transparent">
          {category.name}
        </h1>
        <Link
          href="/"
          className="btn-ghost rounded-lg px-4 py-2 text-sm self-start mt-2 hover:bg-surface-hover transition-colors"
        >
          ← All products
        </Link>
      </section>

      {products.length === 0 ? (
        <p className="text-text-muted">
          Nothing in {category.name} yet — check back soon.
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
    </main>
  );
}