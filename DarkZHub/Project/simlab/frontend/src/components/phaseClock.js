/**
 * Generation phase timing shared by the 2D canvas arena and the 3D view.
 * One generation = spray + selection + reproduction, ~2.5 s at 1x speed.
 * Speeds >= FAST_THRESHOLD skip the sub-animations and crossfade.
 */
export const PHASES = ["spray", "selection", "reproduction"];
export const PHASE_SECONDS = { spray: 0.8, selection: 0.9, reproduction: 0.8 };
export const TOTAL_SECONDS_AT_1X = 2.5;
export const FAST_THRESHOLD = 5;

/** Phase + normalized progress for a generation-local time at a speed. */
export function phaseAt(genTime, speed) {
  const fast = speed >= FAST_THRESHOLD;
  if (fast) {
    return {
      fast,
      phase: "spray",
      phaseIndex: 0,
      p01: Math.min(1, genTime / (TOTAL_SECONDS_AT_1X / speed)),
    };
  }
  let remaining = genTime;
  for (let i = 0; i < PHASES.length; i++) {
    const dur = PHASE_SECONDS[PHASES[i]];
    if (remaining < dur) {
      return { fast, phase: PHASES[i], phaseIndex: i, p01: remaining / dur };
    }
    remaining -= dur;
  }
  return { fast, phase: "reproduction", phaseIndex: 2, p01: 1 };
}

export function phaseDuration(phaseIndex, speed) {
  const fast = speed >= FAST_THRESHOLD;
  return fast
    ? TOTAL_SECONDS_AT_1X / speed
    : PHASE_SECONDS[PHASES[phaseIndex]];
}

/**
 * Advance a phase machine ({genIndex, phaseIndex, t}) by dt real seconds.
 * Mutates the machine and returns { genChanged, ended }.  `ended` is true
 * once when playback reaches the last generation without loop enabled;
 * the caller decides to stop.  Shared by the 2D and 3D arenas.
 */
export function advancePhaseMachine(machine, dt, { speed, total, loop }) {
  machine.t += dt * speed;
  let genChanged = false;
  let ended = false;
  let guard = 0;
  while (machine.t >= phaseDuration(machine.phaseIndex, speed) && guard < 12) {
    guard += 1;
    machine.t -= phaseDuration(machine.phaseIndex, speed);
    machine.phaseIndex += 1;
    if (machine.phaseIndex >= PHASES.length) {
      machine.phaseIndex = 0;
      machine.genIndex += 1;
      if (machine.genIndex >= total) {
        if (loop) {
          machine.genIndex = 0;
        } else {
          // Park on the final generation; the caller stops playback.
          machine.genIndex = total - 1;
          machine.phaseIndex = PHASES.length - 1;
          machine.t = phaseDuration(machine.phaseIndex, speed);
          ended = true;
          break;
        }
      }
      genChanged = true;
    }
  }
  return { genChanged, ended };
}
