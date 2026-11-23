import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchExperiments, fetchSweeps } from "../api.js";
import StatusBadge from "../components/StatusBadge.jsx";

const TYPE_BADGE = {
  experiment: "border-edge text-ash",
  sweep: "border-lilac/60 text-lilac",
};

/** Compact "key params" column for one merged history row. */
function keyParams(row) {
  if (row.kind === "experiment") {
    return Object.entries(row.params)
      .slice(0, 3)
      .map(([k, v]) => `${k}=${v}`)
      .join(", ");
  }
  const shape = Object.keys(row.sweep)
    .map((k) => `${k}(${row.sweep[k].length})`)
    .join(" x ");
  return `${shape} · ${row.replicates} reps`;
}

export default function HistoryPage() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([fetchExperiments(), fetchSweeps()])
      .then(([experiments, sweeps]) => {
        const merged = [
          ...experiments.map((e) => ({ kind: "experiment", ...e })),
          ...sweeps.map((s) => ({ kind: "sweep", ...s })),
        ].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        setRows(merged);
      })
      .catch((err) => setError(`Could not reach the API: ${err.message}`));
  }, []);

  const filtered = useMemo(() => {
    if (!rows) return [];
    return rows.filter(
      (r) =>
        (typeFilter === "all" || r.kind === typeFilter) &&
        (statusFilter === "all" || r.status === statusFilter)
    );
  }, [rows, typeFilter, statusFilter]);

  const selectClass =
    "bg-void border border-edge rounded px-2 py-1.5 text-sm text-ink focus:border-lilac focus:outline-none";

  return (
    <div>
      <h1 className="font-display text-3xl mb-1">History</h1>
      <p className="text-ash text-sm mb-6">Experiments and sweeps, newest first.</p>

      {error && (
        <div className="mb-6 border border-red-500/50 bg-red-500/10 text-red-300 rounded px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4 mb-4">
        <label className="flex items-center gap-2 text-sm text-ash">
          Type
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className={selectClass}
          >
            <option value="all">all</option>
            <option value="experiment">experiments</option>
            <option value="sweep">sweeps</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-ash">
          Status
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={selectClass}
          >
            <option value="all">all</option>
            <option value="pending">pending</option>
            <option value="running">running</option>
            <option value="done">done</option>
            <option value="partial">partial</option>
            <option value="failed">failed</option>
          </select>
        </label>
      </div>

      {!rows && !error && <p className="text-ash">Loading…</p>}

      {rows && (
        <div className="border border-edge rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-panel text-left text-xs uppercase tracking-wider text-ash">
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Engine</th>
                <th className="px-4 py-3">Key params</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr
                  key={`${row.kind}-${row.id}`}
                  data-testid="history-row"
                  onClick={() =>
                    navigate(
                      row.kind === "experiment"
                        ? `/experiments/${row.id}`
                        : `/sweeps/${row.id}`
                    )
                  }
                  className="border-t border-edge/60 hover:bg-lilac/5 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <span
                      className={`border rounded px-2 py-0.5 text-xs ${TYPE_BADGE[row.kind]}`}
                    >
                      {row.kind}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-ink">{row.engine}</td>
                  <td className="px-4 py-3 text-ash font-mono text-xs max-w-xs truncate">
                    {keyParams(row)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="px-4 py-3 text-ash whitespace-nowrap">
                    {new Date(row.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-ash">
                    Nothing matches the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
