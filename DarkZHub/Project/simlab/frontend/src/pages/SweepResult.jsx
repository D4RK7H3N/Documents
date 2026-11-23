import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchSweep } from "../api.js";
import StatusBadge from "../components/StatusBadge.jsx";
import SweepHeatmap from "../components/SweepHeatmap.jsx";
import SweepLineChart from "../components/SweepLineChart.jsx";

const POLL_MS = 1500;

export default function SweepResult() {
  const { id } = useParams();
  const [sweep, setSweep] = useState(null);
  const [error, setError] = useState(null);
  const [metricKey, setMetricKey] = useState("gen50");
  const [selected, setSelected] = useState(null);
  const timerRef = useRef(null);
  const navigate = useNavigate();

  // Poll the sweep every POLL_MS until it reaches a final state.
  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const data = await fetchSweep(id);
        if (cancelled) return;
        setSweep(data);
        setError(null);
        if (data.status === "pending" || data.status === "running") {
          timerRef.current = setTimeout(poll, POLL_MS);
        }
      } catch (err) {
        if (cancelled) return;
        setError(
          err.response?.status === 404
            ? "Sweep not found."
            : `Could not reach the API: ${err.message}`
        );
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timerRef.current);
    };
  }, [id]);

  if (error) {
    return (
      <div className="border border-red-500/50 bg-red-500/10 text-red-300 rounded px-4 py-3 text-sm">
        {error}{" "}
        <Link to="/history" className="underline text-lilac ml-2">
          History
        </Link>
      </div>
    );
  }

  if (!sweep) return <p className="text-ash">Loading…</p>;

  const finished = sweep.status === "done" || sweep.status === "partial";
  const { completed, total } = sweep.progress ?? { completed: 0, total: 0 };
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  /** Prefill NewExperiment with the selected cell's exact parameters. */
  function openSingleRun() {
    if (!selected) return;
    const params = {
      ...sweep.base_params,
      [sweep.axes.param_a]: selected.a,
      ...(sweep.axes.param_b ? { [sweep.axes.param_b]: selected.b } : {}),
    };
    navigate("/", { state: { engine: sweep.engine, params } });
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h1 className="font-display text-3xl">Sweep</h1>
        <StatusBadge status={sweep.status} />
      </div>
      <p className="text-ash text-xs mb-6 font-mono break-all">{sweep.id}</p>

      {/* Mandatory disclaimer on every result view */}
      {finished && (
        <div className="mb-6 border border-lilac/40 bg-lilac/10 text-lilac rounded px-4 py-2.5 text-sm">
          Simulation result, not experimental evidence.
        </div>
      )}

      {/* Progress bar while running */}
      {!finished && (
        <div className="mb-6">
          <div className="flex justify-between text-xs text-ash mb-1">
            <span data-testid="progress-label">
              {completed} / {total} runs
            </span>
            <span>{pct}%</span>
          </div>
          <div className="h-2 bg-panel border border-edge rounded overflow-hidden">
            <div className="h-full bg-lilac transition-all" style={{ width: `${pct}%` }} />
          </div>
          <p className="text-xs text-ash mt-2 animate-pulse">
            Sweep {sweep.status}… polling every {POLL_MS / 1000}s.
          </p>
        </div>
      )}

      {sweep.status === "failed" && (
        <div className="mb-6 border border-red-500/50 bg-red-500/10 text-red-300 rounded px-4 py-3 text-sm">
          Sweep failed.
        </div>
      )}

      {finished && sweep.cells && (
        <>
          {/* Metric toggle */}
          <div className="flex gap-2 mb-4">
            <button
              data-testid="metric-gen50"
              onClick={() => setMetricKey("gen50")}
              className={`border rounded px-3 py-1.5 text-xs transition-colors ${
                metricKey === "gen50"
                  ? "border-lilac bg-lilac/10 text-lilac"
                  : "border-edge text-ash hover:border-lilac/50"
              }`}
            >
              mean gen to 50%
            </button>
            <button
              data-testid="metric-final_freq"
              onClick={() => setMetricKey("final_freq")}
              className={`border rounded px-3 py-1.5 text-xs transition-colors ${
                metricKey === "final_freq"
                  ? "border-lilac bg-lilac/10 text-lilac"
                  : "border-edge text-ash hover:border-lilac/50"
              }`}
            >
              mean final freq
            </button>
          </div>

          {/* Heatmap (2D) or line chart with error bars (1D) */}
          {sweep.axes.param_b ? (
            <SweepHeatmap
              axes={sweep.axes}
              cells={sweep.cells}
              metricKey={metricKey}
              onSelectCell={setSelected}
            />
          ) : (
            <SweepLineChart axes={sweep.axes} cells={sweep.cells} metricKey={metricKey} />
          )}

          {/* Selected cell detail */}
          {selected && (
            <section className="bg-panel border border-lilac/40 rounded-lg p-6 mt-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display text-xl">
                  Cell: {sweep.axes.param_a}={selected.a}
                  {sweep.axes.param_b ? `, ${sweep.axes.param_b}=${selected.b}` : ""}
                </h2>
                <button
                  onClick={openSingleRun}
                  className="text-xs border border-lilac/60 text-lilac hover:bg-lilac/10 rounded px-3 py-1.5 transition-colors"
                >
                  Open a single run with these params
                </button>
              </div>
              <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-8 text-sm">
                <div className="flex justify-between border-b border-edge/50 py-1.5">
                  <dt className="text-ash">runs (n)</dt>
                  <dd className="text-ink">{selected.n}</dd>
                </div>
                <div className="flex justify-between border-b border-edge/50 py-1.5">
                  <dt className="text-ash">failed</dt>
                  <dd className={selected.n_failed ? "text-red-400" : "text-ink"}>
                    {selected.n_failed}
                  </dd>
                </div>
                <div className="flex justify-between border-b border-edge/50 py-1.5">
                  <dt className="text-ash">never reached 50%</dt>
                  <dd className={selected.n_never_reached ? "text-amber-400" : "text-ink"}>
                    {selected.n_never_reached}
                  </dd>
                </div>
                <div className="flex justify-between border-b border-edge/50 py-1.5">
                  <dt className="text-ash">final_freq mean ± std</dt>
                  <dd className="text-ink font-mono">
                    {selected.final_freq_mean == null
                      ? "n/a"
                      : `${selected.final_freq_mean.toFixed(4)} ± ${(selected.final_freq_std ?? 0).toFixed(4)}`}
                  </dd>
                </div>
                <div className="flex justify-between border-b border-edge/50 py-1.5">
                  <dt className="text-ash">gen to 50% mean ± std</dt>
                  <dd className="text-ink font-mono">
                    {selected.gen50_mean == null
                      ? "n/a"
                      : `${selected.gen50_mean.toFixed(1)} ± ${(selected.gen50_std ?? 0).toFixed(1)}`}
                  </dd>
                </div>
              </dl>
            </section>
          )}

          {/* Reproducibility panel */}
          <section className="bg-panel border border-edge rounded-lg p-6 mt-6">
            <h2 className="font-display text-xl mb-4">Reproducibility</h2>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 text-sm">
              <div className="flex justify-between border-b border-edge/50 py-1.5">
                <dt className="text-ash">engine</dt>
                <dd className="text-ink">
                  {sweep.engine} v{sweep.engine_version}
                </dd>
              </div>
              <div className="flex justify-between border-b border-edge/50 py-1.5">
                <dt className="text-ash">replicates</dt>
                <dd className="text-ink">{sweep.replicates}</dd>
              </div>
              <div className="flex justify-between border-b border-edge/50 py-1.5">
                <dt className="text-ash">base seed</dt>
                <dd className="text-lilac font-mono">{sweep.base_params.seed}</dd>
              </div>
              {Object.entries(sweep.base_params)
                .filter(([name]) => name !== "seed")
                .map(([name, value]) => (
                  <div
                    key={name}
                    className="flex justify-between border-b border-edge/50 py-1.5"
                  >
                    <dt className="text-ash">{name}</dt>
                    <dd className="text-ink font-mono">{String(value)}</dd>
                  </div>
                ))}
              {Object.entries(sweep.sweep).map(([name, values]) => (
                <div
                  key={`sweep-${name}`}
                  className="flex justify-between border-b border-edge/50 py-1.5 sm:col-span-2"
                >
                  <dt className="text-ash">sweep: {name}</dt>
                  <dd className="text-ink font-mono">[{values.join(", ")}]</dd>
                </div>
              ))}
              <div className="flex justify-between border-b border-edge/50 py-1.5">
                <dt className="text-ash">created</dt>
                <dd className="text-ink">{new Date(sweep.created_at).toLocaleString()}</dd>
              </div>
            </dl>
          </section>
        </>
      )}

      <Link
        to="/history"
        className="inline-block mt-8 text-sm text-ash hover:text-lilac transition-colors"
      >
        ← History
      </Link>
    </div>
  );
}
