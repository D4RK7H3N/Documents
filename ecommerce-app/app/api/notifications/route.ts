import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  if (!payload) {
    return Response.json({ notifications: [], unread: 0 });
  }

  const notifications = await prisma.notification.findMany({
    where: { userId: payload.userId },
    orderBy: [{ readAt: "asc" }, { createdAt: "desc" }],
    take: 30,
  });

  const unread = await prisma.notification.count({
    where: { userId: payload.userId, readAt: null },
  });

  return Response.json({ notifications, unread });
}