import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

export const dynamic = "force-dynamic";

function requireAdmin(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  return payload !== null && payload.role === "ADMIN" ? payload : null;
}

export async function GET(req: Request) {
  if (!requireAdmin(req)) {
    return Response.json({ error: "Admin access required" }, { status: 403 });
  }

  const reviews = await prisma.review.findMany({
    orderBy: { createdAt: "desc" },
    select: {
      id: true,
      rating: true,
      comment: true,
      createdAt: true,
      product: { select: { name: true } },
      user: { select: { name: true, email: true } },
    },
  });

  return Response.json({ reviews });
}