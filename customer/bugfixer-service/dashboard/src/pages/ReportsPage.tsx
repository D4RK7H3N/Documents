import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { ReportFilters } from "../api/client";
import { useProjects, useReports } from "../api/hooks";
import { DataTable, type Column } from "../components/DataTable";
import { StatusBadge } from "../components/StatusBadge";
import type { ReportSummary } from "../api/types";

export function ReportsPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<ReportFilters>({ limit: 20, offset: 0, ordering: "-created_at" });
  const [search, setSearch] = useState("");
  const projects = useProjects();
  const query = useReports(filters, false);
  const rows = query.data?.results ?? [];
  const shouldPoll = rows.some((row) => row.status === "queued" || row.status === "running");
  const reports = useReports(filters, shouldPoll ? 10000 : false);
  const data = reports.data ?? query.data;

  const set = (patch: Partial<ReportFilters>) => setFilters((current) => ({ ...current, ...patch, offset: 0 }));

  const columns: Column<ReportSummary>[] = [
    { key: "id", label: "ID", render: (row) => <span className="font-mono text-xs">#{row.id}</span> },
    { key: "project", label: "Project", render: (row) => row.project_name },
    { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
    {
      key: "message",
      label: "Message",
      render: (row) => <span className="block max-w-md truncate">{row.message}</span>,
    },
    {
      key: "created",
      label: "Created",
      render: (row) => <span className="whitespace-nowrap text-xs text-zinc-500">{new Date(row.created_at).toLocaleString()}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Reports</h1>
        <p className="mt-1 text-sm text-zinc-500">Auto-refreshes while a report is queued or running.</p>
      </div>

      <div className="grid gap-3 rounded-xl border border-zinc-200 p-4 dark:border-zinc-800 md:grid-cols-4">
        <div className="md:col-span-2">
          <label htmlFor="search" className="block text-xs font-medium text-zinc-500">Search message</label>
          <input
            id="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && set({ search })}
            placeholder="Search…"
            className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
          />
        </div>
        <div>
          <label htmlFor="project" className="block text-xs font-medium text-zinc-500">Project</label>
          <select
            id="project"
            value={filters.project ?? ""}
            onChange={(event) => set({ project: event.target.value })}
            className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
          >
            <option value="">All</option>
            {(projects.data ?? []).map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="status" className="block text-xs font-medium text-zinc-500">Status</label>
          <select
            id="status"
            value={filters.status ?? ""}
            onChange={(event) => set({ status: event.target.value })}
            className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
          >
            <option value="">All</option>
            {["queued", "running", "fix_ready", "failed", "rejected"].map((status) => (
              <option key={status} value={status}>{status.replace("_", " ")}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="date-from" className="block text-xs font-medium text-zinc-500">From</label>
          <input
            id="date-from"
            type="date"
            value={filters.date_from ?? ""}
            onChange={(event) => set({ date_from: event.target.value })}
            className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
          />
        </div>
        <div>
          <label htmlFor="date-to" className="block text-xs font-medium text-zinc-500">To</label>
          <input
            id="date-to"
            type="date"
            value={filters.date_to ?? ""}
            onChange={(event) => set({ date_to: event.target.value })}
            className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
          />
        </div>
        <div className="flex items-end gap-2 md:col-span-2">
          <button
            type="button"
            onClick={() => set({ search })}
            className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-500"
          >
            Apply
          </button>
          <button
            type="button"
            onClick={() => { setSearch(""); setFilters({ limit: 20, offset: 0, ordering: "-created_at" }); }}
            className="rounded-lg border border-zinc-300 px-4 py-2 text-sm dark:border-zinc-700"
          >
            Clear
          </button>
        </div>
      </div>

      {reports.isLoading && <p className="text-sm text-zinc-500">Loading reports…</p>}
      {reports.isError && <p role="alert" className="text-sm text-red-400">{reports.error.message}</p>}
      {data && (
        <>
          <DataTable columns={columns} rows={data.results} rowKey={(row) => row.id} onRowClick={(row) => navigate(`/reports/${row.id}`)} empty="No reports match these filters." />
          <div className="flex items-center justify-between text-sm">
            <button
              type="button"
              disabled={!data.previous}
              onClick={() => setFilters((current) => ({ ...current, offset: Math.max(0, (current.offset ?? 0) - (current.limit ?? 20)) }))}
              className="rounded-lg border border-zinc-300 px-3 py-1.5 disabled:opacity-40 dark:border-zinc-700"
            >
              Previous
            </button>
            <span className="text-zinc-500">{data.count} total</span>
            <button
              type="button"
              disabled={!data.next}
              onClick={() => setFilters((current) => ({ ...current, offset: (current.offset ?? 0) + (current.limit ?? 20) }))}
              className="rounded-lg border border-zinc-300 px-3 py-1.5 disabled:opacity-40 dark:border-zinc-700"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
