import { describe, expect, it } from "vitest";
import { getSpecies } from "../../species/registry.js";
import { insectPose, insectTraits } from "./motion.js";

const mosquito = getSpecies("mosquito");
const beetle = getSpecies("beetle");

describe("deterministic 3D motion", () => {
  it("returns identical poses for identical (seed, generation, index, time)", () => {
    const a = insectPose(42, 7, 3, 1.234, mosquito);
    const b = insectPose(42, 7, 3, 1.234, mosquito);
    expect(a).toEqual(b);
  });

  it("differs across instances, generations and seeds", () => {
    const base = JSON.stringify(insectPose(42, 0, 0, 1, mosquito));
    expect(JSON.stringify(insectPose(42, 0, 1, 1, mosquito))).not.toBe(base);
    expect(JSON.stringify(insectPose(42, 1, 0, 1, mosquito))).not.toBe(base);
    expect(JSON.stringify(insectPose(99, 0, 0, 1, mosquito))).not.toBe(base);
  });

  it("keeps flying species inside the bounded volume and above ground", () => {
    for (let i = 0; i < 50; i++) {
      const pose = insectPose(7, 3, i, 1.7, mosquito);
      expect(Math.hypot(pose.x, pose.z)).toBeLessThanOrEqual(12);
      expect(pose.y).toBeGreaterThan(0);
      expect(pose.y).toBeLessThan(6);
    }
  });

  it("crawling species stay on the ground plane", () => {
    for (let i = 0; i < 20; i++) {
      const pose = insectPose(7, 2, i, 2.5, beetle);
      expect(pose.y).toBeCloseTo(0, 5);
    }
  });

  it("traits are stable per (seed, generation, index) and homes vary per generation", () => {
    const t1 = insectTraits(42, 0, 5, mosquito);
    const t2 = insectTraits(42, 0, 5, mosquito);
    expect(t1).toEqual(t2);
    const otherGen = insectTraits(42, 1, 5, mosquito);
    expect(otherGen.homeX).not.toBe(t1.homeX);
  });

  it("heading tracks the wander direction", () => {
    const pose = insectPose(42, 4, 9, 0.8, mosquito);
    expect(Number.isFinite(pose.heading)).toBe(true);
    expect(Number.isFinite(pose.flapAngle)).toBe(true);
    expect(Number.isFinite(pose.legSwing)).toBe(true);
  });
});
