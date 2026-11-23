import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";
import CancelOrderButton from "@/components/CancelOrderButton";

export const dynamic = "force-dynamic";

const STATUS_META: Record<string, { label: string; badge: string; dot: string }> = {
  PENDING: {
    label: "Order placed",
    badge: "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/30",
    dot: "bg-accent-cyan",
  },
  PAID: {
    label: "Paid",
    badge: "bg-success/10 text-success border border-success/30",
    dot: "bg-success",
  },
  SHIPPED: {
    label: "Shipped",
    badge: "bg-accent-purple/10 text-accent-purple border border-accent-purple/30",
    dot: "bg-accent-purple",
  },
  DELIVERED: {
    label: "Delivered",
    badge: "bg-accent-pink/10 text-accent-pink border border-accent-pink/30",
    dot: "bg-accent-pink",
  },
  CANCELLED: {
    label: "Cancelled",
    badge: "bg-danger/10 text-danger border border-danger/30",
    dot: "bg-danger",
  },
};

async function getOrder(id: string, userId: string) {
  const order = await prisma.order.findUnique({
    where: { id },
    include: {
      items: { include: { product: true } },
      events: { orderBy: { createdAt: "asc" } },
    },
  });
  if (!order || order.userId !== userId) return null;
  return order;
}

export default async function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  const user = token ? verifyToken(token) : null;

  if (!user) redirect("/login");

  const order = await getOrder(id, user.userId);
  if (!order) redirect("/orders");

  const itemCount = order.items.reduce((sum, i) => sum + i.quantity, 0);
  const meta = STATUS_META[order.status] ?? STATUS_META.PENDING;
  const subtotal = order.items.reduce((sum, i) => sum + i.price * i.quantity, 0);
  const shippingLabel =
    order.shippingMethod === "EXPRESS"
      ? "Express"
      : order.shippingMethod === "STANDARD"
        ? "Standard"
        : null;

  return (
    <main className="max-w-4xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <Link href="/orders" className="text-sm text-text-muted hover:text-text transition-colors">
            ← Back to orders
          </Link>
          <h1 className="font-mono-tabular font-medium text-accent-cyan text-2xl">#{order.id.slice(0, 8)}</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${meta.badge}`}>{order.status}</span>
          <span className="font-mono-tabular text-lg font-medium">${(order.totalAmount / 100).toFixed(2)}</span>
          {(order.status === "PENDING" || order.status === "PAID") && (
            <CancelOrderButton orderId={order.id} />
          )}
        </div>
      </div>

      {order.trackingNumber && (
        <div className="glass-panel rounded-xl p-4 flex items-center justify-between gap-4">
          <span className="text-sm text-text-muted">Tracking number</span>
          <span className="font-mono-tabular font-medium text-accent-cyan">{order.trackingNumber}</span>
        </div>
      )}

      <section className="glass-panel rounded-xl p-6">
        <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted mb-6">
          TRACKING
        </h2>
        <ol className="flex flex-col">
          {order.events.map((event, i) => {
            const m = STATUS_META[event.status] ?? STATUS_META.PENDING;
            const isLast = i === order.events.length - 1;
            return (
              <li key={event.id} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <span className={`w-3 h-3 rounded-full mt-1 ${m.dot} ${event.status === order.status ? "ring-4 ring-current" : ""}`} />
                  {!isLast && <span className="w-px flex-1 bg-border my-1" />}
                </div>
                <div className={`flex flex-col gap-0.5 pb-6 ${isLast ? "pb-0" : ""}`}>
                  <span className="font-display font-semibold text-sm">
                    {m.label}
                    {event.status === order.status && (
                      <span className="ml-2 text-xs font-medium text-text-muted">current</span>
                    )}
                  </span>
                  <span className="font-mono-tabular text-xs text-text-muted">
                    {new Date(event.createdAt).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                  {event.note && <span className="text-sm text-text-muted">{event.note}</span>}
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="glass-panel rounded-xl p-6 flex flex-col gap-4">
        <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
          ITEMS · {itemCount}
        </h2>
        <ul className="flex flex-col gap-4">
          {order.items.map((item) => (
            <li key={item.id} className="flex items-center gap-4">
              {item.product.imageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={item.product.imageUrl} alt={item.product.name} className="w-14 h-14 rounded-lg object-cover shrink-0" />
              ) : (
                <div
                  className="w-14 h-14 rounded-lg shrink-0"
                  style={{
                    background:
                      "radial-gradient(circle at 30% 25%, var(--accent-purple) 0%, transparent 60%), radial-gradient(circle at 70% 60%, var(--accent-pink) 0%, transparent 60%), radial-gradient(circle at 45% 85%, var(--accent-cyan) 0%, transparent 60%), var(--surface)",
                  }}
                />
              )}
              <div className="flex-1 flex flex-col gap-0.5 min-w-0">
                <span className="font-display font-semibold truncate">{item.product.name}</span>
                <span className="text-sm text-text-muted">×{item.quantity}</span>
              </div>
              <span className="font-mono-tabular text-sm">${(item.price / 100).toFixed(2)}</span>
            </li>
          ))}
        </ul>
        <div className="border-t border-border pt-3 flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-sm">
            <span className="text-text-muted">Subtotal</span>
            <span className="font-mono-tabular">${(subtotal / 100).toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-text-muted">
              Shipping{shippingLabel ? ` (${shippingLabel})` : ""}
            </span>
            <span className={`font-mono-tabular ${order.shippingCost === 0 ? "text-success" : ""}`}>
              {order.shippingCost === 0 ? "Free" : `$${(order.shippingCost / 100).toFixed(2)}`}
            </span>
          </div>
          <div className="flex items-center justify-between pt-1">
            <span className="text-sm text-text-muted">Total</span>
            <span className="font-mono-tabular font-medium text-accent-cyan">
              ${(order.totalAmount / 100).toFixed(2)}
            </span>
          </div>
        </div>
      </section>

      <section className="glass-panel rounded-xl p-6 flex flex-col gap-2">
        <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
          SHIPPING ADDRESS
        </h2>
        <p className="text-sm text-text whitespace-pre-wrap">{order.shippingAddr}</p>
        {order.phone && (
          <p className="text-sm text-text-muted">
            Phone: <span className="text-text">{order.phone}</span>
          </p>
        )}
      </section>
    </main>
  );
}
