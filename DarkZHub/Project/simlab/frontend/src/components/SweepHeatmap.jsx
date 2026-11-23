import { formatTick, METRICS, scaleColor } from "./sweepMetrics.js";

/**
 * 2D sweep heatmap built as a CSS grid (no chart library).
 * Rows: values of param_a; columns: values of param_b.
 * Cell color encodes the selected metric; cells where some replicates
 * never reached 50% carry a small amber marker. Clicking selects a cell.
 */
export default function SweepHeatmap({ axes, cells, metricKey, onSelectCell }) {
  const metric = METRICS[metricKey];

  const values = (cells ?? []).map(metric.pick).filter((v) => v != null);
  const min = values.length ? Math.min(...values) : null;
  const max = values.length ? Math.max(...values) : null;
  const span = max - min || 1;

  const colorFor = (cell) => {
    const v = metric.pick(cell);
    if (v == null) return "rgb(34, 30, 45)"; // no usable data in this cell
    let t = (v - min) / span;
    if (metric.lowerIsBetter) t = 1 - t; // highlight faster rises
    return scaleColor(t);
  };

  const tooltipFor = (cell) =>
    `${metric.label}: ${metric.fmt(metric.pick(cell))} ` +
    `(std ${metric.fmt(metric.std(cell))}) · runs ${cell.n} · ` +
    `never reached 50%: ${cell.n_never_reached} · failed: ${cell.n_failed}`;

  return (
    <div>
      <div className="inline-block overflow-x-auto pb-2">
        <div
          className="inline-grid gap-1 text-xs"
          style={{
            gridTemplateColumns: `auto repeat(${axes.values_b.length}, minmax(76px, 76px))`,
          }}
        >
          {/* Header row: corner label + b values */}
          <div className="text-ash text-right pr-2 self-end">
            {axes.param_a} \ {axes.param_b}
          </div>
          {axes.values_b.map((b) => (
            <div key={`col-${b}`} data-testid="col-header" className="text-center text-ash pb-1">
              {formatTick(b)}
            </div>
          ))}

          {/* One grid row per a value */}
          {axes.values_a.map((a, aIdx) => (
            <div key={`row-${a}`} className="contents">
              <div data-testid="row-header" className="text-ash text-right pr-2 self-center">
                {formatTick(a)}
              </div>
              {cells
                .filter((c) => c.a_index === aIdx)
                .sort((x, y) => x.b_index - y.b_index)
                .map((cell) => (
                  <button
                    key={`${cell.a_index}-${cell.b_index}`}
                    data-testid="heat-cell"
                    title={tooltipFor(cell)}
                    onClick={() => onSelectCell(cell)}
                    className="relative h-14 rounded border border-edge/70 hover:border-lilac transition-colors flex flex-col items-center justify-center"
                    style={{ backgroundColor: colorFor(cell) }}
                  >
                    <span className={metric.pick(cell) == null ? "text-ash" : "text-ink"}>
                      {metric.fmt(metric.pick(cell))}
                    </span>
                    {cell.n_never_reached > 0 && (
                      <span
                        data-testid="never-marker"
                        title={`${cell.n_never_reached} replicate(s) never reached 50%`}
                        className="absolute top-1 right-1 w-2 h-2 rounded-full bg-amber-400"
                      />
                    )}
                  </button>
                ))}
            </div>
          ))}
        </div>
      </div>

      {/* Color scale legend */}
      <div className="flex items-center gap-3 mt-3 text-xs text-ash">
        <span>
          {min == null ? "n/a" : metric.fmt(min)}
          {metric.lowerIsBetter ? " (faster)" : ""}
        </span>
        <div
          className="w-44 h-3 rounded border border-edge/60"
          style={{
            background: `linear-gradient(90deg, ${scaleColor(
              metric.lowerIsBetter ? 1 : 0
            )}, ${scaleColor(metric.lowerIsBetter ? 0 : 1)})`,
          }}
        />
        <span>
          {max == null ? "n/a" : metric.fmt(max)}
          {metric.lowerIsBetter ? " (slower)" : ""}
        </span>
        <span className="ml-2 flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-400" /> never
          reached 50%
        </span>
      </div>
    </div>
  );
}
