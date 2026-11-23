import { useMutation, useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useMe } from "../api/hooks";
import { useTheme } from "../theme";

const links = [
  { to: "/", label: "Overview", end: true },
  { to: "/reports", label: "Reports" },
  { to: "/projects", label: "Projects" },
  { to: "/settings", label: "Settings" },
];

export function Layout() {
  const { data: me } = useMe();
  const { theme, toggle } = useTheme();
  const client = useQueryClient();
  const navigate = useNavigate();
  const logout = useMutation({
    mutationFn: api.auth.logout,
    onSuccess: () => {
      client.setQueryData(["me"], null);
      navigate("/login");
    },
  });

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `block rounded-lg px-3 py-2 text-sm transition-colors ${
      isActive ? "bg-purple-600/20 text-purple-300" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-900 dark:hover:text-zinc-100"
    }`;

  return (
    <div className="min-h-screen md:flex">
      <aside className="hidden w-56 shrink-0 border-r border-zinc-200 bg-zinc-100/40 p-4 md:block dark:border-zinc-800 dark:bg-zinc-950/60">
        <div className="mb-8 px-3">
          <p className="text-lg font-semibold tracking-tight">BugFixer</p>
          <p className="text-xs text-zinc-500">staff console</p>
        </div>
        <nav className="space-y-1" aria-label="Main navigation">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} className={navClass}>
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <div className="md:hidden">
            <NavLink to="/" className="font-semibold">BugFixer</NavLink>
          </div>
          <div className="hidden text-sm text-zinc-500 md:block">{me?.username ?? "…"}</div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={toggle}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700"
            >
              {theme === "dark" ? "Light" : "Dark"}
            </button>
            <button
              type="button"
              onClick={() => logout.mutate()}
              className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
            >
              Log out
            </button>
          </div>
        </header>

        <nav className="flex gap-2 overflow-x-auto border-b border-zinc-200 px-4 py-2 md:hidden dark:border-zinc-800" aria-label="Mobile navigation">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} className={navClass}>
              {link.label}
            </NavLink>
          ))}
        </nav>

        <main className="mx-auto w-full max-w-6xl flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
