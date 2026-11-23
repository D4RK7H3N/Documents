import { NextResponse } from "next/server";
import Stripe from "stripe";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";
import { notifyUser, notifyAdmins } from "@/lib/notify";

function requireUser(req: Request) {
  const token = getTokenFromRequest(req);
  return token ? verifyToken(token) : null;
}

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;

  const order = await prisma.order.findUnique({
    where: { id },
    include: { items: true },
  });
  if (!order || (order.userId !== user.userId && user.role !== "ADMIN")) {
    return NextResponse.json({ error: "Order not found" }, { status: 404 });
  }

  if (order.status !== "PENDING" && order.status !== "PAID") {
    return NextResponse.json(
      { error: `Cannot cancel an order that is ${order.status}` },
      { status: 409 }
    );
  }

  const cancelledBy = user.role === "ADMIN" ? "admin" : "customer";

  if (order.status === "PAID") {
    const stripeSecret = process.env.STRIPE_SECRET_KEY;
    if (!stripeSecret) {
      return NextResponse.json(
        { error: "Refunds are not configured" },
        { status: 500 }
      );
    }
    if (!order.stripePaymentIntentId) {
      return NextResponse.json(
        { error: "No payment record found for this order" },
        { status: 500 }
      );
    }
    try {
      const stripe = new Stripe(stripeSecret);
      await stripe.refunds.create({ payment_intent: order.stripePaymentIntentId });
    } catch {
      return NextResponse.json(
        { error: "Refund failed — the order was not cancelled" },
        { status: 502 }
      );
    }
  }

  await prisma.$transaction(async (tx) => {
    await tx.order.update({ where: { id }, data: { status: "CANCELLED" } });

    for (const i of order.items) {
      await tx.product.update({
        where: { id: i.productId },
        data: { stock: { increment: i.quantity } },
      });
    }

    await tx.orderEvent.create({
      data: { orderId: id, status: "CANCELLED", note: `Cancelled by ${cancelledBy}` },
    });
  });

  const updated = await prisma.order.findUnique({
    where: { id },
    include: {
      items: { include: { product: true } },
      events: { orderBy: { createdAt: "asc" } },
    },
  });

  const orderShortId = id.slice(0, 8);
  if (cancelledBy === "admin") {
    notifyUser(
      order.userId,
      "ORDER_CANCELLED",
      `Order #${orderShortId} was cancelled`,
      `/orders/${id}`,
    ).catch(() => {});
  } else {
    notifyAdmins(
      "ORDER_CANCELLED",
      `Order #${orderShortId} was cancelled by the customer`,
      `/admin/orders/${id}`,
    ).catch(() => {});
  }

  return NextResponse.json({ order: updated });
}
