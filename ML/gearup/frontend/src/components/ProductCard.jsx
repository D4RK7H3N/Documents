import { Link } from "react-router-dom";
import { peso } from "../api.js";

export function stockBadge(stock) {
  if (stock <= 0) return "bg-rose-500/15 text-rose-400 border-rose-500/30";
  if (stock <= 5) return "bg-amber-500/15 text-amber-400 border-amber-500/30";
  return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
}

export function stockLabel(stock) {
  if (stock <= 0) return "Out of stock";
  if (stock <= 5) return `Only ${stock} left`;
  return "In stock";
}

export default function ProductCard({ product }) {
  return (
    <Link
      to={`/products/${product.slug}`}
      className="group flex flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 transition hover:border-slate-600 hover:shadow-lg hover:shadow-black/30"
    >
      <div className="aspect-square w-full overflow-hidden bg-slate-800">
        {product.image ? (
          <img
            src={product.image}
            alt={product.name}
            loading="lazy"
            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-3xl font-bold text-slate-600">
            {product.name.slice(0, 2).toUpperCase()}
          </div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-4">
        <p className="text-xs uppercase tracking-wide text-slate-500">
          {product.category?.name}
          {product.brand ? ` · ${product.brand}` : ""}
        </p>
        <h3 className="line-clamp-2 text-sm font-semibold text-slate-100">
          {product.name}
        </h3>
        <div className="mt-auto flex items-center justify-between pt-2">
          <span className="font-bold text-emerald-400">{peso(product.price)}</span>
          <span
            className={`rounded-full border px-2 py-0.5 text-xs ${stockBadge(product.stock)}`}
          >
            {stockLabel(product.stock)}
          </span>
        </div>
      </div>
    </Link>
  );
}
