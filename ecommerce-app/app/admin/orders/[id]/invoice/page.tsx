import Link from "next/link";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";
import InvoicePrintButton from "@/components/InvoicePrintButton";

export const dynamic = "force-dynamic";

export default async function InvoicePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  const payload = token ? verifyToken(token) : null;

  if (!payload) redirect("/login");
  if (payload.role !== "ADMIN") redirect("/");

  const order = await prisma.order.findUnique({
    where: { id },
    include: {
      user: { select: { name: true, email: true } },
      items: { include: { product: true } },
    },
  });

  if (!order) notFound();

  const subtotal = order.items.reduce((sum, i) => sum + i.price * i.quantity, 0);
  const paid = order.status !== "CANCELLED" && order.status !== "PENDING";
  const invoiceNumber = `INV-${order.id.slice(0, 8).toUpperCase()}`;
  const shippingLabel =
    order.shippingMethod === "EXPRESS"
      ? "Express"
      : order.shippingMethod === "STANDARD"
        ? "Standard"
        : "—";

  return (
    <main className="max-w-3xl mx-auto p-6 flex flex-col gap-4 print:p-0">
      <div className="flex items-center justify-between print:hidden">
        <Link
          href={`/admin/orders/${order.id}`}
          className="text-sm text-text-muted hover:text-text transition-colors"
        >
          ← Back to order
        </Link>
        <InvoicePrintButton />
      </div>

      <section className="glass-panel rounded-xl p-8 flex flex-col gap-8">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <span className="font-display font-bold tracking-[0.2em] bg-gradient-to-r from-accent-cyan to-accent-pink bg-clip-text text-transparent">
              CLICKBOUND
            </span>
            <span className="font-mono-tabular text-xs text-text-muted">
              INVOICE · {invoiceNumber}
            </span>
          </div>
          <div className="text-right flex flex-col gap-1">
            <span className="text-sm text-text-muted">
              Issued {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
            </span>
            <span className="text-sm text-text-muted">
              Order #{order.id.slice(0, 8)}
            </span>
            <span className="font-mono-tabular text-xs text-text-muted">
              {new Date(order.createdAt).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
            </span>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-6">
          <div className="flex flex-col gap-1">
            <span className="font-mono-tabular text-xs tracking-[0.25em] uppercase text-text-muted">
              Billed to
            </span>
            <span className="font-display font-semibold">{order.user.name}</span>
            <span className="text-sm text-text-muted">{order.user.email}</span>
            <span className="text-sm text-text whitespace-pre-wrap">{order.shippingAddr}</span>
            {order.phone && (
              <span className="text-sm text-text-muted">Phone: {order.phone}</span>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <span className="font-mono-tabular text-xs tracking-[0.25em] uppercase text-text-muted">
              Shipping
            </span>
            <span className="text-sm">{shippingLabel}</span>
            {order.trackingNumber && (
              <span className="font-mono-tabular text-sm text-accent-cyan">
                {order.trackingNumber}
              </span>
            )}
            <span className="text-sm text-text-muted">
              Status: {order.status}
            </span>
          </div>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-muted border-b border-border">
              <th className="pb-2 font-medium">Item</th>
              <th className="pb-2 font-medium text-right">Qty</th>
              <th className="pb-2 font-medium text-right">Unit</th>
              <th className="pb-2 font-medium text-right">Line total</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((i) => (
              <tr key={i.id} className="border-b border-border/50">
                <td className="py-2.5">{i.product.name}</td>
                <td className="py-2.5 text-right font-mono-tabular">{i.quantity}</td>
                <td className="py-2.5 text-right font-mono-tabular">${(i.price / 100).toFixed(2)}</td>
                <td className="py-2.5 text-right font-mono-tabular">${((i.price * i.quantity) / 100).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex flex-col gap-1.5 items-end">
          <div className="flex justify-between gap-12 text-sm">
            <span className="text-text-muted">Subtotal</span>
            <span className="font-mono-tabular">${(subtotal / 100).toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-12 text-sm">
            <span className="text-text-muted">Shipping ({shippingLabel})</span>
            <span className={`font-mono-tabular ${order.shippingCost === 0 ? "text-success" : ""}`}>
              {order.shippingCost === 0 ? "Free" : `$${(order.shippingCost / 100).toFixed(2)}`}
            </span>
          </div>
          <div className="flex justify-between gap-12 border-t border-border pt-2">
            <span className="font-display font-semibold">Total</span>
            <span className="font-mono-tabular text-lg font-medium text-accent-cyan">
              ${(order.totalAmount / 100).toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between gap-12 text-sm">
            <span className="text-text-muted">Amount due</span>
            <span className={`font-mono-tabular font-medium ${paid ? "text-success" : "text-danger"}`}>
              {paid ? "$0.00 — paid" : `$${(order.totalAmount / 100).toFixed(2)}`}
            </span>
          </div>
        </div>
      </section>
    </main>
  );
}
