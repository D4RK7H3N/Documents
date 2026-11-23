import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";

export const dynamic = "force-dynamic";

async function getOrders(userId: string) {
  return prisma.order.findMany({
    where: { userId },
    orderBy: { createdAt: "desc" },
    include: { items: { include: { product: true } } },
  });
}

const STATUS_STYLES: Record<string, string> = {
  PENDING: "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/30",
  PAID: "bg-success/10 text-success border border-success/30",
  SHIPPED: "bg-accent-purple/10 text-accent-purple border border-accent-purple/30",
  DELIVERED: "bg-accent-pink/10 text-accent-pink border border-accent-pink/30",
  CANCELLED: "bg-danger/10 text-danger border border-danger/30",
};

export default async function OrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ success?: string }>;
}) {
  const { success } = await searchParams;

  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  const user = token ? verifyToken(token) : null;

  if (!user) redirect("/login");

  const orders = await getOrders(user.userId);

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-3xl font-bold">ORDERS</h1>
        <p className="text-sm text-text-muted">Everything you&apos;ve locked in.</p>
      </div>

      {success === "true" && (
        <div className="bg-success/10 border border-success/30 text-success rounded-lg px-4 py-3 text-sm">
          Order placed — it&apos;s locked in. We&apos;ll ship it soon.
        </div>
      )}

      {orders.length === 0 ? (
        <p className="text-text-muted">No orders yet.</p>
      ) : (
        <div className="flex flex-col gap-4">
          {orders.map((order) => {
            const itemCount = order.items.reduce((sum, i) => sum + i.quantity, 0);
            return (
              <Link
                key={order.id}
                href={`/orders/${order.id}`}
                className="glass-panel rounded-xl p-4 flex items-center justify-between gap-4 hover:border-accent-cyan/40 transition-colors"
              >
                <div className="flex flex-col gap-1">
                  <span className="font-mono-tabular font-medium text-accent-cyan">
                    #{order.id.slice(0, 8)}
                  </span>
                  <span className="text-text-muted text-sm">
                    {new Date(order.createdAt).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}{" "}
                    · {itemCount} item{itemCount === 1 ? "" : "s"}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                      STATUS_STYLES[order.status] ?? "bg-surface-hover text-text-muted"
                    }`}
                  >
                    {order.status}
                  </span>
                  <span className="font-mono-tabular font-medium">
                    ${(order.totalAmount / 100).toFixed(2)}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </main>
  );
}
