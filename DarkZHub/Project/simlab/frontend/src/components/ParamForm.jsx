/**
 * Shared parameter form, generated from an engine's param_schema.
 * Reused by NewExperiment and (later) the sweep page.
 */

/** Validate params against the schema; returns {paramName: message} for bad values. */
export function validateParams(schema, params) {
  const errors = {};
  for (const [name, spec] of Object.entries(schema)) {
    const value = params[name];
    if (value === "" || value === null || value === undefined || Number.isNaN(Number(value))) {
      errors[name] = "value required";
    } else if (spec.min !== undefined && Number(value) < spec.min) {
      errors[name] = `must be >= ${spec.min}`;
    } else if (spec.max !== undefined && Number(value) > spec.max) {
      errors[name] = `must be <= ${spec.max}`;
    }
  }
  return errors;
}

/** One schema parameter: range slider (when bounded) + number input. */
function ParamField({ name, spec, value, error, onChange }) {
  const bounded = spec.min !== undefined && spec.max !== undefined;
  const step = spec.type === "integer" ? 1 : 0.01;
  return (
    <div className="py-3" data-testid={`field-${name}`}>
      <div className="flex items-baseline justify-between mb-2">
        <label className="text-sm text-ink">
          {name}
          <span className="ml-2 text-xs text-ash">{spec.type}</span>
        </label>
        <span className="text-xs text-ash">default {spec.default}</span>
      </div>
      <div className="flex items-center gap-4">
        {bounded && (
          <input
            type="range"
            min={spec.min}
            max={spec.max}
            step={step}
            value={Number(value)}
            onChange={(e) => onChange(name, Number(e.target.value))}
            className="flex-1"
          />
        )}
        <input
          type="number"
          value={value}
          min={spec.min}
          max={spec.max}
          step={step}
          onChange={(e) =>
            onChange(name, e.target.value === "" ? "" : Number(e.target.value))
          }
          className={`w-28 bg-void border rounded px-2 py-1 text-sm text-ink text-right focus:border-lilac focus:outline-none ${
            error ? "border-red-500/70" : "border-edge"
          }`}
        />
      </div>
      {error && (
        <p className="mt-1 text-xs text-red-400">
          {name} {error}
        </p>
      )}
    </div>
  );
}

/**
 * Form card for one engine's parameters.  Out-of-range or empty values are
 * flagged per field and the Run button is disabled until everything is valid.
 */
export default function ParamForm({
  schema,
  params,
  onChange,
  onSubmit,
  submitting = false,
  disabled = false,
  title = "Parameters",
}) {
  const errors = validateParams(schema, params);
  const isValid = Object.keys(errors).length === 0;

  return (
    <section className="bg-panel border border-edge rounded-lg p-6">
      <h2 className="font-display text-xl mb-2">{title}</h2>
      <div className="divide-y divide-edge/60">
        {Object.entries(schema).map(([name, spec]) => (
          <ParamField
            key={name}
            name={name}
            spec={spec}
            value={params[name]}
            error={errors[name]}
            onChange={onChange}
          />
        ))}
      </div>
      <button
        onClick={onSubmit}
        disabled={!isValid || submitting || disabled}
        className="mt-6 w-full sm:w-auto px-8 py-2.5 rounded bg-lilac text-void font-medium hover:bg-lilac/85 disabled:opacity-50 disabled:hover:bg-lilac transition-colors"
      >
        {submitting ? "Starting…" : "Run experiment"}
      </button>
    </section>
  );
}
