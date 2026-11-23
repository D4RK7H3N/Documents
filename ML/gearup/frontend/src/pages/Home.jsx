import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import ProductCard from "../components/ProductCard.jsx";

export default function Home() {
  const [featured, setFeatured] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [products, cats] = await Promise.all([
          api("/products/?featured=true", { auth: false }),
          api("/categories/", { auth: false }),
        ]);
        setFeatured(products);
        setCategories(cats);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10">
      <section className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950/40 p-8 sm:p-12">
        <p className="text-sm font-medium uppercase tracking-widest text-emerald-400">
          Gaming accessories · Philippines
        </p>
        <h1 className="mt-3 max-w-2xl text-3xl font-bold leading-tight sm:text-5xl">
          Level up your setup with AI-powered shopping
        </h1>
        <p className="mt-4 max-w-xl text-slate-400">
          Search by meaning, get smart recommendations, and chat with an assistant that
          only answers from our real catalog.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to="/products"
            className="rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
          >
            Shop now
          </Link>
          <Link
            to="/products?sort=price_asc"
            className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-slate-500"
          >
            Best budget picks
          </Link>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="mb-4 text-lg font-semibold">Categories</h2>
        <div className="flex flex-wrap gap-2">
          {categories.map((category) => (
            <Link
              key={category.slug}
              to={`/products?category=${category.slug}`}
              className="rounded-full border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-300 transition hover:border-emerald-500 hover:text-emerald-300"
            >
              {category.name}{" "}
              <span className="text-slate-500">({category.product_count})</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="mb-4 text-lg font-semibold">Featured gear</h2>
        {loading ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {[...Array(4)].map((_, index) => (
              <div key={index} className="aspect-[3/4] animate-pulse rounded-2xl bg-slate-900" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {featured.map((product) => (
              <ProductCard key={product.slug} product={product} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
