import { describe, expect, it } from "vitest";
import {
  QUALITY_LEVELS,
  QUALITY_PRESETS,
  averageFrameTime,
  createFrameTimeTracker,
  defaultQualityFor,
  nextQualityDowngrade,
  normalizeQuality,
  shouldDowngrade,
} from "./quality.js";

describe("quality presets", () => {
  it("expose the required instance caps 100/250/400", () => {
    expect(QUALITY_PRESETS.low.instanceCap).toBe(100);
    expect(QUALITY_PRESETS.med.instanceCap).toBe(250);
    expect(QUALITY_PRESETS.high.instanceCap).toBe(400);
  });

  it("order levels low < med < high", () => {
    expect(QUALITY_LEVELS).toEqual(["low", "med", "high"]);
  });

  it("normalizes unknown values to med", () => {
    expect(normalizeQuality("ultra")).toBe("med");
    expect(normalizeQuality("low")).toBe("low");
  });

  it("downgrades one level at a time and stops at low", () => {
    expect(nextQualityDowngrade("high")).toBe("med");
    expect(nextQualityDowngrade("med")).toBe("low");
    expect(nextQualityDowngrade("low")).toBeNull();
  });

  it("defaults mobile/touch to Low", () => {
    expect(defaultQualityFor({ isTouch: true })).toBe("low");
    expect(defaultQualityFor({ isTouch: false, hardwareConcurrency: 4 })).toBe("low");
    expect(defaultQualityFor({ isTouch: false, hardwareConcurrency: 8 })).toBe("med");
  });
});

describe("auto-downgrade policy", () => {
  it("does not trigger before the window fills", () => {
    const tracker = createFrameTimeTracker({ windowMs: 3000 });
    // 30 slow frames ~= 480ms of window: not enough yet.
    let result = null;
    for (let i = 0; i < 30; i++) result = tracker(40);
    expect(result).toBeNull();
  });

  it("triggers when the average stays above 25ms for 3 seconds", () => {
    const tracker = createFrameTimeTracker({ windowMs: 3000 });
    let result = null;
    for (let i = 0; i < 200; i++) result = tracker(40); // ~3.2s of slow frames
    expect(result).toBe(true);
  });

  it("does not trigger when frames are fast", () => {
    const tracker = createFrameTimeTracker({ windowMs: 3000 });
    let result = null;
    for (let i = 0; i < 400; i++) result = tracker(8);
    expect(result).toBeNull();
  });

  it("averageFrameTime/shouldDowngrade agree with the tracker", () => {
    const slow = Array(40).fill(30);
    const fast = Array(40).fill(10);
    expect(averageFrameTime(slow)).toBe(30);
    expect(shouldDowngrade(slow, 25)).toBe(true);
    expect(shouldDowngrade(fast, 25)).toBe(false);
  });
});
