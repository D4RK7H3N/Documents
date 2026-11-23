import { describe, expect, it } from "vitest";
import {
  DEFAULT_SPECIES_ID,
  MOTIONS,
  SPECIES_LIST,
  getSpecies,
  resolveSpecies,
  validateSpeciesConfig,
} from "./registry.js";

describe("species registry", () => {
  it("ships the three procedural species with unique ids", () => {
    const ids = SPECIES_LIST.map((s) => s.id);
    expect(ids).toEqual(["mosquito", "beetle", "fruit_fly"]);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("every shipped species passes validation", () => {
    for (const species of SPECIES_LIST) {
      expect(validateSpeciesConfig(species)).toEqual([]);
    }
  });

  it("rejects configs with bad fields", () => {
    expect(validateSpeciesConfig(null).length).toBeGreaterThan(0);
    expect(validateSpeciesConfig({ id: "X" }).length).toBeGreaterThan(0);
    expect(
      validateSpeciesConfig({
        id: "ok_id",
        name: "Ok",
        bodyBuilder: () => {},
        scale: 1,
        wingCount: 2,
        legCount: 6,
        baseColor: "purple",
        resistantColor: "#a78bfa",
        motion: "teleport",
        speed: 1,
        hoverAmplitude: 0,
        flapHz: 10,
      })
    ).toEqual(
      expect.arrayContaining([
        expect.stringContaining("baseColor"),
        expect.stringContaining("motion must be one of"),
      ])
    );
  });

  it("requires flapHz for winged fliers", () => {
    const problems = validateSpeciesConfig({
      id: "wasp",
      name: "Wasp",
      bodyBuilder: () => {},
      scale: 1,
      wingCount: 2,
      legCount: 6,
      baseColor: "#888888",
      resistantColor: "#a78bfa",
      motion: "fly",
      speed: 1,
      hoverAmplitude: 0.3,
      flapHz: 0,
    });
    expect(problems).toEqual([expect.stringContaining("flapHz")]);
  });

  it("motion enum covers fly/crawl/swim", () => {
    expect(MOTIONS).toEqual(["fly", "crawl", "swim"]);
  });

  it("getSpecies returns null for unknown ids; resolveSpecies falls back", () => {
    expect(getSpecies("dragon")).toBeNull();
    expect(resolveSpecies("dragon").id).toBe(DEFAULT_SPECIES_ID);
    expect(resolveSpecies("beetle").id).toBe("beetle");
  });
});
