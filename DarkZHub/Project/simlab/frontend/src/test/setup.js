import "@testing-library/jest-dom/vitest";

// jsdom lacks ResizeObserver, which recharts' ResponsiveContainer needs.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserverStub;

// jsdom logs a "Not implemented" error on every getContext call; the
// EvolutionArena handles a missing 2D context, so return null quietly.
HTMLCanvasElement.prototype.getContext = () => null;

// jsdom (as configured here) exposes no window.localStorage; provide a
// minimal in-memory stand-in for view-preference persistence.
if (typeof window !== "undefined" && !window.localStorage) {
  const store = new Map();
  window.localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
    clear: () => store.clear(),
    key: (index) => Array.from(store.keys())[index] ?? null,
    get length() {
      return store.size;
    },
  };
}
