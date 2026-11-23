import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";
import AdminTabs from "@/components/AdminTabs";

export const dynamic = "force-dynamic";

export default async function AdminDashboardPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  const payload = token ? verifyToken(token) : null;

  if (!payload) redirect("/login");
  if (payload.role !== "ADMIN") redirect("/");

  const since = new Date();
  since.setMonth(since.getMonth() - 5);
  since.setDate(1);
  since.setHours(0, 0, 0, 0);

  const [
    revenue,
    orderCount,
    productCount,
    outOfStockCount,
    customerCount,
    recentOrders,
    monthly,
    bestSellers,
  ] = await Promise.all([
    prisma.order.aggregate({
      where: { status: { not: "CANCELLED" } },
      _sum: { totalAmount: true },
    }),
    prisma.order.count(),
    prisma.product.count(),
    prisma.product.count({ where: { stock: 0 } }),
    prisma.user.count({ where: { role: "CUSTOMER" } }),
    prisma.order.findMany({
      take: 5,
      orderBy: { createdAt: "desc" },
      include: { user: { select: { email: true } } },
    }),
    prisma.order.groupBy({
      by: ["createdAt"],
      where: {
        status: { not: "CANCELLED" },
        createdAt: { gte: since },
      },
      _sum: { totalAmount: true },
    }),
    prisma.orderItem.groupBy({
      by: ["productId"],
      where: { order: { status: { not: "CANCELLED" } } },
      _sum: { quantity: true },
      orderBy: { _sum: { quantity: "desc" } },
      take: 5,
    }),
  ]);

  const bestSellerNames = bestSellers.length
    ? await prisma.product.findMany({
        where: { id: { in: bestSellers.map((b) => b.productId) } },
        select: { id: true, name: true },
      })
    : [];
  const nameById = new Map(bestSellerNames.map((p) => [p.id, p.name]));

  const monthMap = new Map<string, number>();
  for (const row of monthly) {
    const key = row.createdAt.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
    });
    monthMap.set(key, (monthMap.get(key) ?? 0) + (row._sum.totalAmount ?? 0));
  }

  const monthlyTotals = Array.from({ length: 6 }, (_, i) => {
    const d = new Date(since.getFullYear(), since.getMonth() + i, 1);
    const key = d.toLocaleDateString("en-US", { year: "numeric", month: "short" });
    return { month: key, total: monthMap.get(key) ?? 0 };
  });

  const maxMonthTotal = Math.max(1, ...monthlyTotals.map((m) => m.total));

  const stats = [
    {
      label: "Revenue",
      value: `$${((revenue._sum.totalAmount ?? 0) / 100).toFixed(2)}`,
      sub: "non-cancelled orders",
    },
    { label: "Orders", value: String(orderCount), sub: "all time" },
    { label: "Products", value: String(productCount), sub: `${outOfStockCount} out of stock` },
    { label: "Customers", value: String(customerCount), sub: "customer accounts" },
  ];

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-8">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <p className="font-mono-tabular text-xs tracking-[0.3em] text-accent-pink uppercase">
            Control deck
          </p>
          <h1 className="font-display text-3xl md:text-4xl font-bold">Admin dashboard</h1>
        </div>
        <AdminTabs active="/admin" />
      </div>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="glass-panel rounded-xl p-4 flex flex-col gap-1">
            <span className="text-xs tracking-widest text-text-muted uppercase">{s.label}</span>
            <span className="font-mono-tabular text-2xl font-medium text-accent-cyan">{s.value}</span>
            <span className="text-xs text-text-muted">{s.sub}</span>
          </div>
        ))}
      </section>

      <div className="grid lg:grid-cols-[1fr_360px] gap-6 items-start">
        <section className="glass-panel rounded-xl p-6 flex flex-col gap-4">
          <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
            REVENUE · LAST 6 MONTHS
          </h2>
          {monthlyTotals.some((m) => m.total > 0) ? (
            <div className="flex items-end gap-3 h-40">
              {monthlyTotals.map((m) => (
                <div key={m.month} className="flex-1 flex flex-col items-center gap-2 min-w-0">
                  <span className="font-mono-tabular text-[10px] text-text-muted">
                    ${(m.total / 100).toFixed(0)}
                  </span>
                  <div
                    className="w-full rounded-t bg-gradient-to-t from-accent-purple/60 to-accent-cyan/80"
                    style={{ height: `${Math.max(3, (m.total / maxMonthTotal) * 100)}%` }}
                  />
                  <span className="text-[10px] text-text-muted">{m.month}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted">No sales yet.</p>
          )}
        </section>

        <section className="glass-panel rounded-xl p-6 flex flex-col gap-3">
          <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
            BEST SELLERS
          </h2>
          {bestSellers.length === 0 ? (
            <p className="text-sm text-text-muted">No sales yet.</p>
          ) : (
            <ol className="flex flex-col gap-2">
              {bestSellers.map((b, i) => (
                <li key={b.productId} className="flex items-center justify-between gap-3 text-sm">
                  <span className="flex items-center gap-2 min-w-0">
                    <span className="font-mono-tabular text-text-muted w-4">{i + 1}.</span>
                    <span className="truncate">{nameById.get(b.productId) ?? "Unknown"}</span>
                  </span>
                  <span className="font-mono-tabular text-xs text-text-muted shrink-0">
                    {b._sum.quantity ?? 0} sold
                  </span>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>

      <section className="flex flex-col gap-4">
        <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
          RECENT ORDERS
        </h2>
        {recentOrders.length === 0 ? (
          <p className="text-sm text-text-muted">No orders yet.</p>
        ) : (
          <div className="glass-panel rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-muted border-b border-border">
                  <th className="p-3 font-medium">Order</th>
                  <th className="p-3 font-medium">Customer</th>
                  <th className="p-3 font-medium">Status</th>
                  <th className="p-3 font-medium">Total</th>
                  <th className="p-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {recentOrders.map((order) => (
                  <tr key={order.id} className="border-b border-border last:border-b-0">
                    <td className="p-3 font-mono-tabular text-accent-cyan">#{order.id.slice(0, 8)}</td>
                    <td className="p-3 text-text-muted">{order.user.email}</td>
                    <td className="p-3">{order.status}</td>
                    <td className="p-3 font-mono-tabular">${(order.totalAmount / 100).toFixed(2)}</td>
                    <td className="p-3 text-right">
                      <Link
                        href={`/admin/orders/${order.id}`}
                        className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors"
                      >
                        Manage
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
