import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";
import ProductCard, { type ProductCardData } from "@/components/ProductCard";
import Reveal from "@/components/Reveal";

export const dynamic = "force-dynamic";

export default async function WishlistPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  const payload = token ? verifyToken(token) : null;

  if (!payload) redirect("/login");

  const items = await prisma.wishlistItem.findMany({
    where: { userId: payload.userId },
    orderBy: { createdAt: "desc" },
    include: { product: true },
  });

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-8">
      <section className="flex flex-col gap-2 pt-4">
        <p className="font-mono-tabular text-xs tracking-[0.3em] text-accent-pink uppercase">
          Saved for later
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-bold">Wishlist</h1>
      </section>

      {items.length === 0 ? (
        <div className="flex flex-col items-center gap-4 text-center py-16">
          <p className="text-text-muted">Nothing saved yet.</p>
          <Link href="/" className="btn-primary rounded-lg px-4 py-2 text-sm">
            Browse the grid
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {items.map(({ product }, i) => (
            <Reveal key={product.id} delay={(i % 9) * 60} className="h-full">
              <ProductCard
                product={
                  {
                    id: product.id,
                    name: product.name,
                    description: product.description,
                    price: product.price,
                    salePrice: product.salePrice,
                    saleEndsAt: product.saleEndsAt
                      ? product.saleEndsAt.toISOString()
                      : null,
                    imageUrl: product.imageUrl,
                    stock: product.stock,
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
