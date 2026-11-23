import { fixationGeneration } from "./evolutionLogic.js";

const SPEEDS = [0.5, 1, 2, 5, 20];

/**
 * Playback controls + live readout shared by the 2D and 3D arenas so both
 * views behave identically and own no duplicated logic. All state
 * (currentGen, playing, speed, loop) lives in the parent; this component
 * is purely presentational.
 */
export default function ArenaControls({
  generations,
  currentGen,
  total,
  playing,
  speed,
  loop,
  fps = null,
  reducedMotion = false,
  onPlayPause,
  onStep,
  onRestart,
  onLoopToggle,
  onSpeed,
  onScrub,
  onSkipToEnd,
}) {
  const record = generations[Math.min(currentGen, total) - 1] ?? generations[total - 1];
  const freq = record?.freq ?? 0;
  const fixationGen = fixationGeneration(generations);
  const showFixation = fixationGen != null && currentGen >= fixationGen;

  const btn = (active) =>
    `border rounded px-3 py-1.5 text-xs transition-colors ${
      active
        ? "border-lilac bg-lilac/10 text-lilac"
        : "border-edge text-ash hover:border-lilac/50 hover:text-lilac"
    }`;

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 mt-3">
        <button data-testid="play-pause" onClick={onPlayPause} className={btn(false)}>
          {playing ? "Pause" : "Play"}
        </button>
        <button data-testid="step-back" onClick={() => onStep(-1)} className={btn(false)} aria-label="Step back">
          ◀| Step back
        </button>
        <button data-testid="step-forward" onClick={() => onStep(1)} className={btn(false)} aria-label="Step forward">
          Step forward |▶
        </button>
        <button data-testid="restart" onClick={onRestart} className={btn(false)}>
          Restart
        </button>
        <button data-testid="skip-to-end" onClick={onSkipToEnd} className={btn(false)}>
          Skip to end
        </button>
        <button data-testid="loop-toggle" onClick={onLoopToggle} className={btn(loop)}>
          Loop: {loop ? "on" : "off"}
        </button>
        <div className="flex gap-1 ml-auto">
          {SPEEDS.map((s) => (
            <button
              key={s}
              data-testid={`speed-${s}`}
              onClick={() => onSpeed(s)}
              className={btn(speed === s)}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3">
        <input
          data-testid="scrubber"
          type="range"
          min={1}
          max={total}
          value={Math.min(currentGen, total)}
          onChange={(e) => onScrub(Number(e.target.value))}
          className="w-full"
        />
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-ash mt-1">
          <span data-testid="readout">
            Generation {currentGen} / {total}
          </span>
          <span>
            resistant {(100 * freq).toFixed(1)}% · survivors {record?.size ?? 0}
          </span>
          {fps != null && <span data-testid="fps">{fps} fps</span>}
          <div className="flex items-center gap-2 flex-1 min-w-40">
            <div className="h-1.5 bg-void border border-edge rounded flex-1 overflow-hidden">
              <div className="h-full bg-lilac transition-all" style={{ width: `${100 * freq}%` }} />
            </div>
          </div>
        </div>
      </div>

      {showFixation && (
        <p
          data-testid="fixation-note"
          className="text-xs text-lilac mt-2 border border-lilac/30 bg-lilac/5 rounded px-3 py-1.5 inline-block"
        >
          Resistance fixed at generation {fixationGen}
        </p>
      )}
      {reducedMotion && (
        <p className="text-[11px] text-ash mt-2">Reduced motion: playback starts paused; use the step controls.</p>
      )}
    </>
  );
}
