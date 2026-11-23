import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";
import AdminTabs from "@/components/AdminTabs";

export const dynamic = "force-dynamic";

const STATUS_STYLES: Record<string, string> = {
  PENDING: "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/30",
  PAID: "bg-success/10 text-success border border-success/30",
  SHIPPED: "bg-accent-purple/10 text-accent-purple border border-accent-purple/30",
  DELIVERED: "bg-accent-pink/10 text-accent-pink border border-accent-pink/30",
  CANCELLED: "bg-danger/10 text-danger border border-danger/30",
};

async function getOrders() {
  return prisma.order.findMany({
    orderBy: { createdAt: "desc" },
    include: { user: { select: { email: true } }, items: true },
  });
}

export default async function AdminOrdersPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  const user = token ? verifyToken(token) : null;

  if (!user) redirect("/login");
  if (user.role !== "ADMIN") redirect("/");

  const orders = await getOrders();

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <h1 className="font-display text-3xl font-bold">ORDERS</h1>
        <AdminTabs active="/admin/orders" />
      </div>

      <div className="flex justify-end">
        <a
          href="/api/admin/orders/export"
          className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors"
        >
          ⬇ Export CSV
        </a>
      </div>

      {orders.length === 0 ? (
        <p className="text-text-muted">No orders yet.</p>
      ) : (
        <div className="glass-panel rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-muted border-b border-border">
                <th className="p-3 font-medium">Order</th>
                <th className="p-3 font-medium">Customer</th>
                <th className="p-3 font-medium">Date</th>
                <th className="p-3 font-medium">Status</th>
                <th className="p-3 font-medium">Total</th>
                <th className="p-3 font-medium">Shipping</th>
                <th className="p-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} className="border-b border-border last:border-b-0">
                  <td className="p-3 font-mono-tabular text-accent-cyan">#{order.id.slice(0, 8)}</td>
                  <td className="p-3 text-text-muted">{order.user.email}</td>
                  <td className="p-3 font-mono-tabular text-text-muted">
                    {new Date(order.createdAt).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </td>
                  <td className="p-3">
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                        STATUS_STYLES[order.status] ?? "bg-surface-hover text-text-muted"
                      }`}
                    >
                      {order.status}
                    </span>
                  </td>
                  <td className="p-3 font-mono-tabular">${(order.totalAmount / 100).toFixed(2)}</td>
                  <td className="p-3">
                    {order.shippingMethod === "EXPRESS"
                      ? "Express"
                      : order.shippingMethod === "STANDARD"
                        ? "Standard"
                        : <span className="text-text-muted">—</span>}
                    {order.shippingCost > 0 && (
                      <span className="font-mono-tabular text-xs text-text-muted ml-2">
                        +${(order.shippingCost / 100).toFixed(2)}
                      </span>
                    )}
                  </td>
                  <td className="p-3 flex justify-end">
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
    </main>
  );
}
