import { describe, expect, it } from "vitest";
import { advancePhaseMachine, TOTAL_SECONDS_AT_1X } from "./phaseClock.js";

describe("advancePhaseMachine", () => {
  it("terminates and parks after the last generation", () => {
    const m = { genIndex: 0, phaseIndex: 0, t: 0 };
    let ended = false;
    let calls = 0;
    // 60 simulated seconds at 1x on a 2-generation experiment.
    for (let i = 0; i < 3750; i++) {
      const r = advancePhaseMachine(m, 0.016, { speed: 1, total: 2, loop: false });
      calls += 1;
      if (r.ended) {
        ended = true;
        break;
      }
    }
    expect(ended).toBe(true);
    expect(calls).toBeLessThan(3750);
    expect(m.genIndex).toBe(1);
    expect(m.phaseIndex).toBe(2);
  });
});
