import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, cartChanged, peso } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { stockBadge, stockLabel } from "../components/ProductCard.jsx";

const SENTIMENT_STYLES = {
  positive: "border-emerald-500/30 bg-emerald-500/15 text-emerald-400",
  neutral: "border-slate-500/30 bg-slate-500/15 text-slate-300",
  negative: "border-rose-500/30 bg-rose-500/15 text-rose-400",
};

export default function ProductDetail() {
  const { slug } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [product, setProduct] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState({});
  const [quantity, setQuantity] = useState(1);
  const [adding, setAdding] = useState(false);
  const [addMessage, setAddMessage] = useState("");

  const [reviews, setReviews] = useState([]);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewError, setReviewError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setProduct(null);
    setError("");
    setSelected({});
    setQuantity(1);
    (async () => {
      try {
        const [detail, recs, productReviews] = await Promise.all([
          api(`/products/${slug}/`, { auth: false }),
          api(`/recommendations/${slug}/`, { auth: false }),
          api(`/products/${slug}/reviews/`, { auth: false }),
        ]);
        if (cancelled) return;
        setProduct(detail);
        setRecommendations(recs);
        setReviews(productReviews);
        const defaults = {};
        for (const variant of detail.variants || []) {
          if (!(variant.name in defaults)) defaults[variant.name] = variant.id;
        }
        setSelected(defaults);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const variantGroups = useMemo(() => {
    const groups = {};
    for (const variant of product?.variants || []) {
      (groups[variant.name] ||= []).push(variant);
    }
    return groups;
  }, [product]);

  const selectedVariant = useMemo(() => {
    const ids = Object.values(selected);
    if (!ids.length) return null;
    return (product?.variants || []).find((v) => ids.includes(v.id)) || null;
  }, [selected, product]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center text-slate-400">
        {error} — <Link to="/products" className="text-emerald-400">back to shop</Link>
      </div>
    );
  }
  if (!product) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16">
        <div className="h-96 animate-pulse rounded-2xl bg-slate-900" />
      </div>
    );
  }

  const availableStock = selectedVariant ? selectedVariant.stock : product.stock;
  const unitPrice = selectedVariant ? selectedVariant.price : product.price;

  const addToCart = async () => {
    if (!user) {
      navigate("/login", { state: { from: `/products/${slug}` } });
      return;
    }
    setAdding(true);
    setAddMessage("");
    try {
      await api("/cart/items/", {
        method: "POST",
        body: {
          product: product.slug,
          variant: selectedVariant ? selectedVariant.id : null,
          quantity,
        },
      });
      cartChanged();
      setAddMessage(`Added ${quantity} to your cart.`);
    } catch (err) {
      setAddMessage(err.message);
    } finally {
      setAdding(false);
    }
  };

  const submitReview = async (event) => {
    event.preventDefault();
    setReviewBusy(true);
    setReviewError("");
    try {
      await api(`/products/${slug}/reviews/`, {
        method: "POST",
        body: { rating, comment: comment.trim() },
      });
      setComment("");
      const [productReviews, detail] = await Promise.all([
        api(`/products/${slug}/reviews/`, { auth: false }),
        api(`/products/${slug}/`, { auth: false }),
      ]);
      setReviews(productReviews);
      setProduct(detail);
    } catch (err) {
      setReviewError(err.message);
    } finally {
      setReviewBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="grid gap-8 lg:grid-cols-2">
        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
          {product.image ? (
            <img src={product.image} alt={product.name} className="w-full object-cover" />
          ) : (
            <div className="flex aspect-square items-center justify-center text-6xl font-bold text-slate-600">
              {product.name.slice(0, 2).toUpperCase()}
            </div>
          )}
        </div>

        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">
            <Link to={`/products?category=${product.category.slug}`} className="hover:text-emerald-400">
              {product.category.name}
            </Link>
            {product.brand ? ` · ${product.brand}` : ""}
          </p>
          <h1 className="mt-2 text-2xl font-bold sm:text-3xl">{product.name}</h1>

          <div className="mt-3 flex items-center gap-3">
            <span className="text-2xl font-bold text-emerald-400">{peso(unitPrice)}</span>
            <span className={`rounded-full border px-2.5 py-1 text-xs ${stockBadge(availableStock)}`}>
              {stockLabel(availableStock)}
            </span>
          </div>

          <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
            {product.description}
          </p>

          {Object.entries(variantGroups).map(([name, options]) => (
            <div key={name} className="mt-5">
              <p className="mb-2 text-sm font-medium text-slate-300">{name}</p>
              <div className="flex flex-wrap gap-2">
                {options.map((variant) => (
                  <button
                    key={variant.id}
                    type="button"
                    onClick={() => setSelected((prev) => ({ ...prev, [name]: variant.id }))}
                    disabled={variant.stock === 0}
                    className={`rounded-lg border px-3 py-1.5 text-sm transition disabled:cursor-not-allowed disabled:opacity-30 ${
                      selected[name] === variant.id
                        ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
                        : "border-slate-700 text-slate-300 hover:border-slate-500"
                    }`}
                  >
                    {variant.value}
                  </button>
                ))}
              </div>
            </div>
          ))}

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <div className="flex items-center rounded-xl border border-slate-700">
              <button
                type="button"
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                className="px-3 py-2 text-slate-300 hover:text-white"
                aria-label="Decrease quantity"
              >
                −
              </button>
              <span className="w-10 text-center text-sm">{quantity}</span>
              <button
                type="button"
                onClick={() => setQuantity((q) => Math.min(availableStock || 99, q + 1))}
                className="px-3 py-2 text-slate-300 hover:text-white"
                aria-label="Increase quantity"
              >
                +
              </button>
            </div>
            <button
              type="button"
              onClick={addToCart}
              disabled={adding || availableStock === 0}
              className="rounded-xl bg-emerald-500 px-6 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {availableStock === 0 ? "Out of stock" : adding ? "Adding…" : "Add to cart"}
            </button>
          </div>
          {addMessage && <p className="mt-2 text-sm text-emerald-400">{addMessage}</p>}
        </div>
      </div>

      {recommendations && (
        <div className="mt-12 space-y-8">
          <section>
            <h2 className="mb-3 text-lg font-semibold">Customers also bought</h2>
            {recommendations.also_bought.length === 0 ? (
              <p className="text-sm text-slate-500">No suggestions yet.</p>
            ) : (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                {recommendations.also_bought.slice(0, 4).map((item) => (
                  <MiniCard key={item.slug} product={item} />
                ))}
              </div>
            )}
            {recommendations.also_bought_fallback !== "none" && (
              <p className="mt-2 text-xs text-slate-600">
                Showing {recommendations.also_bought_fallback === "similar" ? "similar products" : "best sellers"} (no purchase data yet)
              </p>
            )}
          </section>
          <section>
            <h2 className="mb-3 text-lg font-semibold">Similar products</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {recommendations.similar.slice(0, 4).map((item) => (
                <MiniCard key={item.slug} product={item} />
              ))}
            </div>
          </section>
        </div>
      )}

      <section className="mt-12">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Reviews</h2>
          {product.reviews_summary.total > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-slate-400">
                {product.reviews_summary.average_rating}/5 · {product.reviews_summary.total} review(s)
              </span>
              {Object.entries(product.reviews_summary.sentiment_counts).map(([label, count]) => (
                <span
                  key={label}
                  className={`rounded-full border px-2 py-0.5 capitalize ${SENTIMENT_STYLES[label]}`}
                >
                  {label}: {count}
                </span>
              ))}
            </div>
          )}
        </div>

        {user ? (
          <form onSubmit={submitReview} className="mt-4 rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-center gap-3">
              <label className="text-sm text-slate-300" htmlFor="rating">Rating</label>
              <select
                id="rating"
                value={rating}
                onChange={(event) => setRating(Number(event.target.value))}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm outline-none focus:border-emerald-500"
              >
                {[5, 4, 3, 2, 1].map((value) => (
                  <option key={value} value={value}>{value} star{value > 1 ? "s" : ""}</option>
                ))}
              </select>
            </div>
            <textarea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              rows={3}
              required
              placeholder="Share your experience with this product…"
              className="mt-3 w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none placeholder-slate-600 focus:border-emerald-500"
            />
            {reviewError && <p className="mt-2 text-sm text-rose-400">{reviewError}</p>}
            <button
              type="submit"
              disabled={reviewBusy || !comment.trim()}
              className="mt-3 rounded-xl bg-emerald-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-40"
            >
              {reviewBusy ? "Posting…" : "Post review"}
            </button>
          </form>
        ) : (
          <p className="mt-4 text-sm text-slate-500">
            <Link to="/login" className="text-emerald-400">Log in</Link> to write a review.
          </p>
        )}

        <div className="mt-6 space-y-3">
          {reviews.length === 0 ? (
            <p className="text-sm text-slate-500">No reviews yet.</p>
          ) : (
            reviews.map((review) => (
              <div key={review.id} className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-semibold">{review.username}</span>
                  <span className="text-amber-400">{"★".repeat(review.rating)}</span>
                  {review.sentiment && (
                    <span className={`rounded-full border px-2 py-0.5 text-xs capitalize ${SENTIMENT_STYLES[review.sentiment]}`}>
                      {review.sentiment}
                    </span>
                  )}
                  <span className="ml-auto text-xs text-slate-500">
                    {new Date(review.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-300">{review.comment}</p>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function MiniCard({ product }) {
  return (
    <Link
      to={`/products/${product.slug}`}
      className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900 p-3 transition hover:border-slate-600"
    >
      <div className="h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-slate-800">
        {product.image && (
          <img src={product.image} alt={product.name} className="h-full w-full object-cover" />
        )}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{product.name}</p>
        <p className="text-sm font-semibold text-emerald-400">{peso(product.price)}</p>
      </div>
    </Link>
  );
}
