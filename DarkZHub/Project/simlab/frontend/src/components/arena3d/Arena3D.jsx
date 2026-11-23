/**
 * Arena3D: the 3D evolution view (lazy-loaded so the main bundle does not
 * grow for users who stay in 2D).
 *
 * Same shared state as the 2D arena: currentGen comes from the parent and
 * is reported back through onCurrentGenChange, so the chart, the 2D arena
 * and this view always agree.  Generation data (colors, survivors) uses
 * the SHARED pure functions in evolutionLogic.js.
 */
import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import ArenaControls from "../ArenaControls.jsx";
import {
  generationSeed,
  incomingFreqFor,
  selectColored,
  selectSurvivors,
  survivorDotCounts,
  totalDotsFor,
} from "../evolutionLogic.js";
import { resolveSpecies, SPECIES_LIST } from "../../species/registry.js";
import { buildProceduralParts } from "../../species/procedural.js";
import ModelLoadErrorBoundary from "./ModelLoadErrorBoundary.jsx";
import Scene from "./Scene.jsx";
import {
  QUALITY_LEVELS,
  QUALITY_PRESETS,
  createFrameTimeTracker,
  defaultQualityFor,
  normalizeQuality,
} from "./quality.js";
import { detectWebGL, onContextLost } from "./webgl.js";

const GltfSpecies = lazy(() => import("./GltfSpecies.jsx"));

const PREF_SPECIES = "simlab.arena3d.species";
const PREF_QUALITY = "simlab.arena3d.quality";

function readPref(key, fallback) {
  try {
    return window.localStorage?.getItem?.(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function writePref(key, value) {
  try {
    window.localStorage?.setItem?.(key, value);
  } catch {
    /* private mode: preference just won't persist */
  }
}

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    (window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false)
  );
}

/** Full-frame sampler inside the Canvas: fps readout + downgrade trigger. */
function FrameTimer({ onFps, onOverBudget }) {
  const lastRef = useRef(null);
  const samplesRef = useRef([]);
  const trackerRef = useRef(createFrameTimeTracker());
  const cbRef = useRef({});
  cbRef.current = { onFps, onOverBudget };

  useEffect(() => {
    const interval = setInterval(() => {
      const s = samplesRef.current;
      if (!s.length) return;
      const avg = s.reduce((a, b) => a + b, 0) / s.length;
      cbRef.current.onFps?.(Math.min(120, Math.round(1000 / Math.max(1, avg))));
      s.length = 0;
    }, 500);
    return () => clearInterval(interval);
  }, []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (lastRef.current != null) {
      const dt = (t - lastRef.current) * 1000;
      if (dt > 0 && dt < 250) {
        samplesRef.current.push(dt);
        if (samplesRef.current.length > 600) samplesRef.current.shift();
        if (trackerRef.current(dt)) cbRef.current.onOverBudget?.();
      }
    }
    lastRef.current = t;
  });
  return null;
}

