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

export async function GET() {
  const categories = await prisma.category.findMany({
    orderBy: { name: "asc" },
    include: { _count: { select: { products: true } } },
  });
  return NextResponse.json({ categories });
}

const createSchema = z.object({
  name: z.string().trim().min(1),
});

async function uniqueSlug(base: string) {
  let slug = base;
  let n = 2;
  while (await prisma.category.findUnique({ where: { slug } })) {
    slug = `${base}-${n}`;
    n++;
  }
  return slug;
}

export async function POST(req: Request) {
  if (!isAdmin(req)) {
    return NextResponse.json({ error: "Admin access required" }, { status: 403 });
  }

  const body = await req.json();
  const parsed = createSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const { name } = parsed.data;

  const existing = await prisma.category.findUnique({ where: { name } });
  if (existing) {
    return NextResponse.json({ error: "Category already exists" }, { status: 409 });
  }

  const category = await prisma.category.create({
    data: { name, slug: await uniqueSlug(slugify(name)) },
  });

  return NextResponse.json({ category }, { status: 201 });
}
