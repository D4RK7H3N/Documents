import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";
import AccountForm from "@/components/AccountForm";
import AccountSecurity from "@/components/AccountSecurity";

export const dynamic = "force-dynamic";

export default async function AccountPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  const user = token ? verifyToken(token) : null;

  if (!user) redirect("/login");

  const dbUser = await prisma.user.findUnique({
    where: { id: user.userId },
    select: {
      id: true,
      name: true,
      email: true,
      role: true,
      addressLine: true,
      city: true,
      zipCode: true,
      phone: true,
      emailVerifiedAt: true,
      phoneVerifiedAt: true,
      totpEnabledAt: true,
      createdAt: true,
    },
  });
  if (!dbUser) redirect("/login");

  return (
    <main className="max-w-3xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="font-display text-3xl font-bold">ACCOUNT</h1>
          <p className="text-sm text-text-muted">
            Member since{" "}
            {new Date(dbUser.createdAt).toLocaleDateString("en-US", {
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </p>
        </div>
        <Link
          href="/orders"
          className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors"
        >
          View orders
        </Link>
      </div>

      <div className="glass-panel rounded-xl p-6 flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <span className="font-display font-semibold">{dbUser.name}</span>
          <span className="text-sm text-text-muted">{dbUser.email}</span>
        </div>
        <span
          className={`text-xs px-2.5 py-1 rounded-full font-medium ${
            dbUser.role === "ADMIN"
              ? "bg-accent-pink/10 text-accent-pink border border-accent-pink/30"
              : "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/30"
          }`}
        >
          {dbUser.role}
        </span>
      </div>

      <AccountForm
        user={{
          name: dbUser.name,
          email: dbUser.email,
          addressLine: dbUser.addressLine,
          city: dbUser.city,
          zipCode: dbUser.zipCode,
          phone: dbUser.phone,
        }}
      />

      <AccountSecurity
        email={dbUser.email}
        phone={dbUser.phone}
        emailVerified={!!dbUser.emailVerifiedAt}
        phoneVerified={!!dbUser.phoneVerifiedAt}
        totpEnabled={!!dbUser.totpEnabledAt}
      />
    </main>
  );
}
