/**
 * Deterministic insect motion for the 3D arena.
 *
 * Everything is a pure function of (experiment seed, generation index,
 * instance index, time): the same inputs always produce the same pose, so
 * scrubbing to any generation renders the same scene without animation
 * history.  Randomness comes from the shared mulberry32/generationSeed
 * helpers so 2D and 3D agree on per-generation seeds.
 */
import { generationSeed, mulberry32 } from "../evolutionLogic.js";

export const ARENA = {
  radius: 10, // ground disc radius
  ceiling: 4.5, // max flight height
  ground: 0, // crawl plane
};

/**
 * Per-instance locomotion traits for one generation. Homes are re-seeded
 * every generation (seed + generation + index), per the phase spec.
 */
export function insectTraits(seed, genIndex, index, species) {
  const rng = mulberry32((generationSeed(seed, genIndex) + index * 7919) >>> 0);
  const r = Math.sqrt(rng()) * ARENA.radius * 0.88;
  const theta = rng() * Math.PI * 2;
  const flying = species.motion === "fly";
  const swimming = species.motion === "swim";
  const baseY = flying
    ? 0.8 + rng() * (ARENA.ceiling - 1.2)
    : swimming
      ? 0.8 + rng() * 1.4
      : ARENA.ground;
  return {
    homeX: Math.cos(theta) * r,
    homeZ: Math.sin(theta) * r,
    baseY,
    heading0: rng() * Math.PI * 2,
    wanderA: 0.6 + rng() * 1.2, // primary wander radius multiplier
    w1: 0.35 + rng() * 0.5, // wander angular frequencies (irrational-ish)
    w2: 0.11 + rng() * 0.23,
    p1: rng() * Math.PI * 2,
    p2: rng() * Math.PI * 2,
    p3: rng() * Math.PI * 2,
    flapPhase: rng() * Math.PI * 2,
    legPhase: rng() * Math.PI * 2,
    hoverPhase: rng() * Math.PI * 2,
    bobPhase: rng() * Math.PI * 2,
  };
}

/** Position at time t (seconds, generation-local) for one insect. */
export function insectPosition(traits, t, species) {
  const sp = species.speed;
  const wx =
    traits.homeX +
    Math.sin(t * traits.w1 * sp + traits.p1) * traits.wanderA +
    Math.sin(t * traits.w2 * sp + traits.p2) * traits.wanderA * 0.45;
  const wz =
    traits.homeZ +
    Math.cos(t * traits.w1 * 0.8 * sp + traits.p2) * traits.wanderA +
    Math.sin(t * traits.w2 * 1.3 * sp + traits.p3) * traits.wanderA * 0.45;
  const hover =
    species.motion === "fly"
      ? Math.sin(t * 1.7 * sp + traits.hoverPhase) * species.hoverAmplitude
      : species.motion === "swim"
        ? Math.sin(t * 1.1 * sp + traits.hoverPhase) * species.hoverAmplitude
        : 0;
  // Crawlers stay glued to the ground plane; fliers bob subtly.
  const bob =
    species.motion === "crawl" ? 0 : Math.sin(t * 0.9 + traits.bobPhase) * 0.05;
  return { x: wx, y: traits.baseY + hover + bob, z: wz };
}

/** Full pose for one insect at time t: position + heading + animation phases. */
export function insectPose(seed, genIndex, index, t, species) {
  const traits = insectTraits(seed, genIndex, index, species);
  const pos = insectPosition(traits, t, species);
  // Heading from the velocity direction (finite difference).
  const eps = 0.05;
  const ahead = insectPosition(traits, t + eps, species);
  const dx = ahead.x - pos.x;
  const dz = ahead.z - pos.z;
  const heading =
    Math.hypot(dx, dz) > 1e-5 ? Math.atan2(dx, dz) : traits.heading0;
  return {
    ...pos,
    heading,
    flapAngle: Math.sin(t * species.flapHz * Math.PI * 2 + traits.flapPhase),
    legSwing: Math.sin(t * 7 * species.speed + traits.legPhase),
    hoverBob: Math.sin(t * 2 * species.speed + traits.hoverPhase),
  };
}