/** When frameloop is "demand", still render once per scrub/prop change. */
function InvalidateOnChange({ deps }) {
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => {
    invalidate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return null;
}

export default function Arena3D({
  experiment,
  currentGen,
  onCurrentGenChange,
  onFallbackTo2D,
}) {
  const generations = experiment?.result?.generations ?? [];
  const total = generations.length;
  const params = experiment?.params ?? {};
  const extinct = Boolean(experiment?.result?.summary?.extinct);
  const scaleInsects = params.population
    ? Math.max(1, Math.round(params.population / 400))
    : 400;

  const [speciesId, setSpeciesId] = useState(() => readPref(PREF_SPECIES, "mosquito"));
  const [quality, setQuality] = useState(() =>
    normalizeQuality(
      readPref(
        PREF_QUALITY,
        defaultQualityFor({
          isTouch:
            typeof window !== "undefined" &&
            window.matchMedia?.("(pointer: coarse)")?.matches,
          hardwareConcurrency:
            typeof navigator !== "undefined" ? navigator.hardwareConcurrency : undefined,
        })
      )
    )
  );
  const [autoRotate, setAutoRotate] = useState(false);
  const [resetSignal, setResetSignal] = useState(0);
  const [playing, setPlaying] = useState(!prefersReducedMotion());
  const [speed, setSpeed] = useState(1);
  const [loop, setLoop] = useState(false);
  const [fps, setFps] = useState(null);
  const [downgraded, setDowngraded] = useState(null);
  const [hidden, setHidden] = useState(false);
  const [onscreen, setOnscreen] = useState(true);
  const webgl = useMemo(() => detectWebGL(), []);

  const machineRef = useRef({ genIndex: 0, phaseIndex: 0, t: 0, genTime: 0 });
  const wrapperRef = useRef(null);

  const species = useMemo(() => resolveSpecies(speciesId), [speciesId]);
  const preset = QUALITY_PRESETS[quality];

  // Procedural part geometries, disposed when they are replaced/unmounted.
  const parts = useMemo(() => {
    if (species.modelUrl) return null; // glb path handled by GltfSpecies
    if (species.bodyBuilder) return species.bodyBuilder().parts;
    return buildProceduralParts(species.id);
  }, [species]);
  useEffect(
    () => () => {
      for (const p of parts ?? []) p.geometry?.dispose();
    },
    [parts]
  );
  const cappedSpecies = useMemo(
    () => ({ ...species, instanceCap: preset.instanceCap }),
    [species, preset]
  );

  const totalDots = useMemo(
    () => Math.min(totalDotsFor(params), preset.instanceCap),
    [params, preset]
  );

  // Shared per-generation state (same functions + seeds as the 2D arena).
  const generationState = useMemo(() => {
    const record = generations[Math.min(currentGen, total) - 1];
    const incomingFreq = incomingFreqFor(currentGen - 1, generations, params);
    const incomingPurple = Math.round(totalDots * incomingFreq);
    const postPurple = Math.round(totalDots * (record?.freq ?? 0));
    const s = generationSeed(params.seed, currentGen - 1);
    return {
      incomingColored: selectColored(incomingPurple, totalDots, s * 2 + 1),
      survivorSet: selectSurvivors(
        totalDots,
        survivorDotCounts(record, incomingFreq, params, totalDots).total,
        s * 3 + 3
      ),
      survCounts: survivorDotCounts(record, incomingFreq, params, totalDots),
      postColored: selectColored(postPurple, totalDots, s * 2 + 2),
      record,
    };
  }, [generations, params, currentGen, total, totalDots]);

  // Scrub / external sync: reset the machine (history-independent states).
  useEffect(() => {
    const m = machineRef.current;
    if (currentGen - 1 !== m.genIndex) {
      m.genIndex = Math.max(0, Math.min(total - 1, currentGen - 1));
      m.phaseIndex = 0;
      m.t = 0;
      m.genTime = 0;
    }
  }, [currentGen, total]);

  // Pause rendering when the tab is hidden or the canvas is offscreen.
  useEffect(() => {
    const onVis = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", onVis);
    let observer = null;
    if (typeof IntersectionObserver !== "undefined" && wrapperRef.current) {
      observer = new IntersectionObserver(
        (entries) => setOnscreen(entries[0]?.isIntersecting ?? true),
        { threshold: 0.02 }
      );
      observer.observe(wrapperRef.current);
    }
    return () => {
      document.removeEventListener("visibilitychange", onVis);
      observer?.disconnect();
    };
  }, []);

  // WebGL unavailable: tell the parent to switch back to 2D.
  useEffect(() => {
    if (!webgl.supported) onFallbackTo2D?.(webgl.reason);
  }, [webgl.supported]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    writePref(PREF_SPECIES, speciesId);
  }, [speciesId]);
  useEffect(() => {
    writePref(PREF_QUALITY, quality);
  }, [quality]);

  const frameloop = playing && !hidden && onscreen ? "always" : "demand";

  if (total === 0) return null;

  const record = generationState.record;
  const showExtinctOverlay = extinct && record?.size === 0 && !playing;

  const sceneProps = {
    species: cappedSpecies,
    seed: params.seed,
    totalDots,
    generationState,
    speed,
    loop,
    total,
    paused: !playing,
    machineRef,
    kill: Number(params.pesticide_kill ?? 0),
    particleCount: preset.particleCount,
    autoRotate,
    resetSignal,
    onGenChange: (g) => onCurrentGenChange?.(g + 1),
    onEnded: () => setPlaying(false),
  };
  const sceneWithParts = (partsArg) => <Scene {...sceneProps} parts={partsArg ?? []} />;

  const btn = (active) =>
    `border rounded px-2.5 py-1 text-xs transition-colors ${
      active
        ? "border-lilac bg-lilac/10 text-lilac"
        : "border-edge text-ash hover:border-lilac/50 hover:text-lilac"
    }`;

  return (
    <section className="bg-panel border border-edge rounded-lg p-6 mb-6">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <h2 className="font-display text-xl mr-auto">3D evolution view</h2>
        <span className="text-xs text-ash">1 model = {scaleInsects} insects</span>
      </div>

      {/* Species + view options (visualization only, never sent to the engine) */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="text-[11px] uppercase tracking-wider text-ash">Species</span>
        {SPECIES_LIST.map((s) => (
          <button
            key={s.id}
            data-testid={`species-${s.id}`}
            onClick={() => setSpeciesId(s.id)}
            className={btn(speciesId === s.id)}
          >
            {s.name}
          </button>
        ))}
        <span className="text-[11px] uppercase tracking-wider text-ash ml-2">Quality</span>
        {QUALITY_LEVELS.map((q) => (
          <button
            key={q}
            data-testid={`quality-${q}`}
            onClick={() => setQuality(q)}
            className={btn(quality === q)}
          >
            {q}
          </button>
        ))}
        <button
          data-testid="auto-rotate"
          onClick={() => setAutoRotate((v) => !v)}
          className={btn(autoRotate) + " ml-2"}
        >
          Auto-rotate: {autoRotate ? "on" : "off"}
        </button>
        <button
          data-testid="reset-camera"
          onClick={() => setResetSignal((n) => n + 1)}
          className={btn(false)}
        >
          Reset camera
        </button>
      </div>

      <div ref={wrapperRef} className="relative border border-edge rounded overflow-hidden">
        <div style={{ height: 420, backgroundColor: "#0a0810" }}>
          <Canvas
            data-testid="arena3d-canvas"
            frameloop={frameloop}
            dpr={[0.75, preset.dprMax]}
            antialias={preset.antialias}
            camera={{ position: [11, 8, 13], fov: 45 }}
            onCreated={({ gl }) => {
              // Verification hooks: renderer.info + scene access for probes.
              window.__r3fInfo = () => gl.info.memory;
              window.__r3fRender = () => gl.info.render;
              window.__r3fScene = gl.scene;
              onContextLost(gl.domElement, () => onFallbackTo2D?.("webgl-context-lost"));
            }}
          >
            <FrameTimer
              onFps={setFps}
              onOverBudget={() => {
                const lower = { low: null, med: "low", high: "med" }[quality];
                if (lower) {
                  setQuality(lower);
                  setDowngraded(lower);
                }
              }}
            />
            <InvalidateOnChange
              deps={[currentGen, totalDots, speciesId, quality, frameloop]}
            />
            {species.modelUrl ? (
              <ModelLoadErrorBoundary fallback={sceneWithParts(parts)}>
                <Suspense fallback={null}>
                  <GltfSpecies
                    url={species.modelUrl}
                    sceneProps={sceneProps}
                    fallbackParts={parts}
                  />
                </Suspense>
              </ModelLoadErrorBoundary>
            ) : (
              sceneWithParts(parts)
            )}
          </Canvas>
        </div>
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
        onStep={(delta) => {
          const next = Math.max(1, Math.min(total, currentGen + delta));
          if (next !== currentGen) onCurrentGenChange?.(next);
        }}
        onRestart={() => onCurrentGenChange?.(1)}
        onLoopToggle={() => setLoop((l) => !l)}
        onSpeed={setSpeed}
        onScrub={(gen) => onCurrentGenChange?.(gen)}
        onSkipToEnd={() => onCurrentGenChange?.(total)}
      />

      {downgraded && (
        <p className="text-[11px] text-amber-400 mt-2">
          Frame time over budget: quality lowered to “{downgraded}”.
        </p>
      )}

      <p className="text-[11px] text-ash mt-3">
        Each model represents a group of insects. Counts and colors come from
        the simulation data; individual movement is illustrative.
      </p>
    </section>
  );
}
