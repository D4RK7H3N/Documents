import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;

  if (!payload) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (payload.role !== "ADMIN") {
    return Response.json({ error: "Forbidden" }, { status: 403 });
  }

  const order = await prisma.order.findUnique({
    where: { id },
    include: {
      user: { select: { name: true, email: true } },
      items: { include: { product: true } },
    },
  });

  if (!order) {
    return Response.json({ error: "Order not found" }, { status: 404 });
  }

  const subtotal = order.items.reduce((sum, i) => sum + i.price * i.quantity, 0);
  const paid = order.status !== "CANCELLED" && order.status !== "PENDING";

  return Response.json({
    invoice: {
      invoiceNumber: `INV-${order.id.slice(0, 8).toUpperCase()}`,
      generatedAt: new Date().toISOString(),
      order: {
        id: order.id,
        createdAt: order.createdAt,
        status: order.status,
        trackingNumber: order.trackingNumber,
      },
      customer: {
        name: order.user.name,
        email: order.user.email,
      },
      shippingAddress: order.shippingAddr,
      shippingMethod: order.shippingMethod,
      shippingCost: order.shippingCost,
      items: order.items.map((i) => ({
        name: i.product.name,
        quantity: i.quantity,
        unitPrice: i.price,
        lineTotal: i.price * i.quantity,
      })),
      subtotal,
      total: order.totalAmount,
      amountDue: paid ? 0 : order.totalAmount,
      paymentStatus: paid ? "PAID" : order.status,
    },
  });
}
