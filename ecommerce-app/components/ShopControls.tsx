"use client";

import { useRouter } from "next/navigation";

export default function ShopControls({
  sort,
  inStock,
  category,
  q,
  total,
}: {
  sort: string;
  inStock: boolean;
  category?: string;
  q?: string;
  total: number;
}) {
  const router = useRouter();

  function update(patch: { sort?: string; inStock?: boolean }) {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (q) params.set("q", q);
    if (patch.sort && patch.sort !== "newest") params.set("sort", patch.sort);
    if (patch.inStock) params.set("inStock", "1");
    router.replace(params.toString() ? `/?${params.toString()}` : "/", {
      scroll: false,
    });
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-text-muted">
        {total} {total === 1 ? "product" : "products"}
      </p>

      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-sm text-text-muted cursor-pointer select-none">
          <input
            type="checkbox"
            checked={inStock}
            onChange={(e) => update({ inStock: e.target.checked })}
            className="w-4 h-4 accent-accent-cyan"
          />
          In stock only
        </label>

        <select
          value={sort}
          onChange={(e) => update({ sort: e.target.value })}
          className="input-field rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
          aria-label="Sort products"
        >
          <option value="newest">Newest</option>
          <option value="price-asc">Price: low → high</option>
          <option value="price-desc">Price: high → low</option>
          <option value="name">Name A–Z</option>
        </select>
      </div>
    </div>
  );
}
