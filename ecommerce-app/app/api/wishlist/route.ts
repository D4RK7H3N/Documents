import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

export const dynamic = "force-dynamic";

const wishlistSchema = z.object({
  productId: z.string().min(1),
});

function getAuth(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  return payload;
}

export async function GET(req: Request) {
  const payload = getAuth(req);
  if (!payload) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const items = await prisma.wishlistItem.findMany({
    where: { userId: payload.userId },
    select: { productId: true },
  });

  return Response.json({ ids: items.map((i) => i.productId) });
}

export async function POST(req: Request) {
  const payload = getAuth(req);
  if (!payload) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const parsed = wishlistSchema.safeParse(await req.json().catch(() => ({})));
  if (!parsed.success) {
    return Response.json({ error: parsed.error.flatten() }, { status: 400 });
  }

  const product = await prisma.product.findUnique({
    where: { id: parsed.data.productId },
  });
  if (!product) {
    return Response.json({ error: "Product not found" }, { status: 404 });
  }

  const item = await prisma.wishlistItem.upsert({
    where: {
      productId_userId: {
        productId: parsed.data.productId,
        userId: payload.userId,
      },
    },
    update: {},
    create: { productId: parsed.data.productId, userId: payload.userId },
  });

  return Response.json({ id: item.id }, { status: 201 });
}

export async function DELETE(req: Request) {
  const payload = getAuth(req);
  if (!payload) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const parsed = wishlistSchema.safeParse(await req.json().catch(() => ({})));
  if (!parsed.success) {
    return Response.json({ error: parsed.error.flatten() }, { status: 400 });
  }

  await prisma.wishlistItem.deleteMany({
    where: {
      productId: parsed.data.productId,
      userId: payload.userId,
    },
  });

  return Response.json({ ok: true });
}
