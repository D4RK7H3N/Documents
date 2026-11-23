import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { slugify } from "@/lib/slug";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

function requireUser(req: Request) {
  const token = getTokenFromRequest(req);
  return token ? verifyToken(token) : null;
}

function isAdmin(req: Request) {
  const user = requireUser(req);
  return user !== null && user.role === "ADMIN";
}

const updateSchema = z.object({
  name: z.string().trim().min(1),
});

async function uniqueSlug(base: string, exceptId: string) {
  let slug = base;
  let n = 2;
  while (await prisma.category.findFirst({ where: { slug, NOT: { id: exceptId } } })) {
    slug = `${base}-${n}`;
    n++;
  }
  return slug;
}

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  if (!isAdmin(req)) {
    return NextResponse.json({ error: "Admin access required" }, { status: 403 });
  }

  const { id } = await params;

  const existing = await prisma.category.findUnique({ where: { id } });
  if (!existing) return NextResponse.json({ error: "Category not found" }, { status: 404 });

  const body = await req.json();
  const parsed = updateSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const { name } = parsed.data;

  const taken = await prisma.category.findFirst({ where: { name, NOT: { id } } });
  if (taken) {
    return NextResponse.json({ error: "Category already exists" }, { status: 409 });
  }

  const category = await prisma.category.update({
    where: { id },
    data: { name, slug: await uniqueSlug(slugify(name), id) },
  });

  return NextResponse.json({ category });
}

export async function DELETE(req: Request, { params }: { params: Promise<{ id: string }> }) {
  if (!isAdmin(req)) {
    return NextResponse.json({ error: "Admin access required" }, { status: 403 });
  }

  const { id } = await params;

  const existing = await prisma.category.findUnique({
    where: { id },
    include: { _count: { select: { products: true } } },
  });
  if (!existing) return NextResponse.json({ error: "Category not found" }, { status: 404 });

  if (existing._count.products > 0) {
    return NextResponse.json(
      { error: "Cannot delete category: it still has products" },
      { status: 409 }
    );
  }

  await prisma.category.delete({ where: { id } });
  return NextResponse.json({ ok: true });
}
