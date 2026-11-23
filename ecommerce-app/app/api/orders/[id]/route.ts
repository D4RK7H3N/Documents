import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";
import { notifyUser } from "@/lib/notify";

type OrderStatus = "PENDING" | "PAID" | "SHIPPED" | "DELIVERED" | "CANCELLED";

const ORDER_FLOW: OrderStatus[] = ["PENDING", "PAID", "SHIPPED", "DELIVERED", "CANCELLED"];

function requireUser(req: Request) {
  const token = getTokenFromRequest(req);
  return token ? verifyToken(token) : null;
}

function isAdmin(req: Request) {
  const user = requireUser(req);
  return user !== null && user.role === "ADMIN";
}

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;

  const order = await prisma.order.findUnique({
    where: { id },
    include: {
      items: { include: { product: true } },
      events: { orderBy: { createdAt: "asc" } },
      user: { select: { email: true } },
    },
  });

  if (!order || (order.userId !== user.userId && user.role !== "ADMIN")) {
    return NextResponse.json({ error: "Order not found" }, { status: 404 });
  }

  return NextResponse.json({ order });
}

const updateSchema = z.object({
  status: z.enum(["PENDING", "PAID", "SHIPPED", "DELIVERED", "CANCELLED"]).optional(),
  trackingNumber: z.string().trim().min(1).optional(),
  note: z.string().trim().min(1).optional(),
  shippingAddr: z.string().trim().min(1).optional(),
  phone: z.string().trim().min(7).max(20).optional(),
});

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  if (!isAdmin(req)) {
    return NextResponse.json({ error: "Admin access required" }, { status: 403 });
  }

  const { id } = await params;

  const existing = await prisma.order.findUnique({ where: { id } });
  if (!existing) return NextResponse.json({ error: "Order not found" }, { status: 404 });

  const body = await req.json();
  const parsed = updateSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const { status, trackingNumber, note, shippingAddr, phone } = parsed.data;

  const data: {
    status?: OrderStatus;
    trackingNumber?: string;
    shippingAddr?: string;
    phone?: string;
  } = {};
  if (trackingNumber !== undefined) data.trackingNumber = trackingNumber;
  if (shippingAddr !== undefined) data.shippingAddr = shippingAddr;
  if (phone !== undefined) data.phone = phone;

  const statusChanged = status !== undefined && status !== existing.status;

  if (statusChanged) {
    if (status === "CANCELLED") {
      return NextResponse.json(
        { error: "Use the cancel action to cancel an order" },
        { status: 400 }
      );
    }
    const oldIndex = ORDER_FLOW.indexOf(existing.status);
    const newIndex = ORDER_FLOW.indexOf(status);
    if (newIndex < oldIndex) {
      return NextResponse.json(
        { error: `Cannot move order from ${existing.status} to ${status}` },
        { status: 409 }
      );
    }
    if (status === "SHIPPED" && !(data.trackingNumber ?? existing.trackingNumber)) {
      return NextResponse.json(
        { error: "Tracking number is required when shipping an order" },
        { status: 400 }
      );
    }
    data.status = status;
  }

  const order = await prisma.$transaction(async (tx) => {
    await tx.order.update({ where: { id }, data });

    if (statusChanged) {
      await tx.orderEvent.create({ data: { orderId: id, status: status as OrderStatus, note } });
    }

    return tx.order.findUnique({
      where: { id },
      include: {
        items: { include: { product: true } },
        events: { orderBy: { createdAt: "asc" } },
        user: { select: { email: true } },
      },
    });
  });

  const orderShortId = id.slice(0, 8);
  if (statusChanged && existing.userId) {
    if (status === "SHIPPED") {
      notifyUser(
        existing.userId,
        "ORDER_SHIPPED",
        `Order #${orderShortId} is on its way (${data.trackingNumber ?? existing.trackingNumber})`,
        `/orders/${id}`,
      ).catch(() => {});
    } else if (status === "DELIVERED") {
      notifyUser(
        existing.userId,
        "ORDER_DELIVERED",
        `Order #${orderShortId} has been delivered`,
        `/orders/${id}`,
      ).catch(() => {});
    } else if (status === "PAID") {
      notifyUser(
        existing.userId,
        "ORDER_PAID",
        `Payment confirmed for order #${orderShortId}`,
        `/orders/${id}`,
      ).catch(() => {});
    }
  }

  return NextResponse.json({ order });
}
