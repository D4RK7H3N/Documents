import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createSweep, fetchEngines } from "../api.js";
import EnginePicker from "../components/EnginePicker.jsx";
import ParamForm from "../components/ParamForm.jsx";

const MAX_RUNS = 300;
const MAX_SWEEP_PARAMS = 2;

/** Linear range of `steps` values; integer params get rounded unique ints. */
function linearRange(min, max, steps, isInteger) {
  const values = [];
  for (let i = 0; i < steps; i++) {
    const v = min + ((max - min) * i) / (steps - 1);
    values.push(isInteger ? Math.round(v) : Number(v.toFixed(6)));
  }
  return isInteger ? [...new Set(values)] : values;
}

function defaultsFrom(schema) {
  const params = {};
  for (const [name, spec] of Object.entries(schema)) params[name] = spec.default;
  return params;
}

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

/** Small bounded number input with a label. */
function RangeInput({ label, value, onChange, min, max }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-ash">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
        className="w-24 bg-void border border-edge rounded px-2 py-1 text-sm text-ink text-right focus:border-lilac focus:outline-none"
      />
    </label>
  );
}

export default function SweepPage() {
  const [engines, setEngines] = useState([]);
  const [engineName, setEngineName] = useState(null);
  const [selected, setSelected] = useState([]); // swept param names (max 2)
  const [ranges, setRanges] = useState({}); // {name: {min, max, steps}}
  const [replicates, setReplicates] = useState(3);
  const [baseParams, setBaseParams] = useState({});
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchEngines()
      .then((data) => {
        setEngines(data);
        if (data.length > 0) {
          setEngineName(data[0].name);
          setBaseParams(defaultsFrom(data[0].param_schema));
        }
      })
      .catch((err) => setError(formatApiError(err)));
  }, []);

  const engine = engines.find((e) => e.name === engineName);
  // Seed is derived per replicate, so it cannot be swept.
  const sweepable = useMemo(
    () =>
      Object.entries(engine?.param_schema ?? {}).filter(([name]) => name !== "seed"),
    [engine]
  );

  function selectEngine(name) {
    setEngineName(name);
    setSelected([]);
    setRanges({});
    setBaseParams(defaultsFrom(engines.find((e) => e.name === name).param_schema));
  }

  function toggleParam(name) {
    setSelected((prev) => {
      if (prev.includes(name)) return prev.filter((p) => p !== name);
      if (prev.length >= MAX_SWEEP_PARAMS) return prev; // max 2 params
      const spec = engine.param_schema[name];
      setRanges((r) => ({
        ...r,
        [name]: {
          min: spec.min ?? 0,
          max: spec.max ?? (spec.min ?? 0) + 10,
          steps: 4,
        },
      }));
      return [...prev, name];
    });
  }

  function setRange(name, key, value) {
    setRanges((prev) => ({ ...prev, [name]: { ...prev[name], [key]: value } }));
  }

  // Live run count: product of the generated ranges x replicates.
  const valueLists = useMemo(() => {
    if (!engine) return [];
    return selected.map((name) => {
      const r = ranges[name] ?? {};
      const spec = engine.param_schema[name];
      const min = Number(r.min);
      const max = Number(r.max);
      const steps = Number(r.steps);
      if (!Number.isFinite(min) || !Number.isFinite(max) || !Number.isFinite(steps) || steps < 2 || max < min) {
        return [];
      }
      return linearRange(min, max, steps, spec.type === "integer");
    });
  }, [engine, selected, ranges]);

  const totalCombos = valueLists.reduce((acc, list) => acc * list.length, selected.length ? 1 : 0);
  const totalRuns = totalCombos * replicates;
  const rangesValid = selected.length > 0 && valueLists.every((l) => l.length > 0);
  const overCap = totalRuns > MAX_RUNS;
  const canSubmit = rangesValid && !overCap && !submitting;

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      // Swept params are excluded from base_params: the ranges define them.
      const base = Object.fromEntries(
        Object.entries(baseParams).filter(([name]) => !selected.includes(name))
      );
      const sweep = Object.fromEntries(selected.map((name, i) => [name, valueLists[i]]));
      const created = await createSweep({
        engine: engineName,
        base_params: base,
        sweep,
        replicates,
      });
      navigate(`/sweeps/${created.id}`);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="font-display text-3xl mb-1">New sweep</h1>
      <p className="text-ash text-sm mb-8">
        Sweep 1-2 parameters over a range; every combination runs once per replicate.
      </p>

      {error && (
        <div className="mb-6 border border-red-500/50 bg-red-500/10 text-red-300 rounded px-4 py-3 text-sm whitespace-pre-wrap">
          {error}
        </div>
      )}

      {engines.length === 0 && !error && <p className="text-ash">Loading engines…</p>}

      {engine && (
        <>
          <EnginePicker engines={engines} selected={engineName} onSelect={selectEngine} />

          {/* Step 1: choose swept parameters */}
          <section className="bg-panel border border-edge rounded-lg p-6 mb-6">
            <h2 className="font-display text-xl mb-2">
              Swept parameters{" "}
              <span className="text-ash text-sm font-sans">— pick 1 or 2</span>
            </h2>
            <div className="flex flex-wrap gap-2 mb-4">
              {sweepable.map(([name, spec]) => (
                <button
                  key={name}
                  onClick={() => toggleParam(name)}
                  className={`border rounded px-3 py-1.5 text-sm transition-colors ${
                    selected.includes(name)
                      ? "border-lilac bg-lilac/10 text-lilac"
                      : "border-edge text-ash hover:border-lilac/50"
                  }`}
                >
                  {name}
                </button>
              ))}
            </div>

            {selected.map((name) => {
              const r = ranges[name] ?? {};
              const spec = engine.param_schema[name];
              const preview = valueLists[selected.indexOf(name)];
              return (
                <div key={name} className="border-t border-edge/60 py-3">
                  <div className="text-sm text-ink mb-2">
                    {name} <span className="text-xs text-ash">{spec.type}</span>
                  </div>
                  <div className="flex flex-wrap items-end gap-4">
                    <RangeInput label="min" value={r.min} onChange={(v) => setRange(name, "min", v)} />
                    <RangeInput label="max" value={r.max} onChange={(v) => setRange(name, "max", v)} />
                    <RangeInput label="steps" value={r.steps} onChange={(v) => setRange(name, "steps", v)} min={2} />
                    <span className="text-xs text-ash flex-1 min-w-48 truncate">
                      {preview && preview.length
                        ? `values: ${preview.map((v) => (Number.isInteger(v) ? v : v.toFixed(3))).join(", ")}`
                        : "invalid range (need max >= min, steps >= 2)"}
                    </span>
                  </div>
                </div>
              );
            })}
          </section>

          {/* Step 2: replicates + base params + live run count */}
          <section className="bg-panel border border-edge rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-display text-xl">Replicates</h2>
              <div className="flex items-center gap-4">
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={replicates}
                  onChange={(e) => setReplicates(Number(e.target.value))}
                  className="w-20 bg-void border border-edge rounded px-2 py-1 text-sm text-ink text-right focus:border-lilac focus:outline-none"
                />
                <span className="text-sm">
                  <span data-testid="total-runs" className={overCap ? "text-red-400 font-medium" : "text-lilac"}>
                    {totalRuns} runs
                  </span>
                  <span className="text-ash text-xs ml-2">
                    ({totalCombos} combinations x {replicates} replicates, cap {MAX_RUNS})
                  </span>
                </span>
              </div>
            </div>
            {overCap && (
              <p className="text-xs text-red-400">
                {totalRuns} runs exceeds the cap of {MAX_RUNS}. Reduce the ranges or replicates.
              </p>
            )}
            <p className="text-xs text-ash mt-1">
              Replicate i runs with seed = base seed + i, so every sweep is reproducible.
            </p>
          </section>

          {selected.length > 0 && (
            <ParamForm
              schema={Object.fromEntries(
                Object.entries(engine.param_schema).filter(([name]) => !selected.includes(name))
              )}
              params={baseParams}
              onChange={(name, value) =>
                setBaseParams((prev) => ({ ...prev, [name]: value }))
              }
              onSubmit={submit}
              submitting={submitting}
              disabled={!canSubmit}
              title={`Base parameters — ${engine.name}`}
            />
          )}
        </>
      )}
    </div>
  );
}
