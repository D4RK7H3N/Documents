import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api, cartChanged, peso } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [cartCount, setCartCount] = useState(0);
  const searchRef = useRef(null);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const data = await api(
          `/search/?q=${encodeURIComponent(query.trim())}&limit=6`,
          { auth: false }
        );
        setResults(data);
        setOpen(true);
      } catch {
        /* ignore search errors */
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const refresh = async () => {
      if (!user) {
        setCartCount(0);
        return;
      }
      try {
        const cart = await api("/cart/");
        setCartCount(cart.items.reduce((sum, item) => sum + item.quantity, 0));
      } catch {
        setCartCount(0);
      }
    };
    refresh();
    window.addEventListener("gearup:cart", refresh);
    return () => window.removeEventListener("gearup:cart", refresh);
  }, [user, location.pathname]);

  useEffect(() => {
    const onClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const goToProduct = (slug) => {
    setOpen(false);
    setQuery("");
    navigate(`/products/${slug}`);
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:gap-4">
        <Link to="/" className="text-lg font-bold tracking-tight">
          Gear<span className="text-emerald-400">Up</span>{" "}
          <span className="text-slate-500">PH</span>
        </Link>

        <div ref={searchRef} className="relative order-last w-full sm:order-none sm:w-auto sm:flex-1 sm:max-w-md">
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onFocus={() => results.length > 0 && setOpen(true)}
            placeholder="Search products… try 'cheap gift for a gamer'"
            aria-label="Search products"
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none transition placeholder-slate-600 focus:border-emerald-500"
          />
          {open && (
            <div className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-xl">
              {results.length === 0 ? (
                <p className="px-4 py-3 text-sm text-slate-500">No matching products.</p>
              ) : (
                results.map((product) => (
                  <button
                    key={product.slug}
                    type="button"
                    onClick={() => goToProduct(product.slug)}
                    className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-sm hover:bg-slate-800"
                  >
                    <span className="truncate">{product.name}</span>
                    <span className="whitespace-nowrap font-semibold text-emerald-400">
                      {peso(product.price)}
                    </span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        <nav className="ml-auto flex items-center gap-1">
          <Link to="/products" className="rounded-lg px-3 py-2 text-sm font-medium text-slate-300 transition hover:text-white">
            Shop
          </Link>
          {user && (
            <Link to="/orders" className="rounded-lg px-3 py-2 text-sm font-medium text-slate-300 transition hover:text-white">
              Orders
            </Link>
          )}
          <Link
            to="/cart"
            className="relative rounded-lg px-3 py-2 text-sm font-medium text-slate-300 transition hover:text-white"
          >
            Cart
            {cartCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-500 px-1 text-xs font-bold text-slate-950">
                {cartCount}
              </span>
            )}
          </Link>
          {user ? (
            <div className="flex items-center gap-2">
              <span className="hidden text-sm text-slate-400 sm:block">
                {user.username}
              </span>
              <button
                type="button"
                onClick={() => {
                  logout();
                  navigate("/");
                }}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition hover:border-slate-500 hover:text-white"
              >
                Logout
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="rounded-lg bg-emerald-500 px-3 py-1.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
            >
              Login
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
