/**
 * Species registry for the 3D evolution view.
 *
 * A species is a pure visualization choice: it never reaches the engine.
 * Every species is either procedural (bodyBuilder merges three.js
 * primitives into one BufferGeometry per body-part group so it can be
 * instanced) or a glb model (modelUrl, loaded with useGLTF; must fall
 * back to procedural if loading fails).  See README.md before committing
 * any third-party model file.
 *
 * This module is only imported by the lazy 3D chunk, so pulling in three
 * via procedural.js does not grow the main bundle.
 */
import { buildBeetle, buildFruitFly, buildMosquito } from "./procedural.js";

export const MOTIONS = ["fly", "crawl", "swim"];

/**
 * Validate one species config. Returns a list of problems (empty = valid)
 * so tests and the registry can fail loudly on bad definitions.
 */
export function validateSpeciesConfig(species) {
  const problems = [];
  const push = (msg) => problems.push(`${species?.id ?? "?"}: ${msg}`);

  if (!species || typeof species !== "object") return ["species must be an object"];
  if (typeof species.id !== "string" || !/^[a-z][a-z0-9_]*$/.test(species.id)) {
    push("id must be a lowercase identifier");
  }
  if (typeof species.name !== "string" || !species.name) push("name is required");
  if (typeof species.bodyBuilder !== "function" && typeof species.modelUrl !== "string") {
    push("needs a bodyBuilder function or a modelUrl string");
  }
  if (typeof species.scale !== "number" || species.scale <= 0) push("scale must be > 0");
  if (!Number.isInteger(species.wingCount) || species.wingCount < 0) {
    push("wingCount must be a non-negative integer");
  }
  if (!Number.isInteger(species.legCount) || species.legCount < 0) {
    push("legCount must be a non-negative integer");
  }
  for (const key of ["baseColor", "resistantColor"]) {
    if (typeof species[key] !== "string" || !/^#[0-9a-fA-F]{6}$/.test(species[key] ?? "")) {
      push(`${key} must be a #rrggbb color`);
    }
  }
  if (!MOTIONS.includes(species.motion)) push(`motion must be one of ${MOTIONS.join(", ")}`);
  if (typeof species.speed !== "number" || species.speed < 0) push("speed must be >= 0");
  if (typeof species.hoverAmplitude !== "number" || species.hoverAmplitude < 0) {
    push("hoverAmplitude must be >= 0");
  }
  if (typeof species.flapHz !== "number" || species.flapHz < 0) push("flapHz must be >= 0");
  if (species.motion === "fly" && species.wingCount > 0 && species.flapHz === 0) {
    push("flying species with wings need flapHz > 0");
  }
  return problems;
}

export const SPECIES = [
  {
    id: "mosquito",
    name: "Mosquito",
    bodyBuilder: buildMosquito,
    scale: 1.15,
    wingCount: 2,
    legCount: 6,
    baseColor: "#8d8598",
    resistantColor: "#a78bfa",
    motion: "fly",
    speed: 1.0,
    hoverAmplitude: 0.35,
    flapHz: 26,
  },
  {
    id: "beetle",
    name: "Beetle",
    bodyBuilder: buildBeetle,
    scale: 1.0,
    wingCount: 0,
    legCount: 6,
    baseColor: "#7d6e63",
    resistantColor: "#a78bfa",
    motion: "crawl",
    speed: 0.45,
    hoverAmplitude: 0,
    flapHz: 0,
  },
  {
    id: "fruit_fly",
    name: "Fruit fly",
    bodyBuilder: buildFruitFly,
    scale: 0.8,
    wingCount: 2,
    legCount: 6,
    baseColor: "#9a8f7a",
    resistantColor: "#a78bfa",
    motion: "fly",
    speed: 1.35,
    hoverAmplitude: 0.3,
    flapHz: 34,
  },
];

/** All valid species (validated on import so a bad config fails fast). */
export const SPECIES_LIST = (() => {
  for (const species of SPECIES) {
    const problems = validateSpeciesConfig(species);
    if (problems.length) throw new Error(`Invalid species config: ${problems.join("; ")}`);
  }
  return SPECIES;
})();

export const DEFAULT_SPECIES_ID = "mosquito";

export function getSpecies(id) {
  return SPECIES_LIST.find((s) => s.id === id) ?? null;
}

/** Resolve a stored/selected species id to a config, with a safe fallback. */
export function resolveSpecies(id) {
  return getSpecies(id) ?? getSpecies(DEFAULT_SPECIES_ID);
}
