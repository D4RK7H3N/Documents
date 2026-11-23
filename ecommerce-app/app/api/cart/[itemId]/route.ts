import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

function requireUser(req: Request) {
  const token = getTokenFromRequest(req);
  return token ? verifyToken(token) : null;
}

const updateSchema = z.object({
  quantity: z.number().int().min(1),
});

export async function PATCH(req: Request, { params }: { params: Promise<{ itemId: string }> }) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { itemId } = await params;

  const item = await prisma.cartItem.findUnique({
    where: { id: itemId },
    include: { cart: true, product: true },
  });
  if (!item || item.cart.userId !== user.userId) {
    return NextResponse.json({ error: "Cart item not found" }, { status: 404 });
  }

  const body = await req.json();
  const parsed = updateSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const { quantity } = parsed.data;

  if (item.product.stock < quantity) {
    return NextResponse.json({ error: "Not enough stock" }, { status: 409 });
  }

  const updated = await prisma.cartItem.update({
    where: { id: itemId },
    data: { quantity },
  });

  return NextResponse.json({ item: updated });
}

export async function DELETE(req: Request, { params }: { params: Promise<{ itemId: string }> }) {
  const user = requireUser(req);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { itemId } = await params;

  const item = await prisma.cartItem.findUnique({
    where: { id: itemId },
    include: { cart: true },
  });
  if (!item || item.cart.userId !== user.userId) {
    return NextResponse.json({ error: "Cart item not found" }, { status: 404 });
  }

  await prisma.cartItem.delete({ where: { id: itemId } });
  return NextResponse.json({ ok: true });
}
