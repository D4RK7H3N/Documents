import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const NAV_ACTIVE = "bg-secondary-container text-on-surface font-semibold rounded-lg border border-secondary-fixed-dim";

function NavItem({ to, icon, label, end, onClick }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        `flex min-h-11 items-center gap-space-md px-space-md py-space-sm transition-colors font-body-md text-body-md ${
          isActive ? NAV_ACTIVE : "rounded-lg text-slate-300 hover:bg-white/10 hover:text-white"
        }`
      }
    >
      <span className="material-symbols-outlined text-lg">{icon}</span>
      <span>{label}</span>
    </NavLink>
  );
}

export default function Layout({ children }) {
  const { user, config, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === "admin";
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef(null);
  const drawerRef = useRef(null);

  const groups = [
    {
      label: "Academic Operations",
      items: [
        { to: "/", label: "Dashboard", icon: "dashboard", end: true },
        { to: "/classes", label: "My Classes", icon: "class" },
        { to: "/submissions", label: "Submissions", icon: "outgoing_mail" },
        { to: "/reports", label: "Reports", icon: "monitoring" },
      ],
    },
    ...(isAdmin
      ? [
          {
            label: "Class Records",
            items: [
              { to: "/admin/class-records", label: "Class Records", icon: "table_chart" },
            ],
          },
          {
            label: "Administration",
            items: [
              { to: "/students", label: "Students", icon: "group" },
              { to: "/teachers", label: "Teacher Config", icon: "co_present" },
              { to: "/users", label: "User Accounts", icon: "manage_accounts" },
              { to: "/academics", label: "Academics", icon: "menu_book" },
              { to: "/grading-config", label: "Grading Config", icon: "tune" },
              { to: "/settings", label: "School Settings", icon: "branding_watermark" },
              { to: "/audit-log", label: "Audit Log", icon: "history" },
            ],
          },
        ]
      : []),
  ];

  const initials = (user?.username || "?").slice(0, 2).toUpperCase();

  useEffect(() => {
    if (!menuOpen) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const drawer = drawerRef.current;
    const getFocusable = () => Array.from(
      drawer?.querySelectorAll('a[href], button:not([disabled]), [tabindex="0"]') || [],
    );
    getFocusable()[0]?.focus();

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = getFocusable();
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
      menuButtonRef.current?.focus();
    };
  }, [menuOpen]);

  return (
    <>
      <aside className="fixed left-0 top-0 h-full w-64 bg-navigation text-on-navigation border-r border-white/10 z-50 hidden lg:flex flex-col justify-between">
        <div className="flex flex-col flex-1 overflow-y-auto">
          <div className="h-20 flex items-center px-space-lg gap-space-sm border-b border-white/10">
            <img src={config?.logo_url || "/logo.svg"} alt="" className="h-9 w-9 object-contain" />
            <div className="flex flex-col">
              <span className="font-headline-sm text-headline-sm font-bold text-white tracking-tight">
                Grade Monitor
              </span>
              <span className="font-label-sm text-label-sm text-slate-400 uppercase tracking-wider">
                {config?.short_name || "SNHS"}
              </span>
            </div>
          </div>
          {groups.map((group) => (
            <div key={group.label} className="px-space-md py-space-sm">
              <div className="px-space-sm pb-space-xs font-label-sm text-label-sm text-slate-400 uppercase tracking-wider">
                {group.label}
              </div>
              <nav className="flex flex-col gap-space-2xs" aria-label={group.label}>
                {group.items.map((item) => (
                  <NavItem key={item.to} {...item} />
                ))}
              </nav>
            </div>
          ))}
        </div>
        <div className="p-space-md m-space-md bg-white/5 border border-white/10 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="font-label-sm text-label-sm text-slate-300 font-medium">System Status</span>
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
          </div>
          <p className="mt-space-2xs font-data-tabular-sm text-data-tabular-sm text-white">DepEd 8 s. 2015 Engine</p>
          <p className="font-label-sm text-label-sm text-slate-400">S.Y. {config?.default_school_year || "—"}</p>
        </div>
      </aside>

      {menuOpen && (
        <div className="fixed inset-0 z-[70] lg:hidden">
          <button
            type="button"
            tabIndex={-1}
            aria-label="Close navigation"
            onClick={() => setMenuOpen(false)}
            className="absolute inset-0 bg-slate-950/45 backdrop-blur-[2px]"
          />
          <div
            id="mobile-navigation"
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Portal navigation"
            className="absolute inset-y-0 left-0 flex w-[min(21rem,88vw)] flex-col bg-navigation text-on-navigation shadow-2xl"
          >
            <div className="flex h-16 items-center justify-between gap-space-sm border-b border-white/10 px-space-md">
              <div className="flex min-w-0 items-center gap-space-sm">
                <img src={config?.logo_url || "/logo.svg"} alt="" className="h-8 w-8 object-contain" />
                <span className="truncate font-headline-sm text-headline-sm font-bold text-white">Grade Monitor</span>
              </div>
              <button
                type="button"
                aria-label="Close navigation"
                onClick={() => setMenuOpen(false)}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-slate-300 hover:bg-white/10 hover:text-white"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto py-space-sm">
              {groups.map((group) => (
                <div key={group.label} className="px-space-md py-space-sm">
                  <div className="px-space-sm pb-space-xs font-label-sm text-label-sm text-slate-400 uppercase tracking-wider">
                    {group.label}
                  </div>
                  <nav className="flex flex-col gap-space-2xs" aria-label={`${group.label} mobile`}>
                    {group.items.map((item) => (
                      <NavItem key={item.to} {...item} onClick={() => setMenuOpen(false)} />
                    ))}
                  </nav>
                </div>
              ))}
            </div>
            <div className="border-t border-white/10 p-space-md">
              <Link
                to="/profile"
                onClick={() => setMenuOpen(false)}
                className="mb-space-md flex min-h-11 items-center gap-space-md rounded-lg px-space-sm hover:bg-white/10"
              >
                {user?.avatar_url ? (
                  <img src={user.avatar_url} alt="" className="h-9 w-9 rounded-full object-cover border border-outline-variant" />
                ) : (
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary-container font-label-md font-semibold text-on-surface">
                    {initials}
                  </div>
                )}
                <div className="min-w-0">
                  <div className="truncate font-body-md text-body-md font-semibold text-white">{user?.display_name || user?.username}</div>
                  <div className="font-label-sm text-label-sm capitalize text-slate-400">{user?.role}</div>
                </div>
              </Link>
              <button
                type="button"
                onClick={async () => {
                  await logout();
                  setMenuOpen(false);
                  navigate("/login");
                }}
                className="flex min-h-11 w-full items-center gap-space-md rounded-lg px-space-md py-space-sm text-left font-body-md text-body-md text-slate-300 hover:bg-white/10 hover:text-white"
              >
                <span className="material-symbols-outlined text-lg">logout</span>
                Log out
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="fixed top-0 left-0 lg:left-64 right-0 h-16 bg-surface-container-lowest/95 backdrop-blur-xl border-b border-outline-variant/70 z-40 flex items-center justify-between gap-space-md px-gutter sm:px-gutter-desktop">
          <div className="flex min-w-0 flex-1 items-center gap-space-md">
            <button
              ref={menuButtonRef}
              type="button"
              aria-label="Open navigation"
              aria-expanded={menuOpen}
              aria-controls="mobile-navigation"
              onClick={() => setMenuOpen(true)}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface lg:hidden"
            >
              <span className="material-symbols-outlined">menu</span>
            </button>
            <div className="flex min-w-0 items-center gap-space-sm lg:hidden">
              <img src={config?.logo_url || "/logo.svg"} alt="" className="h-8 w-8 object-contain" />
              <span className="truncate font-headline-sm text-headline-sm font-bold text-on-surface">Grade Monitor</span>
            </div>
            <div className="hidden lg:flex flex-1 items-center gap-space-lg max-w-2xl">
              <div className="flex items-center gap-space-xs bg-secondary-container/60 px-space-md py-space-xs rounded-lg">
                <span className="material-symbols-outlined text-on-surface-variant text-base">calendar_month</span>
                <span className="font-label-md text-label-md text-on-surface">
                  S.Y. {config?.default_school_year || "—"}
                </span>
              </div>
              <form
                className="relative flex flex-1"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (query.trim()) navigate(`/students?q=${encodeURIComponent(query.trim())}`);
                }}
              >
                <div className="flex items-center bg-surface-container-low border border-outline-variant/70 px-space-md py-space-xs rounded-lg w-full text-on-surface-variant">
                  <span className="material-symbols-outlined text-base mr-space-xs">search</span>
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="bg-transparent min-h-8 w-full font-body-sm text-body-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none"
                    placeholder="Search learners by name or LRN…"
                    aria-label="Search learners by name or LRN"
                    type="text"
                  />
                </div>
              </form>
            </div>
          </div>
          <div className="flex items-center gap-space-md">
            <button
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
              title="Log out"
              aria-label="Log out"
              className="hidden lg:flex h-11 w-11 items-center justify-center rounded-lg text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-colors"
              type="button"
            >
              <span className="material-symbols-outlined text-xl">logout</span>
            </button>
            <Link to="/profile" aria-label="Open my profile" className="flex min-h-11 items-center gap-space-md rounded-lg lg:pl-space-sm hover:bg-surface-container-low">
              <div className="text-right hidden sm:block">
                <div className="font-headline-sm text-headline-sm font-semibold text-on-surface leading-tight">
                  {user?.display_name || user?.username}
                </div>
                <div className="font-label-sm text-label-sm text-on-surface-variant capitalize">{user?.role}</div>
              </div>
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-9 h-9 rounded-full object-cover border border-outline-variant" />
              ) : (
                <div className="w-9 h-9 rounded-full bg-primary-container text-on-primary flex items-center justify-center font-label-md font-semibold">
                  {initials}
                </div>
              )}
            </Link>
          </div>
        </header>

        <main className="w-full min-h-screen bg-background px-gutter sm:px-gutter-desktop pb-space-lg pt-20 sm:pb-space-xl sm:pt-24">
          <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-space-lg sm:gap-space-xl">{children}</div>
        </main>
      </div>
    </>
  );
}
