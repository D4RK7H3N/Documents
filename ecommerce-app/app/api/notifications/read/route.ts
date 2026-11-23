import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

export const dynamic = "force-dynamic";

const readSchema = z.object({
  id: z.string().min(1).optional(),
});

export async function POST(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  if (!payload) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const parsed = readSchema.safeParse(await req.json().catch(() => ({})));
  if (!parsed.success) {
    return Response.json({ error: parsed.error.flatten() }, { status: 400 });
  }

  if (parsed.data.id) {
    await prisma.notification.updateMany({
      where: { id: parsed.data.id, userId: payload.userId },
      data: { readAt: new Date() },
    });
  } else {
    await prisma.notification.updateMany({
      where: { userId: payload.userId, readAt: null },
      data: { readAt: new Date() },
    });
  }

  return Response.json({ ok: true });
}