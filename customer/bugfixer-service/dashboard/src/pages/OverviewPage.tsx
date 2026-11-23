import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useReports, useStats } from "../api/hooks";
import { StatusBadge } from "../components/StatusBadge";

const cards = [
  { key: "queued", label: "Queued", accent: "text-zinc-300" },
  { key: "running", label: "Running", accent: "text-purple-300" },
  { key: "fix_ready", label: "Fix ready", accent: "text-emerald-300" },
  { key: "failed", label: "Failed", accent: "text-red-300" },
  { key: "rejected", label: "Rejected", accent: "text-amber-300" },
] as const;

export function OverviewPage() {
  const stats = useStats();
  const latest = useReports({ limit: 5 }, false);

  if (stats.isLoading) return <p className="text-sm text-zinc-500">Loading overview…</p>;
  if (stats.isError) return <p role="alert" className="text-sm text-red-400">{stats.error.message}</p>;
  if (!stats.data) return null;

  const hours = Math.round(stats.data.avg_time_to_fix_seconds / 360) / 10;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Overview</h1>
        <p className="mt-1 text-sm text-zinc-500">Current pipeline state and activity.</p>
      </div>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-5" aria-label="Status counts">
        {cards.map((card) => (
          <div key={card.key} className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
            <p className="text-xs uppercase tracking-wide text-zinc-500">{card.label}</p>
            <p className={`mt-2 text-2xl font-semibold ${card.accent}`}>
              {stats.data.status_counts[card.key] ?? 0}
            </p>
          </div>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-zinc-200 p-4 lg:col-span-2 dark:border-zinc-800">
          <h2 className="mb-4 text-sm font-semibold">Reports per day (30 days)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.data.reports_per_day}>
                <CartesianGrid strokeDasharray="3 3" stroke="#52525b33" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={5} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#a855f7" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-4 rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
          <h2 className="text-sm font-semibold">At a glance</h2>
          <p className="text-sm text-zinc-500">
            Average time to fix: <span className="text-zinc-900 dark:text-zinc-100">{hours} h</span>
          </p>
          <ul className="space-y-3 text-sm">
            {stats.data.per_project.map((project) => (
              <li key={project.project_id} className="flex justify-between gap-2">
                <span className="truncate">{project.name}</span>
                <span className="text-zinc-500">{project.success_rate}% ({project.total})</span>
              </li>
            ))}
          </ul>
          {stats.data.per_project.length === 0 && <p className="text-sm text-zinc-500">No projects yet.</p>}
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Latest reports</h2>
          <Link to="/reports" className="text-sm text-purple-400 hover:underline">View all</Link>
        </div>
        {latest.isLoading && <p className="text-sm text-zinc-500">Loading reports…</p>}
        {latest.isError && <p role="alert" className="text-sm text-red-400">{latest.error.message}</p>}
        {latest.data && latest.data.results.length === 0 && (
          <p className="rounded-lg border border-zinc-200 p-6 text-center text-sm text-zinc-500 dark:border-zinc-800">No reports yet.</p>
        )}
        {latest.data && latest.data.results.length > 0 && (
          <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
            {latest.data.results.map((report) => (
              <li key={report.id} className="flex items-center justify-between gap-4 p-3">
                <Link to={`/reports/${report.id}`} className="min-w-0 truncate text-sm hover:underline">
                  #{report.id} {report.message}
                </Link>
                <StatusBadge status={report.status} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
