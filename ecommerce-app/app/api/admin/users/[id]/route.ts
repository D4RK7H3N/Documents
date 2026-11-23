import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

export const dynamic = "force-dynamic";

function requireAdmin(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  return payload !== null && payload.role === "ADMIN" ? payload : null;
}

const updateSchema = z.object({
  name: z.string().trim().min(2).optional(),
  email: z.string().email().optional(),
  role: z.enum(["CUSTOMER", "ADMIN"]).optional(),
});

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const admin = requireAdmin(req);
  if (!admin) {
    return Response.json({ error: "Admin access required" }, { status: 403 });
  }

  const { id } = await params;
  if (id === admin.userId) {
    return Response.json(
      { error: "Edit your own profile from the Account page" },
      { status: 400 },
    );
  }

  const parsed = updateSchema.safeParse(await req.json().catch(() => ({})));
  if (!parsed.success) {
    return Response.json({ error: parsed.error.flatten() }, { status: 400 });
  }

  const existing = await prisma.user.findUnique({ where: { id } });
  if (!existing) {
    return Response.json({ error: "User not found" }, { status: 404 });
  }

  const data: { name?: string; email?: string; role?: "CUSTOMER" | "ADMIN" } = {};
  if (parsed.data.name) data.name = parsed.data.name;
  if (parsed.data.email && parsed.data.email !== existing.email) {
    const taken = await prisma.user.findUnique({
      where: { email: parsed.data.email },
    });
    if (taken) {
      return Response.json({ error: "Email already registered" }, { status: 409 });
    }
    data.email = parsed.data.email;
  }
  if (parsed.data.role) data.role = parsed.data.role;

  const user = await prisma.user.update({ where: { id }, data });
  return Response.json({ user });
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
  if (id === admin.userId) {
    return Response.json(
      { error: "You can't delete your own account" },
      { status: 400 },
    );
  }

  const orderCount = await prisma.order.count({ where: { userId: id } });
  if (orderCount > 0) {
    return Response.json(
      {
        error: `Cannot delete user: they have ${orderCount} order${
          orderCount > 1 ? "s" : ""
        } in history`,
      },
      { status: 409 },
    );
  }

  await prisma.user.delete({ where: { id } });
  return Response.json({ ok: true });
}