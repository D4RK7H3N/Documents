import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";
import { z } from "zod";

export const dynamic = "force-dynamic";

function requireAdmin(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  return payload !== null && payload.role === "ADMIN" ? payload : null;
}

const bulkSchema = z.discriminatedUnion("action", [
  z.object({ action: z.literal("delete"), ids: z.array(z.string().min(1)).min(1) }),
  z.object({
    action: z.literal("setStock"),
    ids: z.array(z.string().min(1)).min(1),
    stock: z.number().int().min(0),
  }),
]);

export async function POST(req: Request) {
  if (!requireAdmin(req)) {
    return Response.json({ error: "Admin access required" }, { status: 403 });
  }

  const body = await req.json();
  const parsed = bulkSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json({ error: parsed.error.flatten() }, { status: 400 });
  }

  const { action, ids } = parsed.data;

  if (action === "setStock") {
    await prisma.product.updateMany({
      where: { id: { in: ids } },
      data: { stock: parsed.data.stock },
    });
    return Response.json({ ok: true, updated: ids.length });
  }

  const [orderItems, cartItems] = await Promise.all([
    prisma.orderItem.count({ where: { productId: { in: ids } } }),
    prisma.cartItem.count({ where: { productId: { in: ids } } }),
  ]);
  if (orderItems > 0 || cartItems > 0) {
    return Response.json(
      {
        error:
          "Cannot delete: some products appear in orders or carts. Delete them individually.",
      },
      { status: 409 },
    );
  }

  const result = await prisma.product.deleteMany({ where: { id: { in: ids } } });
  return Response.json({ ok: true, deleted: result.count });
}
