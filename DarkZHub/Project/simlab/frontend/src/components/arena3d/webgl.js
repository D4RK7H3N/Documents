/** WebGL availability / context-loss detection for the 3D arena. */

function tryCreateContext(canvas) {
  return (
    canvas.getContext("webgl2") ||
    canvas.getContext("webgl") ||
    canvas.getContext("experimental-webgl")
  );
}

/**
 * Returns { supported, reason }.  Creates a throwaway canvas and tries to
 * get a WebGL context; jsdom and locked-down browsers return null.
 */
export function detectWebGL() {
  if (typeof document === "undefined") return { supported: false, reason: "no-dom" };
  try {
    const canvas = document.createElement("canvas");
    const gl = tryCreateContext(canvas);
    if (!gl) return { supported: false, reason: "no-webgl-context" };
    return { supported: true, reason: null };
  } catch (err) {
    return { supported: false, reason: String(err?.message ?? err) };
  }
}

/** True once a real context was lost (driver reset, GPU process crash...). */
export function onContextLost(canvasElement, callback) {
  if (!canvasElement) return () => {};
  const handler = (event) => {
    event.preventDefault();
    callback();
  };
  canvasElement.addEventListener("webglcontextlost", handler);
  return () => canvasElement.removeEventListener("webglcontextlost", handler);
}
