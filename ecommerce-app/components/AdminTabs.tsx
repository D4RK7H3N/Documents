import Link from "next/link";

const TABS: { href: string; label: string; exact?: boolean }[] = [
  { href: "/admin", label: "Dashboard", exact: true },
  { href: "/admin/products", label: "Products" },
  { href: "/admin/orders", label: "Orders" },
  { href: "/admin/categories", label: "Categories" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/reviews", label: "Reviews" },
  { href: "/admin/wishlists", label: "Wishlists" },
];

export default function AdminTabs({ active }: { active: string }) {
  return (
    <div className="flex flex-wrap gap-2">
      {TABS.map((t) => {
        const isActive = t.exact ? active === t.href : active.startsWith(t.href);
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
              isActive
                ? "btn-primary"
                : "btn-ghost hover:bg-surface-hover"
            }`}
          >
            {t.label}
          </Link>
        );
      })}
    </div>
  );
}