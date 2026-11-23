import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

export const dynamic = "force-dynamic";

function requireAdmin(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  return payload !== null && payload.role === "ADMIN" ? payload : null;
}

function csvEscape(value: string | number | null | undefined): string {
  const s = value == null ? "" : String(value);
  return `"${s.replace(/"/g, '""')}"`;
}

export async function GET(req: Request) {
  if (!requireAdmin(req)) {
    return Response.json({ error: "Admin access required" }, { status: 403 });
  }

  const orders = await prisma.order.findMany({
    orderBy: { createdAt: "desc" },
    include: { user: { select: { email: true, name: true } }, items: { include: { product: { select: { name: true } } } } },
  });

  const header = [
    "orderId", "createdAt", "customer", "email", "status",
    "item", "quantity", "unitPrice", "shipping", "total",
  ];

  const rows: (string | number)[][] = [];
  for (const o of orders) {
    if (o.items.length === 0) {
      rows.push([o.id, o.createdAt.toISOString(), o.user.name, o.user.email, o.status, "", 0, "", (o.shippingCost ?? 0) / 100, (o.totalAmount ?? 0) / 100]);
      continue;
    }
    for (const item of o.items) {
      rows.push([
        o.id,
        o.createdAt.toISOString(),
        o.user.name,
        o.user.email,
        o.status,
        item.product?.name ?? item.productId,
        item.quantity,
        (item.price / 100).toFixed(2),
        (o.shippingCost ?? 0) / 100,
        (o.totalAmount ?? 0) / 100,
      ]);
    }
  }

  const csv = [header, ...rows]
    .map((row) => row.map(csvEscape).join(","))
    .join("\r\n");

  const bom = "\uFEFF";
  return new Response(bom + csv, {
    status: 200,
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="orders-${new Date().toISOString().slice(0, 10)}.csv"`,
    },
  });
}
