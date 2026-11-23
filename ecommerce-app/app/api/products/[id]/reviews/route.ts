import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";
import { notifyAdmins } from "@/lib/notify";

export const dynamic = "force-dynamic";

const reviewSchema = z.object({
  rating: z.number().int().min(1).max(5),
  comment: z.string().trim().max(1000).optional().nullable(),
});

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const token = getTokenFromRequest(_req);
  const payload = token ? verifyToken(token) : null;

  const reviews = await prisma.review.findMany({
    where: { productId: id },
    orderBy: { createdAt: "desc" },
    select: {
      id: true,
      rating: true,
      comment: true,
      createdAt: true,
      userId: true,
      user: { select: { name: true } },
    },
  });

  return Response.json({
    reviews: reviews.map((r) => ({
      id: r.id,
      rating: r.rating,
      comment: r.comment,
      createdAt: r.createdAt,
      userName: r.user.name,
      isOwn: payload ? r.userId === payload.userId : false,
    })),
  });
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;

  if (!payload) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const product = await prisma.product.findUnique({ where: { id } });
  if (!product) {
    return Response.json({ error: "Product not found" }, { status: 404 });
  }

  const parsed = reviewSchema.safeParse(await req.json().catch(() => ({})));
  if (!parsed.success) {
    return Response.json(
      { error: parsed.error.flatten() },
      { status: 400 },
    );
  }

  const existing = await prisma.review.findUnique({
    where: { productId_userId: { productId: id, userId: payload.userId } },
  });
  if (existing) {
    return Response.json(
      { error: "You already reviewed this product" },
      { status: 409 },
    );
  }

  const review = await prisma.review.create({
    data: {
      productId: id,
      userId: payload.userId,
      rating: parsed.data.rating,
      comment: parsed.data.comment || null,
    },
  });

  notifyAdmins(
    "NEW_REVIEW",
    `New ${parsed.data.rating}-star review on ${product.name}`,
    "/admin/reviews",
  ).catch(() => {});

  return Response.json({ review }, { status: 201 });
}
