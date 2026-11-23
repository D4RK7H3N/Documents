import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ArenaControls from "./ArenaControls.jsx";
import {
  advancePhaseMachine,
  FAST_THRESHOLD,
  PHASES,
  PHASE_SECONDS,
  TOTAL_SECONDS_AT_1X,
} from "./phaseClock.js";
import {
  dotLayout,
  incomingFreqFor,
  selectColored,
  selectSurvivors,
  survivorDotCounts,
  totalDotsFor,
  generationSeed,
} from "./evolutionLogic.js";

const ARENA_HEIGHT = 300;
const COLOR_RESISTANT = "#a78bfa";
const COLOR_NORMAL = "#7d7590";

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    (window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false)
  );
}

const LEG_PHASES = 8; // discrete leg poses baked into cached sprites

/** Procedural bug path: body ellipse + head + 6 legs + 2 antennae.
 *  Drawn once into cached sprite canvases (one per color x leg pose), so
 *  animating 400 dots is one drawImage per bug, not several path ops. */
function paintBug(ctx, size, legPhase) {
  ctx.lineWidth = 1;

  ctx.beginPath();
  for (const side of [-1, 1]) {
    for (let i = 0; i < 3; i++) {
      const lx = (i - 1) * size * 0.45;
      const wig = Math.sin(legPhase + i * 1.7 + side) * size * 0.2;
      ctx.moveTo(lx, side * size * 0.26);
      ctx.lineTo(lx + wig, side * size * 0.85);
    }
    ctx.moveTo(size * 0.42, side * size * 0.14);
    ctx.lineTo(size * 0.95, side * size * 0.5);
  }
  ctx.stroke();

  ctx.beginPath();
  ctx.ellipse(0, 0, size * 0.55, size * 0.32, 0, 0, Math.PI * 2);
  ctx.moveTo(size * 0.72, 0);
  ctx.arc(size * 0.52, 0, size * 0.2, 0, Math.PI * 2);
  ctx.fill();
}

const spriteCache = new Map(); // "color|size|pose" -> {canvas, bodyX, bodyY}
const SPRITE_SCALE = 2; // render at 2x for crisp devicePixelRatio scaling

function getBugSprite(color, size, pose) {
  const key = `${color}|${size}|${pose}`;
  let sprite = spriteCache.get(key);
  if (sprite) return sprite;
  const w = Math.ceil(size * 2.6);
  const h = Math.ceil(size * 2.2);
  const canvas = document.createElement("canvas");
  canvas.width = w * SPRITE_SCALE;
  canvas.height = h * SPRITE_SCALE;
  const sctx = canvas.getContext("2d");
  const bodyX = w / 2 - size * 0.2; // body center inside the sprite
  const bodyY = h / 2;
  if (sctx) {
    sctx.setTransform(SPRITE_SCALE, 0, 0, SPRITE_SCALE, bodyX * SPRITE_SCALE, bodyY * SPRITE_SCALE);
    sctx.strokeStyle = color;
    sctx.fillStyle = color;
    paintBug(sctx, size, (pose / LEG_PHASES) * Math.PI * 2);
  }
  sprite = { canvas, w, h, bodyX, bodyY };
  spriteCache.set(key, sprite);
  return sprite;
}

/** Cached soft glow halo for surviving resistant dots. */
function getGlowSprite(color) {
  const key = `glow|${color}`;
  let sprite = spriteCache.get(key);
  if (sprite) return sprite;
  const r = 14;
  const canvas = document.createElement("canvas");
  canvas.width = r * 2 * SPRITE_SCALE;
  canvas.height = r * 2 * SPRITE_SCALE;
  const gctx = canvas.getContext("2d");
  if (gctx) {
    gctx.setTransform(SPRITE_SCALE, 0, 0, SPRITE_SCALE, r * SPRITE_SCALE, r * SPRITE_SCALE);
    const grad = gctx.createRadialGradient(0, 0, 0, 0, 0, r);
    grad.addColorStop(0, color);
    grad.addColorStop(1, "rgba(167, 139, 250, 0)");
    gctx.fillStyle = grad;
    gctx.fillRect(-r, -r, r * 2, r * 2);
  }
  sprite = { canvas, w: r * 2, h: r * 2, bodyX: r, bodyY: r };
  spriteCache.set(key, sprite);
  return sprite;
}

