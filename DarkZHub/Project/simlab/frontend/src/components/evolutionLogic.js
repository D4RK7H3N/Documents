/**
 * Pure logic for the Live Evolution View (EvolutionArena).
 *
 * Everything here is deterministic and scrub-safe: the state for any
 * generation is computed from (experiment seed, generation index) alone,
 * never from animation history.
 */

/** Cap on rendered dots. */
export const MAX_DOTS = 400;

/** Deterministic PRNG (mulberry32). */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** How many dots to render: up to MAX_DOTS, at most one per insect. */
export function totalDotsFor(params) {
  const population = Number(params?.population ?? 0);
  if (!Number.isFinite(population) || population <= 0) return MAX_DOTS;
  return Math.max(1, Math.min(MAX_DOTS, Math.round(population)));
}

/** Per-generation PRNG seed derived from the experiment seed. */
export function generationSeed(experimentSeed, generationIndex) {
  return (Number(experimentSeed ?? 0) >>> 0) * 7919 + generationIndex;
}

/**
 * Purple/gray dot split for a generation record's population ratio.
 * Uses resistant_survivors/size when the field exists (engine >= 1.1.0);
 * falls back to freq for older stored results. Sums to totalDots.
 */
export function dotCountsForGeneration(generation, totalDots) {
  const size = generation?.size ?? 0;
  let purple;
  if (generation && generation.resistant_survivors != null && size > 0) {
    purple = Math.round(totalDots * (generation.resistant_survivors / size));
  } else {
    purple = Math.round(totalDots * (generation?.freq ?? 0));
  }
  purple = Math.max(0, Math.min(totalDots, purple));
  return { purple, gray: totalDots - purple };
}

/** Frequency of the population that enters generation `index` (pre-spray). */
export function incomingFreqFor(index, generations, params) {
  if (index <= 0) return Number(params?.start_freq ?? 0);
  return Number(generations?.[index - 1]?.freq ?? 0);
}

/**
 * Generation (1-based) where the resistant allele first reaches `threshold`
 * of the population, or null if it never does within the run.
 */
export function fixationGeneration(generations, threshold = 0.99) {
  for (const record of generations ?? []) {
    if (Number(record?.freq ?? 0) >= threshold) return record.gen;
  }
  return null;
}

/**
 * Dots still alive after the pesticide for generation `index`.
 * Total scales with size/population; the purple/gray split uses the
 * recorded resistant_survivors/normal_survivors when present, otherwise
 * derives the expected split: resistant always survive, normal survive
 * with (1 - kill), so E[rs] = freq, E[ns] = (1-freq)*(1-kill).
 */
export function survivorDotCounts(generation, incomingFreq, params, totalDots) {
  const size = Number(generation?.size ?? 0);
  const population = Number(params?.population ?? 0) || 1;
  if (size <= 0) return { purple: 0, gray: 0, total: 0 };
  const total = Math.max(0, Math.round(totalDots * (size / population)));
  let purple;
  if (generation.resistant_survivors != null) {
    purple = Math.round(total * (generation.resistant_survivors / size));
  } else {
    const kill = Number(params?.pesticide_kill ?? 0);
    const expectedResistant = incomingFreq;
    const expectedNormal = (1 - incomingFreq) * (1 - kill);
    const share =
      expectedResistant + expectedNormal > 0
        ? expectedResistant / (expectedResistant + expectedNormal)
        : 0;
    purple = Math.round(total * share);
  }
  purple = Math.max(0, Math.min(total, purple));
  return { purple, gray: total - purple, total };
}

/**
 * Deterministic selection: which dot indices survive. A seeded partial
 * Fisher-Yates picks `survivorCount` indices from `totalDots`; the same
 * seed always yields the same set.
 */
export function selectSurvivors(totalDots, survivorCount, seed) {
  const rng = mulberry32(seed);
  const indices = Array.from({ length: totalDots }, (_, i) => i);
  const take = Math.max(0, Math.min(survivorCount, totalDots));
  for (let i = 0; i < take; i++) {
    const j = i + Math.floor(rng() * (totalDots - i));
    [indices[i], indices[j]] = [indices[j], indices[i]];
  }
  return new Set(indices.slice(0, take));
}

/** Which dot indices carry the purple color in a population state. */
export function selectColored(purpleCount, totalDots, seed) {
  return selectSurvivors(totalDots, purpleCount, seed);
}

/** Seeded home positions/wandering parameters for one generation's dots. */
export function dotLayout(totalDots, width, height, seed) {
  const rng = mulberry32(seed);
  const pad = 22;
  const w = Math.max(1, width - pad * 2);
  const h = Math.max(1, height - pad * 2);
  return Array.from({ length: totalDots }, () => ({
    x: pad + rng() * w,
    y: pad + rng() * h,
    angle: rng() * Math.PI * 2,
    phase: rng() * Math.PI * 2,
    speed: 0.6 + rng() * 1.6,
    wobble: 4 + rng() * 9,
  }));
}
