import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

export const dynamic = "force-dynamic";

function requireAdmin(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  return payload !== null && payload.role === "ADMIN" ? payload : null;
}

export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const admin = requireAdmin(req);
  if (!admin) {
    return Response.json({ error: "Admin access required" }, { status: 403 });
  }

  const { id } = await params;

  const existing = await prisma.wishlistItem.findUnique({ where: { id } });
  if (!existing) {
    return Response.json({ error: "Wishlist item not found" }, { status: 404 });
  }

  await prisma.wishlistItem.delete({ where: { id } });
  return Response.json({ ok: true });
}