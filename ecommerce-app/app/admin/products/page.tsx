import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";
import AdminTabs from "@/components/AdminTabs";
import AdminProductsTable from "@/components/admin/AdminProductsTable";

export const dynamic = "force-dynamic";

const LOW_STOCK_THRESHOLD = 10;

export default async function AdminProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ lowStock?: string }>;
}) {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  const user = token ? verifyToken(token) : null;

  if (!user) redirect("/login");
  if (user.role !== "ADMIN") redirect("/");

  const { lowStock } = await searchParams;
  const lowStockOnly = lowStock === "1";

  const products = await prisma.product.findMany({
    orderBy: { createdAt: "desc" },
    include: { category: { select: { name: true } } },
  });

  const lowStockCount = products.filter((p) => p.stock <= LOW_STOCK_THRESHOLD).length;

  const rows = products.map((p) => ({
    id: p.id,
    name: p.name,
    price: p.price,
    salePrice: p.salePrice,
    stock: p.stock,
    categoryName: p.category?.name ?? null,
  }));

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <h1 className="font-display text-3xl font-bold">PRODUCTS</h1>
        <AdminTabs active="/admin/products" />
      </div>

      <div className="flex flex-wrap justify-between items-center gap-3">
        <div className="flex items-center gap-2">
          <Link
            href={lowStockOnly ? "/admin/products" : "/admin/products?lowStock=1"}
            className={`rounded-full px-3 py-1.5 text-sm transition-colors ${
              lowStockOnly
                ? "bg-amber-500/20 text-amber-500 border border-amber-500/40"
                : "btn-ghost hover:bg-surface-hover border border-border"
            }`}
          >
            ⚠ Low stock ({lowStockCount})
          </Link>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/api/admin/products/export"
            className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors"
          >
            ⬇ Export CSV
          </a>
          <Link
            href="/admin/products/new"
            className="btn-primary rounded-lg px-3 py-1.5 text-sm"
          >
            New product
          </Link>
        </div>
      </div>

      <AdminProductsTable products={rows} lowStockOnly={lowStockOnly} />
    </main>
  );
}