function drawBug(ctx, x, y, angle, color, size, legPhase, opts = {}) {
  const { flip = false, glow = 0, alpha = 1, scale = 1 } = opts;
  if (alpha <= 0.01 || scale <= 0.01) return;
  const pose = ((Math.floor(legPhase) % LEG_PHASES) + LEG_PHASES) % LEG_PHASES;
  const sprite = getBugSprite(color, size, pose);
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);
  if (flip) ctx.scale(1, -1); // belly-up
  ctx.scale(scale, scale);
  ctx.globalAlpha = alpha;
  if (glow > 0) {
    const halo = getGlowSprite(color);
    ctx.globalAlpha = alpha * Math.min(1, glow / 8);
    ctx.drawImage(halo.canvas, -halo.bodyX, -halo.bodyY, halo.w, halo.h);
    ctx.globalAlpha = alpha;
  }
  ctx.drawImage(sprite.canvas, -sprite.bodyX, -sprite.bodyY, sprite.w, sprite.h);
  ctx.restore();
}

/** Subtle grid + vignette backdrop. */
function drawBackdrop(ctx, width, height) {
  ctx.fillStyle = "#0d0b12";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(43, 36, 64, 0.45)";
  ctx.lineWidth = 1;
  for (let x = 36; x < width; x += 36) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 36; y < height; y += 36) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  const vignette = ctx.createRadialGradient(
    width / 2, height / 2, height * 0.2,
    width / 2, height / 2, Math.max(width, height) * 0.75
  );
  vignette.addColorStop(0, "rgba(0,0,0,0)");
  vignette.addColorStop(1, "rgba(0,0,0,0.45)");
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, width, height);
}

/** Pesticide cloud: opacity scales with pesticide_kill. */
function drawCloud(ctx, width, height, kill, progress) {
  const alpha = 0.08 + 0.3 * kill;
  for (let i = 0; i < 5; i++) {
    const bx =
      width * (-0.25 + 1.5 * progress) + Math.sin(i * 2.1) * width * 0.12;
    const by =
      height * (0.18 + 0.64 * ((i * 0.37) % 1)) +
      Math.cos(i * 1.3 + progress * 2.5) * height * 0.08;
    const radius = 60 + (i % 3) * 34;
    const gradient = ctx.createRadialGradient(bx, by, 0, bx, by, radius);
    gradient.addColorStop(0, `rgba(140, 152, 126, ${alpha})`);
    gradient.addColorStop(1, "rgba(140, 152, 126, 0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(bx - radius, by - radius, radius * 2, radius * 2);
  }
}

/** Small sparkle for a mutation event. */
function drawSparkle(ctx, x, y, intensity) {
  ctx.save();
  ctx.globalAlpha = Math.max(0, Math.min(1, intensity));
  ctx.strokeStyle = "#e9e2ff";
  ctx.lineWidth = 1.2;
  const r = 4 + 6 * (1 - intensity);
  for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + dx * r, y + dy * r);
    ctx.stroke();
  }
  ctx.restore();
}

const easeOutBack = (t) => 1 + 2.7 * Math.pow(t - 1, 3) + 1.7 * Math.pow(t - 1, 2);

// requestAnimationFrame may be unavailable in non-visual environments.
const scheduleFrame = (cb) =>
  typeof window.requestAnimationFrame === "function"
    ? window.requestAnimationFrame(cb)
    : 0;
const cancelFrame = (id) =>
  typeof window.cancelAnimationFrame === "function"
    ? window.cancelAnimationFrame(id)
    : undefined;

