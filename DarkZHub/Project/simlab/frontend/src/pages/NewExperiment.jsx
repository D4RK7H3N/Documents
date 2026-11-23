import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { createExperiment, fetchEngines } from "../api.js";
import EnginePicker from "../components/EnginePicker.jsx";
import ParamForm from "../components/ParamForm.jsx";

/** Build a params object filled with an engine's schema defaults. */
function defaultsFrom(schema) {
  const params = {};
  for (const [name, spec] of Object.entries(schema)) {
    params[name] = spec.default;
  }
  return params;
}

/** Curated demo presets (engine-specific; only shown for their engine). */
const PRESETS = [
  {
    id: "slow-evolution",
    engine: "insect_evo",
    label: "Slow evolution (demo)",
    description: "weak pesticide: resistance takes ~50 generations to fix",
    params: {
      pesticide_kill: 0.22,
      resistance_cost: 0.1,
      start_freq: 0.05,
      population: 10000,
      generations: 120,
    },
  },
];

/** Flatten a DRF 400 response into a single readable message. */
function formatApiError(error) {
  const data = error.response?.data;
  if (!data) return error.message;
  if (typeof data === "string") return data;
  return Object.entries(data)
    .map(
      ([field, messages]) =>
        `${field}: ${Array.isArray(messages) ? messages.join(" ") : messages}`
    )
    .join(" — ");
}

export default function NewExperiment() {
  const [engines, setEngines] = useState([]);
  const [engineName, setEngineName] = useState(null);
  const [params, setParams] = useState({});
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  // "Run again" from a result page navigates here with
  // { engine, params } in the router state -> prefill the form.
  const prefill = useLocation().state ?? null;

  useEffect(() => {
    fetchEngines()
      .then((data) => {
        setEngines(data);
        const wanted = prefill ? data.find((e) => e.name === prefill.engine) : null;
        const chosen = wanted ?? data[0];
        if (chosen) {
          setEngineName(chosen.name);
          setParams(
            wanted
              ? { ...defaultsFrom(chosen.param_schema), ...prefill.params }
              : defaultsFrom(chosen.param_schema)
          );
        }
      })
      .catch((err) => setError(formatApiError(err)));
    // Runs once on mount; navigation state is stable for the page's life.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const engine = engines.find((e) => e.name === engineName);

  function selectEngine(name) {
    setEngineName(name);
    setParams(defaultsFrom(engines.find((e) => e.name === name).param_schema));
  }

  function updateParam(name, value) {
    setParams((prev) => ({ ...prev, [name]: value }));
  }

  async function run() {
    setSubmitting(true);
    setError(null);
    try {
      const experiment = await createExperiment(engineName, params);
      navigate(`/experiments/${experiment.id}`);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="font-display text-3xl mb-1">New experiment</h1>
      <p className="text-ash text-sm mb-8">
        Choose an engine, tune its parameters, run.
      </p>

      {error && (
        <div className="mb-6 border border-red-500/50 bg-red-500/10 text-red-300 rounded px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {engines.length === 0 && !error && <p className="text-ash">Loading engines…</p>}

      {engines.length > 0 && (
        <>
          {/* Engine picker */}
          <EnginePicker engines={engines} selected={engineName} onSelect={selectEngine} />

          {/* Demo presets for the selected engine */}
          {engine && PRESETS.some((p) => p.engine === engine.name) && (
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <span className="text-xs text-ash uppercase tracking-wider">Presets</span>
              {PRESETS.filter((p) => p.engine === engine.name).map((preset) => (
                <button
                  key={preset.id}
                  data-testid={`preset-${preset.id}`}
                  title={preset.description}
                  onClick={() =>
                    setParams((prev) => ({
                      ...defaultsFrom(engine.param_schema),
                      ...prev,
                      ...preset.params,
                    }))
                  }
                  className="border border-edge rounded px-3 py-1.5 text-xs text-ash hover:border-lilac/60 hover:text-lilac transition-colors"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          )}

          {/* Form generated from param_schema */}
          {engine && (
            <ParamForm
              schema={engine.param_schema}
              params={params}
              onChange={updateParam}
              onSubmit={run}
              submitting={submitting}
              title={`Parameters — ${engine.name}`}
            />
          )}
        </>
      )}
    </div>
  );
}
