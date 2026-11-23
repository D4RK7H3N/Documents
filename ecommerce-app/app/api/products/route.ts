import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q") ?? undefined;
  const idsRaw = searchParams.get("ids");
  const ids = idsRaw ? idsRaw.split(",").map((s) => s.trim()).filter(Boolean) : undefined;
  const limitRaw = searchParams.get("limit");
  const limit = limitRaw ? Math.min(Math.max(parseInt(limitRaw, 10) || 1, 1), 50) : undefined;

  const products = await prisma.product.findMany({
    where: ids
      ? { id: { in: ids } }
      : q
        ? { name: { contains: q, mode: "insensitive" } }
        : undefined,
    orderBy: { createdAt: "desc" },
    ...(limit ? { take: limit } : {}),
  });

  return NextResponse.json({ products });
}

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

export async function POST(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;

  if (!payload || payload.role !== "ADMIN") {
    return NextResponse.json({ error: "Admin access required" }, { status: 403 });
  }

  const body = await req.json();
  const parsed = productSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }

  const { salePrice, saleEndsAt, ...rest } = parsed.data;
  const product = await prisma.product.create({
    data: {
      ...rest,
      salePrice: salePrice ?? null,
      saleEndsAt: saleEndsAt ? new Date(saleEndsAt) : null,
    },
  });
  return NextResponse.json({ product }, { status: 201 });
}
