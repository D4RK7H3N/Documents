import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import ProductCard from "../components/ProductCard.jsx";

const SORTS = [
  { value: "newest", label: "Newest" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "name", label: "Name A-Z" },
];

export default function Products() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const category = searchParams.get("category") || "";
  const sort = searchParams.get("sort") || "newest";
  const minPrice = searchParams.get("min_price") || "";
  const maxPrice = searchParams.get("max_price") || "";
  const inStock = searchParams.get("in_stock") === "true";

  const updateParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  };

  useEffect(() => {
    api("/categories/", { auth: false }).then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (sort) params.set("sort", sort);
    if (minPrice) params.set("min_price", minPrice);
    if (maxPrice) params.set("max_price", maxPrice);
    if (inStock) params.set("in_stock", "true");

    api(`/products/?${params.toString()}`, { auth: false })
      .then((data) => {
        if (!cancelled) setProducts(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [category, sort, minPrice, maxPrice, inStock]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold">All products</h1>

      <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900 p-4">
        <select
          value={category}
          onChange={(event) => updateParam("category", event.target.value)}
          aria-label="Category"
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
        >
          <option value="">All categories</option>
          {categories.map((cat) => (
            <option key={cat.slug} value={cat.slug}>
              {cat.name}
            </option>
          ))}
        </select>

        <select
          value={sort}
          onChange={(event) => updateParam("sort", event.target.value)}
          aria-label="Sort by"
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
        >
          {SORTS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <input
            type="number"
            min="0"
            value={minPrice}
            onChange={(event) => updateParam("min_price", event.target.value)}
            placeholder="Min ₱"
            aria-label="Minimum price"
            className="w-24 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          />
          <span className="text-slate-600">–</span>
          <input
            type="number"
            min="0"
            value={maxPrice}
            onChange={(event) => updateParam("max_price", event.target.value)}
            placeholder="Max ₱"
            aria-label="Maximum price"
            className="w-24 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={inStock}
            onChange={(event) => updateParam("in_stock", event.target.checked ? "true" : "")}
            className="h-4 w-4 accent-emerald-500"
          />
          In stock only
        </label>
      </div>

      {error && (
        <p className="mt-4 rounded-lg border border-rose-900 bg-rose-950/60 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      )}

      {loading ? (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {[...Array(8)].map((_, index) => (
            <div key={index} className="aspect-[3/4] animate-pulse rounded-2xl bg-slate-900" />
          ))}
        </div>
      ) : products.length === 0 ? (
        <p className="mt-10 text-center text-slate-500">
          No products match these filters.
        </p>
      ) : (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {products.map((product) => (
            <ProductCard key={product.slug} product={product} />
          ))}
        </div>
      )}
    </div>
  );
}
