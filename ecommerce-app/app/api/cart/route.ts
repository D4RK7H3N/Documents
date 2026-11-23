import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

function requireUser(req: Request) {
  const token = getTokenFromRequest(req);
  return token ? verifyToken(token) : null;
}

export async function GET(req: Request) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ cart: null });

  const cart = await prisma.cart.findUnique({
    where: { userId: user.userId },
    include: { items: { include: { product: true } } },
  });

  return NextResponse.json({ cart });
}

const addItemSchema = z.object({
  productId: z.string(),
  quantity: z.number().int().positive().default(1),
});

export async function POST(req: Request) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();
  const parsed = addItemSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const { productId, quantity } = parsed.data;

  const product = await prisma.product.findUnique({ where: { id: productId } });
  if (!product) return NextResponse.json({ error: "Product not found" }, { status: 404 });
  if (product.stock < quantity) {
    return NextResponse.json({ error: "Not enough stock" }, { status: 409 });
  }

  const cart = await prisma.cart.upsert({
    where: { userId: user.userId },
    create: { userId: user.userId },
    update: {},
  });

  const item = await prisma.cartItem.upsert({
    where: { cartId_productId: { cartId: cart.id, productId } },
    create: { cartId: cart.id, productId, quantity },
    update: { quantity: { increment: quantity } },
  });

  return NextResponse.json({ item }, { status: 201 });
}
