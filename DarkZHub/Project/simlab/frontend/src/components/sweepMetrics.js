/**
 * Shared sweep metric definitions and the dark -> purple color scale.
 * Used by both the heatmap (2D sweeps) and the line chart (1D sweeps).
 */

export const METRICS = {
  gen50: {
    key: "gen50",
    label: "mean gen to 50%",
    pick: (cell) => cell.gen50_mean,
    std: (cell) => cell.gen50_std,
    // Faster rise (lower generation) is highlighted with stronger purple.
    lowerIsBetter: true,
    fmt: (v) => (v == null ? "n/a" : Number(v).toFixed(1)),
  },
  final_freq: {
    key: "final_freq",
    label: "mean final freq",
    pick: (cell) => cell.final_freq_mean,
    std: (cell) => cell.final_freq_std,
    lowerIsBetter: false,
    fmt: (v) => (v == null ? "n/a" : Number(v).toFixed(3)),
  },
};

const DARK = [24, 20, 36]; // near-black panel tone
const LILAC = [167, 139, 250]; // purple accent #a78bfa

/** Interpolate between the dark and purple endpoints; t in [0, 1]. */
export function scaleColor(t) {
  const c = DARK.map((d, i) => Math.round(d + (LILAC[i] - d) * Math.min(1, Math.max(0, t))));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

/** Compact axis tick label: integers plain, floats to 2 decimals. */
export function formatTick(value) {
  return Number.isInteger(value) ? String(value) : Number(value).toFixed(2);
}
