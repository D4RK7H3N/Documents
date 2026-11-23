/**
 * Render quality presets and the auto-downgrade policy for the 3D arena.
 *
 * The downgrade decision is a pure rolling-average check so it can be unit
 * tested: if the average frame time over `windowMs` stays above
 * `thresholdMs`, drop one quality level (never below "low").
 */

export const QUALITY_LEVELS = ["low", "med", "high"];

export const QUALITY_PRESETS = {
  low: { instanceCap: 100, particleCount: 60, dprMax: 1, antialias: false },
  med: { instanceCap: 250, particleCount: 120, dprMax: 1.5, antialias: true },
  high: { instanceCap: 400, particleCount: 200, dprMax: 2, antialias: true },
};

export function normalizeQuality(value) {
  return QUALITY_LEVELS.includes(value) ? value : "med";
}

export function nextQualityDowngrade(current) {
  const index = QUALITY_LEVELS.indexOf(normalizeQuality(current));
  return index > 0 ? QUALITY_LEVELS[index - 1] : null;
}

/** Default quality: mobile / touch devices start at Low per the phase spec. */
export function defaultQualityFor({ isTouch, hardwareConcurrency } = {}) {
  if (isTouch) return "low";
  if (typeof hardwareConcurrency === "number" && hardwareConcurrency <= 4) return "low";
  return "med";
}

/**
 * Rolling frame-time tracker: `add(frameTimeMs)` returns the quality level
 * to downgrade to (or null) when the window average stays above the
 * threshold for the full window.  Repeated triggers while already bad are
 * suppressed by the caller checking the returned value.
 */
export function createFrameTimeTracker({
  windowMs = 3000,
  thresholdMs = 25,
  maxSamples = 600,
} = {}) {
  let samples = [];
  return function add(frameTimeMs) {
    samples.push(frameTimeMs);
    if (samples.length > maxSamples) samples = samples.slice(-maxSamples);
    const cutoff = windowMs;
    // Window in samples: assume ~16ms frames when unknown.
    const windowSamples = Math.max(2, Math.round(cutoff / 16));
    if (samples.length < windowSamples) return null;
    const window = samples.slice(-windowSamples);
    const avg = window.reduce((a, b) => a + b, 0) / window.length;
    return avg > thresholdMs ? true : null;
  };
}

/** True when the tracked average frame time exceeds the threshold. */
export function averageFrameTime(samples) {
  if (!samples.length) return 0;
  return samples.reduce((a, b) => a + b, 0) / samples.length;
}

export function shouldDowngrade(samples, thresholdMs = 25) {
  return samples.length >= 30 && averageFrameTime(samples) > thresholdMs;
}
