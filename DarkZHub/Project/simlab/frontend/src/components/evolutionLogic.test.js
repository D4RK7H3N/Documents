import { describe, expect, it } from "vitest";
import {
  dotCountsForGeneration,
  dotLayout,
  generationSeed,
  incomingFreqFor,
  mulberry32,
  selectSurvivors,
  survivorDotCounts,
  totalDotsFor,
} from "./evolutionLogic.js";

const newEngineRecord = {
  gen: 1,
  freq: 0.0429,
  size: 2040,
  resistant_survivors: 100,
  normal_survivors: 1940,
};

const oldEngineRecord = { gen: 1, freq: 0.01, size: 2040 }; // no survivor fields

describe("dotCountsForGeneration", () => {
  it("splits dots by the recorded survivor ratio and sums to totalDots", () => {
    const counts = dotCountsForGeneration(newEngineRecord, 400);
    expect(counts.purple + counts.gray).toBe(400);
    // 100 resistant of 2040 survivors -> ~20 purple dots.
    expect(counts.purple).toBe(Math.round(400 * (100 / 2040)));
    expect(counts.gray).toBe(400 - counts.purple);
  });

  it("falls back to freq when resistant_survivors is missing", () => {
    const counts = dotCountsForGeneration(oldEngineRecord, 400);
    expect(counts.purple + counts.gray).toBe(400);
    expect(counts.purple).toBe(4); // round(400 * 0.01) ~ 1% share
    expect(counts.gray).toBe(396);
  });

  it("clamps degenerate records to valid counts", () => {
    expect(dotCountsForGeneration({ freq: 1.0, size: 10 }, 400)).toEqual({
      purple: 400,
      gray: 0,
    });
    expect(dotCountsForGeneration({ freq: 0.0, size: 0 }, 400)).toEqual({
      purple: 0,
      gray: 400,
    });
  });
});

describe("survivorDotCounts", () => {
  it("scales survivors by size/population and splits by recorded types", () => {
    const params = { population: 10000, pesticide_kill: 0.8 };
    const counts = survivorDotCounts(newEngineRecord, 0.01, params, 400);
    expect(counts.total).toBe(Math.round(400 * (2040 / 10000)));
    expect(counts.purple).toBe(Math.round(counts.total * (100 / 2040)));
    expect(counts.purple + counts.gray).toBe(counts.total);
  });

  it("derives the expected split when resistant_survivors is missing", () => {
    // E[rs] = freq = 0.01, E[ns] = (1-freq)*(1-kill) = 0.99*0.2 = 0.198
    // share = 0.01 / 0.208 ~ 0.0481 of ~82 survivor dots -> 4 purple.
    const params = { population: 10000, pesticide_kill: 0.8 };
    const counts = survivorDotCounts(oldEngineRecord, 0.01, params, 400);
    expect(counts.total).toBe(82);
    expect(counts.purple).toBe(4);
  });

  it("returns zero for an extinct generation", () => {
    const counts = survivorDotCounts(
      { freq: 0, size: 0 },
      0,
      { population: 15 },
      15
    );
    expect(counts).toEqual({ purple: 0, gray: 0, total: 0 });
  });
});

describe("selectSurvivors (seeded selection)", () => {
  it("is deterministic for the same seed", () => {
    const a = selectSurvivors(400, 82, 1234);
    const b = selectSurvivors(400, 82, 1234);
    expect([...a].sort((x, y) => x - y)).toEqual([...b].sort((x, y) => x - y));
  });

  it("yields exactly the requested survivor count within bounds", () => {
    const set = selectSurvivors(400, 82, 99);
    expect(set.size).toBe(82);
    for (const idx of set) {
      expect(idx).toBeGreaterThanOrEqual(0);
      expect(idx).toBeLessThan(400);
    }
  });

  it("differs across seeds (different generations look different)", () => {
    const a = selectSurvivors(400, 200, 1);
    const b = selectSurvivors(400, 200, 2);
    expect(a).not.toEqual(b);
  });

  it("selects nobody when the population is extinct", () => {
    expect(selectSurvivors(400, 0, 42).size).toBe(0);
  });
});

describe("totalDotsFor", () => {
  it("caps at 400 and matches tiny populations one-to-one", () => {
    expect(totalDotsFor({ population: 10000 })).toBe(400);
    expect(totalDotsFor({ population: 15 })).toBe(15);
    expect(totalDotsFor({})).toBe(400);
  });
});

describe("helpers", () => {
  it("mulberry32 is deterministic", () => {
    const a = mulberry32(7);
    const b = mulberry32(7);
    expect([a(), a(), a()]).toEqual([b(), b(), b()]);
  });

  it("generationSeed separates generations", () => {
    expect(generationSeed(42, 0)).not.toBe(generationSeed(42, 1));
  });

  it("incomingFreqFor uses start_freq for gen 1 then the previous freq", () => {
    const gens = [{ freq: 0.2 }, { freq: 0.5 }];
    expect(incomingFreqFor(0, gens, { start_freq: 0.01 })).toBe(0.01);
    expect(incomingFreqFor(1, gens, { start_freq: 0.01 })).toBe(0.2);
    expect(incomingFreqFor(2, gens, { start_freq: 0.01 })).toBe(0.5);
  });

  it("dotLayout is deterministic per seed", () => {
    const a = dotLayout(50, 800, 300, 123);
    const b = dotLayout(50, 800, 300, 123);
    expect(a).toEqual(b);
    expect(a).toHaveLength(50);
    for (const dot of a) {
      expect(dot.x).toBeGreaterThanOrEqual(0);
      expect(dot.x).toBeLessThanOrEqual(800);
    }
  });
});
