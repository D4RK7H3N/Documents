import { prisma } from "@/lib/prisma";
import { getTokenFromRequest, verifyToken } from "@/lib/auth";

export const dynamic = "force-dynamic";

function requireAdmin(req: Request) {
  const token = getTokenFromRequest(req);
  const payload = token ? verifyToken(token) : null;
  return payload !== null && payload.role === "ADMIN" ? payload : null;
}

function csvEscape(value: string | number | null | undefined): string {
  const s = value == null ? "" : String(value);
  return `"${s.replace(/"/g, '""')}"`;
}

export async function GET(req: Request) {
  if (!requireAdmin(req)) {
    return Response.json({ error: "Admin access required" }, { status: 403 });
  }

  const products = await prisma.product.findMany({
    orderBy: { createdAt: "desc" },
    include: { category: { select: { name: true } } },
  });

  const header = ["id", "name", "description", "price", "salePrice", "saleEndsAt", "stock", "category", "imageUrl"];
  const rows = products.map((p) => [
    p.id,
    p.name,
    p.description,
    (p.price / 100).toFixed(2),
    p.salePrice != null ? (p.salePrice / 100).toFixed(2) : "",
    p.saleEndsAt ? p.saleEndsAt.toISOString() : "",
    p.stock,
    p.category?.name ?? "",
    p.imageUrl ?? "",
  ]);

  const csv = [header, ...rows]
    .map((row) => row.map(csvEscape).join(","))
    .join("\r\n");

  const bom = "\uFEFF";
  return new Response(bom + csv, {
    status: 200,
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="products-${new Date().toISOString().slice(0, 10)}.csv"`,
    },
  });
}
