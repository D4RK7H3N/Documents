import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchExperiment } from "../api.js";
import EvolutionArena from "../components/EvolutionArena.jsx";
import EvolutionChart from "../components/EvolutionChart.jsx";

// The 3D view (three + R3F) loads only when the user switches to it.
const Arena3D = lazy(() => import("../components/arena3d/Arena3D.jsx"));

const POLL_MS = 1500;
const PREF_VIEW = "simlab.arenaView";

const STATUS_BADGE = {
  pending: "border-edge text-ash",
  running: "border-lilac text-lilac animate-pulse",
  done: "border-emerald-500/60 text-emerald-400",
  failed: "border-red-500/60 text-red-400",
};

function readViewPref() {
  try {
    return window.localStorage?.getItem?.(PREF_VIEW) === "3d" ? "3d" : "2d";
  } catch {
    return "2d";
  }
}

export default function ExperimentResult() {
  const { id } = useParams();
  const [experiment, setExperiment] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [currentGen, setCurrentGen] = useState(1);
  const [viewMode, setViewMode] = useState(readViewPref);
  const [webglNote, setWebglNote] = useState(null);
  const timerRef = useRef(null);
  const navigate = useNavigate();

  function switchView(mode) {
    setViewMode(mode);
    try {
      window.localStorage?.setItem?.(PREF_VIEW, mode);
    } catch {
      /* ignore private-mode failures */
    }
  }

  /** The 3D view bails out here when WebGL is unavailable or the context is lost. */
  function fallbackTo2D(reason) {
    setWebglNote(
      reason === "webgl-context-lost"
        ? "The 3D context was lost — switched back to the 2D view."
        : "WebGL is not available — showing the 2D view instead."
    );
    switchView("2d");
  }

  // Poll the experiment every POLL_MS until it reaches a final state.
  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const data = await fetchExperiment(id);
        if (cancelled) return;
        setExperiment(data);
        setError(null);
        if (data.status === "pending" || data.status === "running") {
          timerRef.current = setTimeout(poll, POLL_MS);
        }
      } catch (err) {
        if (cancelled) return;
        setError(
          err.response?.status === 404
            ? "Experiment not found."
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

  // Reset the arena position when a different experiment is opened.
  useEffect(() => {
    setCurrentGen(1);
  }, [id]);

  function copyParams() {
    navigator.clipboard
      ?.writeText(JSON.stringify(experiment.params, null, 2))
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      });
  }

  /** Back to the form with this experiment's engine + params prefilled. */
  function runAgain() {
    navigate("/", {
      state: { engine: experiment.engine, params: experiment.params },
    });
  }

  if (error) {
    return (
      <div className="border border-red-500/50 bg-red-500/10 text-red-300 rounded px-4 py-3 text-sm">
        {error}{" "}
        <Link to="/" className="underline text-lilac ml-2">
          New experiment
        </Link>
      </div>
    );
  }

  if (!experiment) return <p className="text-ash">Loading…</p>;

  const gens = experiment.result?.generations ?? [];
  const summary = experiment.result?.summary ?? {};

  return (
    <div>
      {/* Header row: title + status badge */}
      <div className="flex items-center justify-between mb-2">
        <h1 className="font-display text-3xl">Experiment</h1>
        <span
          className={`border rounded px-3 py-1 text-xs uppercase tracking-wider ${
            STATUS_BADGE[experiment.status] ?? STATUS_BADGE.pending
          }`}
        >
          {experiment.status}
        </span>
      </div>
      <p className="text-ash text-xs mb-6 font-mono break-all">{experiment.id}</p>

      {experiment.status === "failed" && (
        <div className="mb-6 border border-red-500/50 bg-red-500/10 rounded px-4 py-3 text-sm">
          <p className="text-red-300">Simulation failed: {experiment.error}</p>
          <button
            onClick={runAgain}
            className="mt-3 border border-red-400/60 text-red-300 hover:bg-red-500/10 rounded px-3 py-1.5 text-xs transition-colors"
          >
            Run again with same params
          </button>
        </div>
      )}

      {(experiment.status === "pending" || experiment.status === "running") && (
        <>
          <div className="mb-6 border border-lilac/40 bg-lilac/10 text-lilac rounded px-4 py-3 text-sm animate-pulse">
            Simulation {experiment.status}… polling every {POLL_MS / 1000}s.
          </div>
          {/* Skeleton for the arena that appears once the run is done */}
          <div className="bg-panel border border-edge rounded-lg p-6 mb-6" data-testid="arena-skeleton">
            <div className="h-4 w-40 bg-edge/60 rounded animate-pulse mb-4" />
            <div className="h-72 rounded bg-void/60 animate-pulse" />
            <p className="text-xs text-ash mt-3">
              The evolution arena will appear here when the simulation finishes.
            </p>
          </div>
        </>
      )}

      {experiment.status === "done" && (
        <>
          {/* Mandatory disclaimer on every result view */}
          <div className="mb-6 border border-lilac/40 bg-lilac/10 text-lilac rounded px-4 py-2.5 text-sm">
            Simulation result, not experimental evidence.
          </div>

          {/* 2D / 3D switch (visualization choice only) */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs uppercase tracking-wider text-ash">View</span>
            <button
              data-testid="view-2d"
              onClick={() => switchView("2d")}
              className={`border rounded px-3 py-1.5 text-xs transition-colors ${
                viewMode === "2d"
                  ? "border-lilac bg-lilac/10 text-lilac"
                  : "border-edge text-ash hover:border-lilac/50 hover:text-lilac"
              }`}
            >
              2D
            </button>
            <button
              data-testid="view-3d"
              onClick={() => switchView("3d")}
              className={`border rounded px-3 py-1.5 text-xs transition-colors ${
                viewMode === "3d"
                  ? "border-lilac bg-lilac/10 text-lilac"
                  : "border-edge text-ash hover:border-lilac/50 hover:text-lilac"
              }`}
            >
              3D
            </button>
            {webglNote && <span className="text-xs text-amber-400">{webglNote}</span>}
          </div>

          {/* Live evolution view (2D canvas or lazy 3D scene, synced with the chart) */}
          {viewMode === "2d" ? (
            <EvolutionArena
              experiment={experiment}
              currentGen={currentGen}
              onCurrentGenChange={setCurrentGen}
            />
          ) : (
            <Suspense
              fallback={
                <div className="bg-panel border border-edge rounded-lg p-6 mb-6" data-testid="arena3d-skeleton">
                  <div className="h-4 w-40 bg-edge/60 rounded animate-pulse mb-4" />
                  <div className="h-72 rounded bg-void/60 animate-pulse" />
                  <p className="text-xs text-ash mt-3">Loading 3D view…</p>
                </div>
              }
            >
              <Arena3D
                experiment={experiment}
                currentGen={currentGen}
                onCurrentGenChange={setCurrentGen}
                onFallbackTo2D={fallbackTo2D}
              />
            </Suspense>
          )}

          {/* Trajectory chart with 50% reference line + arena sync marker */}
          <section className="bg-panel border border-edge rounded-lg p-6 mb-6">
            <h2 className="font-display text-xl mb-4">
              Trajectory
              <span className="text-ash text-xs font-sans ml-2">
                (click to jump the arena)
              </span>
            </h2>
            <EvolutionChart
              generations={gens}
              currentGen={currentGen}
              onGenClick={setCurrentGen}
            />
          </section>

          {/* Summary cards */}
          <section className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div className="bg-panel border border-edge rounded-lg p-4">
              <div className="text-xs uppercase tracking-wider text-ash mb-1">
                Final frequency
              </div>
              <div className="font-display text-2xl text-lilac">
                {Number(summary.final_freq ?? 0).toFixed(4)}
              </div>
            </div>
            <div className="bg-panel border border-edge rounded-lg p-4">
              <div className="text-xs uppercase tracking-wider text-ash mb-1">
                Generation to 50%
              </div>
              <div className="font-display text-2xl text-ink">
                {summary.gen_to_50pct ?? "never"}
              </div>
            </div>
            <div className="bg-panel border border-edge rounded-lg p-4">
              <div className="text-xs uppercase tracking-wider text-ash mb-1">
                Extinct
              </div>
              <div
                className={`font-display text-2xl ${
                  summary.extinct ? "text-red-400" : "text-emerald-400"
                }`}
              >
                {summary.extinct ? "Yes" : "No"}
              </div>
            </div>
          </section>

          {/* Reproducibility panel */}
          <section className="bg-panel border border-edge rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-xl">Reproducibility</h2>
              <button
                onClick={copyParams}
                className="text-xs border border-edge rounded px-3 py-1.5 text-ash hover:text-lilac hover:border-lilac/60 transition-colors"
              >
                {copied ? "Copied ✓" : "Copy params JSON"}
              </button>
            </div>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 text-sm">
              <div className="flex justify-between border-b border-edge/50 py-1.5">
                <dt className="text-ash">seed</dt>
                <dd className="text-lilac font-mono">{experiment.params.seed}</dd>
              </div>
              <div className="flex justify-between border-b border-edge/50 py-1.5">
                <dt className="text-ash">engine</dt>
                <dd className="text-ink">
                  {experiment.engine} v{experiment.engine_version}
                </dd>
              </div>
              {Object.entries(experiment.params)
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
              <div className="flex justify-between border-b border-edge/50 py-1.5">
                <dt className="text-ash">created</dt>
                <dd className="text-ink">
                  {new Date(experiment.created_at).toLocaleString()}
                </dd>
              </div>
            </dl>
          </section>
        </>
      )}

      <div className="mt-8 flex items-center gap-6">
        <Link to="/" className="text-sm text-ash hover:text-lilac transition-colors">
          ← New experiment
        </Link>
        {experiment.status === "done" && (
          <button
            onClick={runAgain}
            className="text-sm text-lilac hover:underline"
          >
            Run again with these params
          </button>
        )}
      </div>
    </div>
  );
}