export default function EvolutionArena({
  experiment,
  currentGen,
  onCurrentGenChange,
}) {
  const generations = experiment?.result?.generations ?? [];
  const total = generations.length;
  const params = experiment?.params ?? {};
  const totalDots = useMemo(() => totalDotsFor(params), [params]);
  const extinct = Boolean(experiment?.result?.summary?.extinct);
  const scaleInsects = Math.max(1, Math.round((params.population ?? 0) / totalDots));

  const [playing, setPlaying] = useState(!prefersReducedMotion());
  const [speed, setSpeed] = useState(1);
  const [loop, setLoop] = useState(false);
  const [size, setSize] = useState({ width: 800, height: ARENA_HEIGHT });
  const [fps, setFps] = useState(0);
  const [phaseInfo, setPhaseInfo] = useState({ genIndex: 0, phaseIndex: 0 });

  const wrapperRef = useRef(null);
  const canvasRef = useRef(null);
  const machineRef = useRef({ genIndex: 0, phaseIndex: 0, t: 0 });
  const lastTsRef = useRef(null);
  const fpsFramesRef = useRef(0);
  const fpsWindowRef = useRef(null);
  const rafRef = useRef(null);
  // Backdrop (grid + vignette) cached offscreen; rebuilt only on resize.
  const backdropRef = useRef(null);

  // Latest props for the rAF loop (avoids restarting it on prop changes).
  const propsRef = useRef({});
  propsRef.current = { experiment, currentGen, onCurrentGenChange, speed, loop, total, generations, params, totalDots };

  const fast = speed >= FAST_THRESHOLD;

  const reportGen = useCallback((genIndex) => {
    propsRef.current.onCurrentGenChange?.(genIndex + 1);
  }, []);

  /** Render one frame for the machine's current state. */
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext?.("2d");
    if (!ctx) return; // jsdom / unsupported: nothing to draw

    const { generations: gens, params: prm, totalDots: dots, total: gensTotal } = propsRef.current;
    if (!gens.length) return;
    const m = machineRef.current;
    const genIndex = Math.min(m.genIndex, gensTotal - 1);
    const record = gens[genIndex];
    const width = size.width;
    const height = size.height;

    ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
    if (!backdropRef.current) {
      const off = document.createElement("canvas");
      off.width = Math.max(1, Math.floor(width * (window.devicePixelRatio || 1)));
      off.height = Math.max(1, Math.floor(height * (window.devicePixelRatio || 1)));
      const offCtx = off.getContext("2d");
      if (offCtx) {
        offCtx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
        drawBackdrop(offCtx, width, height);
      }
      backdropRef.current = off;
    }
    ctx.drawImage(backdropRef.current, 0, 0, width, height);

    const seed = generationSeed(prm.seed, genIndex);
    const layout = dotLayout(dots, width, height, seed);
    const incomingFreq = incomingFreqFor(genIndex, gens, prm);
    const incomingPurple = Math.round(dots * incomingFreq);
    const postPurpleCount = Math.round(dots * (record?.freq ?? 0));
    const incomingColored = selectColored(incomingPurple, dots, seed * 2 + 1);
    const postColored = selectColored(postPurpleCount, dots, seed * 2 + 2);
    const survCounts = survivorDotCounts(record, incomingFreq, prm, dots);
    const survivorSet = selectSurvivors(dots, survCounts.total, seed * 3 + 3);

    const phase = PHASES[m.phaseIndex];
    const dur = fast
      ? TOTAL_SECONDS_AT_1X / (propsRef.current.speed || 1)
      : PHASE_SECONDS[phase];
    const p01 = Math.max(0, Math.min(1, m.t / dur));
    const legPhase = performance.now() / 90;
    const size0 = (record?.size ?? 0) === 0;

    if (fast) {
      // High speeds: skip sub-animations, crossfade incoming -> post colors.
      const p = p01;
      for (let i = 0; i < dots; i++) {
        const dot = layout[i];
        const color = incomingColored.has(i) ? COLOR_RESISTANT : COLOR_NORMAL;
        const postColor = postColored.has(i) ? COLOR_RESISTANT : COLOR_NORMAL;
        const wx = dot.x + Math.sin(legPhase * 0.12 + dot.phase) * dot.wobble * 0.4;
        const wy = dot.y + Math.cos(legPhase * 0.1 + dot.phase) * dot.wobble * 0.4;
        drawBug(ctx, wx, wy, dot.angle, color, 7, legPhase + i, {
          alpha: 1 - p,
          scale: survCounts.total === 0 && p > 0.5 ? 1 - p : 1,
        });
        drawBug(ctx, wx, wy, dot.angle, postColor, 7, legPhase + i, {
          alpha: p,
          scale: survCounts.total === 0 && p > 0.5 ? p : 1,
        });
      }
    } else if (phase === "spray") {
      for (let i = 0; i < dots; i++) {
        const dot = layout[i];
        const wx = dot.x + Math.sin(legPhase * 0.12 + dot.phase) * dot.wobble * 0.4;
        const wy = dot.y + Math.cos(legPhase * 0.1 + dot.phase) * dot.wobble * 0.4;
        drawBug(ctx, wx, wy, dot.angle, incomingColored.has(i) ? COLOR_RESISTANT : COLOR_NORMAL, 7, legPhase + i);
      }
      drawCloud(ctx, width, height, Number(prm.pesticide_kill ?? 0), p01);
    } else if (phase === "selection") {
      const p = p01;
      for (let i = 0; i < dots; i++) {
        const dot = layout[i];
        const wx = dot.x + Math.sin(legPhase * 0.12 + dot.phase) * dot.wobble * 0.4;
        const wy = dot.y + Math.cos(legPhase * 0.1 + dot.phase) * dot.wobble * 0.4;
        const survives = survivorSet.has(i);
        const color = incomingColored.has(i) ? COLOR_RESISTANT : COLOR_NORMAL;
        if (survives) {
          drawBug(ctx, wx, wy, dot.angle, color, 7, legPhase + i, {
            glow: incomingColored.has(i) ? 4 + 4 * Math.sin(p * Math.PI) : 0,
          });
        } else {
          // Dies: flips belly-up, fades, and drifts slightly downward.
          drawBug(ctx, wx, wy + p * 4, dot.angle, color, 7, legPhase + i, {
            flip: true,
            alpha: 1 - p,
            scale: 1 - 0.15 * p,
          });
        }
      }
      drawCloud(ctx, width, height, Number(prm.pesticide_kill ?? 0), 0.9);
    } else {
      // reproduction: survivors stay, offspring pop in with post colors.
      for (let i = 0; i < dots; i++) {
        const dot = layout[i];
        const wx = dot.x + Math.sin(legPhase * 0.12 + dot.phase) * dot.wobble * 0.4;
        const wy = dot.y + Math.cos(legPhase * 0.1 + dot.phase) * dot.wobble * 0.4;
        if (survivorSet.has(i)) {
          drawBug(ctx, wx, wy, dot.angle, incomingColored.has(i) ? COLOR_RESISTANT : COLOR_NORMAL, 7, legPhase + i);
        } else if (!size0) {
          const delay = ((i * 13) % 17) / 17 * 0.55;
          const grow = Math.max(0, Math.min(1, (p01 - delay) / 0.45));
          const isPurple = postColored.has(i);
          const mutated = isPurple && !incomingColored.has(i);
          drawBug(ctx, wx, wy, dot.angle, isPurple ? COLOR_RESISTANT : COLOR_NORMAL, 7, legPhase + i, {
            scale: easeOutBack(grow),
          });
          if (mutated && grow > 0.2 && grow < 0.95) {
            drawSparkle(ctx, wx, wy - 10, 1 - grow);
          }
        }
      }
    }
  }, [fast, size.width, size.height]);

  /** Advance the phase machine by `dt` real seconds. */
  const advance = useCallback(
    (dt) => {
      const m = machineRef.current;
      const props = propsRef.current;
      const { genChanged, ended } = advancePhaseMachine(m, dt, {
        speed: props.speed,
        total: props.total,
        loop: props.loop,
      });
      if (ended) {
        playingRef.current = false;
        setPlaying(false);
      }
      if (genChanged || ended) {
        setPhaseInfo({ genIndex: m.genIndex, phaseIndex: m.phaseIndex });
        reportGen(m.genIndex);
      }
    },
    [reportGen]
  );

  const playingRef = useRef(playing);
  playingRef.current = playing;

  const loopFn = useCallback(
    (ts) => {
      if (lastTsRef.current == null) lastTsRef.current = ts;
      const dt = Math.min(0.1, (ts - lastTsRef.current) / 1000);
      lastTsRef.current = ts;

      advance(dt);
      draw();

      // fps meter: report twice per second.
      fpsFramesRef.current += 1;
      if (fpsWindowRef.current == null) fpsWindowRef.current = ts;
      if (ts - fpsWindowRef.current >= 500) {
        setFps(Math.round((fpsFramesRef.current * 1000) / (ts - fpsWindowRef.current)));
        fpsFramesRef.current = 0;
        fpsWindowRef.current = ts;
      }

      if (playingRef.current) {
        rafRef.current = scheduleFrame(loopFn);
      }
    },
    [advance, draw]
  );

  // Run the rAF loop only while playing; cancel on pause/hide/unmount.
  useEffect(() => {
    if (!playing) return undefined;
    lastTsRef.current = null;
    rafRef.current = scheduleFrame(loopFn);
    const onVisibility = () => {
      if (document.hidden) {
        cancelFrame(rafRef.current);
      } else if (playingRef.current) {
        rafRef.current = scheduleFrame(loopFn);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelFrame(rafRef.current);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [playing, loopFn]);

  // Sync external generation changes (scrubber, chart clicks). Declared
  // BEFORE the static-draw effect so a scrub resets the machine first and
  // the same commit's draw renders the NEW generation, not the old one.
  useEffect(() => {
    const m = machineRef.current;
    if (currentGen - 1 !== m.genIndex) {
      m.genIndex = Math.max(0, Math.min(total - 1, currentGen - 1));
      m.phaseIndex = 0;
      m.t = 0;
      setPhaseInfo({ genIndex: m.genIndex, phaseIndex: 0 });
    }
  }, [currentGen, total]);

  // Static render whenever paused / scrubbed / resized.
  useEffect(() => {
    if (!playing) draw();
  }, [playing, currentGen, draw]);

  // Responsive canvas with devicePixelRatio handling.
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper || typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver((entries) => {
      const width = Math.floor(entries[0].contentRect.width);
      if (width > 0) setSize((prev) => ({ ...prev, width }));
    });
    observer.observe(wrapper);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(size.width * dpr);
    canvas.height = Math.floor(size.height * dpr);
    backdropRef.current = null; // rebuild the cached backdrop
    // Always repaint after resetting the backing store: while playing the
    // rAF loop covers it, but when paused this is the only chance before
    // the static-draw effect would be skipped (playing just toggled).
    draw();
  }, [size, draw]);

  const step = (delta) => {
    const next = Math.max(1, Math.min(total, currentGen + delta));
    if (next !== currentGen) onCurrentGenChange?.(next);
  };

  const restart = () => {
    onCurrentGenChange?.(1);
  };

  if (total === 0) return null;

  const record = generations[Math.min(currentGen, total) - 1] ?? generations[total - 1];
  const showExtinctOverlay =
    extinct &&
    record?.size === 0 &&
    (!playing || phaseInfo.phaseIndex >= 1 || fast);

  return (
    <section className="bg-panel border border-edge rounded-lg p-6 mb-6">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-display text-xl">Live evolution view</h2>
        <span className="text-xs text-ash">1 dot = {scaleInsects} insects</span>
      </div>

      <div ref={wrapperRef} className="relative border border-edge rounded overflow-hidden">
        <canvas
          ref={canvasRef}
          data-testid="evolution-canvas"
          style={{ width: "100%", height: ARENA_HEIGHT, display: "block" }}
        />
        {showExtinctOverlay && (
          <div
            data-testid="extinct-overlay"
            className="absolute inset-0 flex items-center justify-center bg-void/60"
          >
            <span className="font-display text-2xl text-red-400">Population extinct</span>
          </div>
        )}
      </div>

      <ArenaControls
        generations={generations}
        currentGen={currentGen}
        total={total}
        playing={playing}
        speed={speed}
        loop={loop}
        fps={fps}
        onPlayPause={() => setPlaying((p) => !p)}
        onStep={step}
        onRestart={restart}
        onLoopToggle={() => setLoop((l) => !l)}
        onSpeed={setSpeed}
        onScrub={(gen) => onCurrentGenChange?.(gen)}
        onSkipToEnd={() => onCurrentGenChange?.(total)}
      />

      <p className="text-[11px] text-ash mt-3">
        Each dot represents a group of insects. Colors and counts come from the
        simulation data; individual movement is illustrative.
      </p>
    </section>
  );
}
