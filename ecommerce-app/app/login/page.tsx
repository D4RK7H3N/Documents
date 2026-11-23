import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";
import LoginForm from "@/components/LoginForm";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  const user = token ? verifyToken(token) : null;

  if (user) redirect("/");

  const [categories, productCount] = await Promise.all([
    prisma.category.findMany({ select: { name: true }, orderBy: { name: "asc" } }),
    prisma.product.count(),
  ]);

  return (
    <LoginForm
      categories={categories.map((c) => c.name)}
      productCount={productCount}
    />
  );
}
