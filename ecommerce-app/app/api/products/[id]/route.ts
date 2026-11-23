import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

const productSchema = z.object({
  name: z.string().min(1),
  description: z.string().min(1),
  price: z.number().int().positive(),
  salePrice: z.number().int().positive().nullable().optional(),
  saleEndsAt: z.string().datetime().nullable().optional(),
  imageUrl: z.string().url().optional(),
  stock: z.number().int().min(0).default(0),
  categoryId: z.string().nullable().optional(),
});

function isAdmin(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  return payload !== null && payload.role === "ADMIN";
}

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const product = await prisma.product.findUnique({ where: { id } });
  if (!product) return NextResponse.json({ error: "Product not found" }, { status: 404 });

  return NextResponse.json({ product });
}

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  if (!isAdmin(req)) {
    return NextResponse.json({ error: "Admin access required" }, { status: 403 });
  }

  const { id } = await params;

  const existing = await prisma.product.findUnique({ where: { id } });
  if (!existing) return NextResponse.json({ error: "Product not found" }, { status: 404 });

  const body = await req.json();
  const parsed = productSchema.partial().safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }

  const { salePrice, saleEndsAt, ...rest } = parsed.data;
  const data = {
    ...rest,
    ...(salePrice !== undefined ? { salePrice: salePrice ?? null } : {}),
    ...(saleEndsAt !== undefined
      ? { saleEndsAt: saleEndsAt ? new Date(saleEndsAt) : null }
      : {}),
  };

  const product = await prisma.product.update({ where: { id }, data });

  const restocked =
    parsed.data.stock !== undefined && parsed.data.stock > 0 && existing.stock === 0;
  if (restocked) {
    const wishlistItems = await prisma.wishlistItem.findMany({
      where: { productId: id },
      select: { userId: true },
    });
    if (wishlistItems.length > 0) {
      await prisma.notification.createMany({
        data: wishlistItems.map((w) => ({
          userId: w.userId,
          type: "BACK_IN_STOCK",
          message: `${product.name} is back in stock`,
          link: `/products/${id}`,
        })),
      });
    }
  }

  return NextResponse.json({ product });
}

export async function DELETE(req: Request, { params }: { params: Promise<{ id: string }> }) {
  if (!isAdmin(req)) {
    return NextResponse.json({ error: "Admin access required" }, { status: 403 });
  }

  const { id } = await params;

  const existing = await prisma.product.findUnique({ where: { id } });
  if (!existing) return NextResponse.json({ error: "Product not found" }, { status: 404 });

  const orderItemCount = await prisma.orderItem.count({ where: { productId: id } });
  if (orderItemCount > 0) {
    return NextResponse.json(
      { error: "Cannot delete product: it appears in past orders" },
      { status: 409 }
    );
  }

  const cartItemCount = await prisma.cartItem.count({ where: { productId: id } });
  if (cartItemCount > 0) {
    return NextResponse.json(
      { error: "Cannot delete product: it is in users' carts" },
      { status: 409 }
    );
  }

  await prisma.product.delete({ where: { id } });
  return NextResponse.json({ ok: true });
}
