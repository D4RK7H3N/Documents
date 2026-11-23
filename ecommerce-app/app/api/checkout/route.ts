import { NextResponse } from "next/server";
import { z } from "zod";
import Stripe from "stripe";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";
import { getShippingMethod, calcShippingCost } from "@/lib/shipping";
import { notifyUser, notifyAdmins } from "@/lib/notify";
import { effectivePrice } from "@/lib/pricing";

function requireUser(req: Request) {
  const token = getTokenFromRequest(req);
  return token ? verifyToken(token) : null;
}

const checkoutSchema = z.object({
  shippingAddr: z.string().trim().min(1, "Shipping address is required"),
  phone: z.string().trim().min(7, "Enter a valid phone number").max(20, "Phone number is too long"),
  shippingMethod: z.enum(["STANDARD", "EXPRESS"]).default("STANDARD"),
});

const stripeSecret = process.env.STRIPE_SECRET_KEY;
const stripe = stripeSecret ? new Stripe(stripeSecret) : null;

class StockShortageError extends Error {
  constructor(
    public productId: string,
    public name: string,
    public requested: number,
    public available: number,
  ) {
    super("STOCK_SHORTAGE");
  }
}

export async function POST(req: Request) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();
  const parsed = checkoutSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const { shippingAddr, phone, shippingMethod } = parsed.data;

  const shipping = getShippingMethod(shippingMethod);
  if (!shipping) {
    return NextResponse.json({ error: "Unknown shipping method" }, { status: 400 });
  }

  const cart = await prisma.cart.findUnique({
    where: { userId: user.userId },
    include: { items: { include: { product: true } } },
  });

  if (!cart || cart.items.length === 0) {
    return NextResponse.json({ error: "Cart is empty" }, { status: 400 });
  }

  const outOfStock = cart.items.filter((i) => i.product.stock < i.quantity);
  if (outOfStock.length > 0) {
    return NextResponse.json(
      {
        error: "Not enough stock for some items",
        items: outOfStock.map((i) => ({
          productId: i.productId,
          name: i.product.name,
          requested: i.quantity,
          available: i.product.stock,
        })),
      },
      { status: 409 }
    );
  }

  const subtotal = cart.items.reduce(
    (sum, i) => sum + effectivePrice(i.product) * i.quantity,
    0
  );
  const shippingCost = calcShippingCost(shipping, subtotal);
  const totalAmount = subtotal + shippingCost;

  let order: Awaited<ReturnType<typeof prisma.order.create>>;
  try {
    order = await prisma.$transaction(async (tx) => {
      // Reserve stock with a conditional decrement inside the transaction so
      // concurrent checkouts can't both pass a stale stock check. Any shortfall
      // aborts the whole order.
      for (const i of cart.items) {
        const reserved = await tx.product.updateMany({
          where: { id: i.productId, stock: { gte: i.quantity } },
          data: { stock: { decrement: i.quantity } },
        });
        if (reserved.count !== 1) {
          throw new StockShortageError(
            i.productId,
            i.product.name,
            i.quantity,
            Math.max(0, i.product.stock),
          );
        }
      }

      const created = await tx.order.create({
        data: {
          userId: user.userId,
          status: "PENDING",
          totalAmount,
          shippingAddr,
          phone,
          shippingMethod,
          shippingCost,
          items: {
            create: cart.items.map((i) => ({
              productId: i.productId,
              quantity: i.quantity,
              price: effectivePrice(i.product),
            })),
          },
        },
        include: { items: { include: { product: true } } },
      });

      await tx.cartItem.deleteMany({ where: { cartId: cart.id } });

      await tx.orderEvent.create({
        data: { orderId: created.id, status: "PENDING" },
      });

      return created;
    });
  } catch (err) {
    if (err instanceof StockShortageError) {
      return NextResponse.json(
        {
          error: "Not enough stock for some items",
          items: [
            {
              productId: err.productId,
              name: err.name,
              requested: err.requested,
              available: err.available,
            },
          ],
        },
        { status: 409 }
      );
    }
    throw err;
  }

  const orderShortId = order.id.slice(0, 8);
  notifyUser(
    order.userId,
    "ORDER_PLACED",
    `Order #${orderShortId} placed`,
    `/orders/${order.id}`,
  ).catch(() => {});
  notifyAdmins(
    "NEW_ORDER",
    `New order #${orderShortId} — $${(order.totalAmount / 100).toFixed(2)}`,
    `/admin/orders/${order.id}`,
  ).catch(() => {});
  const lowStock = cart.items.filter(
    (i) => i.product.stock - i.quantity <= 3,
  );
  for (const i of lowStock) {
    notifyAdmins(
      "LOW_STOCK",
      `${i.product.name} is low on stock (${Math.max(0, i.product.stock - i.quantity)} left)`,
      "/admin/products",
    ).catch(() => {});
  }

  if (!stripe) {
    return NextResponse.json({ order, sessionUrl: null }, { status: 201 });
  }

  const origin = new URL(req.url).origin;

  let sessionUrl: string | null = null;
  try {
    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      line_items: [
        ...cart.items.map((i) => ({
          quantity: i.quantity,
          price_data: {
            currency: "usd",
            unit_amount: effectivePrice(i.product),
            product_data: {
              name: i.product.name,
              images: i.product.imageUrl ? [i.product.imageUrl] : undefined,
            },
          },
        })),
        ...(shippingCost > 0
          ? [
              {
                quantity: 1,
                price_data: {
                  currency: "usd",
                  unit_amount: shippingCost,
                  product_data: {
                    name: `Shipping — ${shipping.label}`,
                  },
                },
              },
            ]
          : []),
      ],
      success_url: `${origin}/orders?success=true`,
      cancel_url: `${origin}/cart`,
      metadata: { orderId: order.id, userId: user.userId },
    });
    sessionUrl = session.url;
  } catch {
    await prisma.$transaction(async (tx) => {
      await tx.orderEvent.deleteMany({ where: { orderId: order.id } });
      await tx.order.delete({ where: { id: order.id } });
      for (const i of cart.items) {
        await tx.product.update({
          where: { id: i.productId },
          data: { stock: { increment: i.quantity } },
        });
      }
      await tx.cartItem.createMany({
        data: cart.items.map((i) => ({
          cartId: cart.id,
          productId: i.productId,
          quantity: i.quantity,
        })),
      });
    });
    return NextResponse.json({ error: "Payment is not configured correctly" }, { status: 500 });
  }

  return NextResponse.json({ order, sessionUrl }, { status: 201 });
}
