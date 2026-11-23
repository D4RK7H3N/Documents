import { NextResponse } from "next/server";
import Stripe from "stripe";
import { prisma } from "@/lib/prisma";
import { notifyUser } from "@/lib/notify";

export async function POST(req: Request) {
  const stripeSecret = process.env.STRIPE_SECRET_KEY;
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!stripeSecret || !webhookSecret) {
    return NextResponse.json(
      { error: "Stripe webhook is not configured" },
      { status: 503 },
    );
  }

  const stripe = new Stripe(stripeSecret);

  const sig = req.headers.get("stripe-signature");
  if (!sig) return NextResponse.json({ error: "Missing signature" }, { status: 400 });

  const rawBody = await req.text();

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, sig, webhookSecret);
  } catch {
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;
    if (session.payment_status === "paid") {
      const orderId = session.metadata?.orderId;
      if (orderId) {
        const order = await prisma.order.findUnique({ where: { id: orderId } });
        if (order && order.status === "PENDING") {
          await prisma.$transaction([
            prisma.order.update({
              where: { id: orderId },
              data: {
                status: "PAID",
                ...(typeof session.payment_intent === "string"
                  ? { stripePaymentIntentId: session.payment_intent }
                  : {}),
              },
            }),
            prisma.orderEvent.create({ data: { orderId, status: "PAID" } }),
          ]);
          notifyUser(
            order.userId,
            "ORDER_PAID",
            `Payment confirmed for order #${orderId.slice(0, 8)}`,
            `/orders/${orderId}`,
          ).catch(() => {});
        }
      }
    }
  }

  return NextResponse.json({ received: true });
}
