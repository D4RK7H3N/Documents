/**
 * 2D/3D switch + species selector + WebGL fallback tests.
 * jsdom has no WebGL: @react-three/fiber's Canvas and the drei helpers are
 * mocked; the real Arena3D component logic (species selection, controls,
 * fallback wiring) runs for real.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ExperimentResult from "./ExperimentResult.jsx";

const { fetchExperimentMock, webglState } = vi.hoisted(() => ({
  fetchExperimentMock: vi.fn(),
  webglState: { supported: true },
}));

vi.mock("../api.js", () => ({ fetchExperiment: fetchExperimentMock }));

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => vi.fn() };
});

vi.mock("../components/arena3d/webgl.js", () => ({
  detectWebGL: () => ({ supported: webglState.supported, reason: webglState.supported ? null : "no-webgl-context" }),
  onContextLost: () => () => {},
}));

vi.mock("@react-three/fiber", () => ({
  Canvas: ({ children, ...props }) => <div data-testid="mock-canvas" {...props}>{children}</div>,
  useFrame: () => {},
  useThree: () => () => {},
}));

vi.mock("@react-three/drei", () => ({
  OrbitControls: () => null,
  Grid: () => null,
  useGLTF: () => ({ scene: null }),
}));

vi.mock("../components/arena3d/Scene.jsx", () => ({ default: () => null }));

const doneExp = {
  id: "exp-1",
  engine: "insect_evo",
  params: { seed: 42, population: 10000, pesticide_kill: 0.8 },
  status: "done",
  engine_version: "1.1.0",
  created_at: "2026-01-01T00:00:00Z",
  finished_at: "2026-01-01T00:00:05Z",
  result: {
    generations: [
      { gen: 1, freq: 0.04, size: 2000, resistant_survivors: 80, normal_survivors: 1920 },
      { gen: 2, freq: 0.99, size: 10000, resistant_survivors: 9900, normal_survivors: 100 },
    ],
    summary: { final_freq: 0.99, generations_run: 2, extinct: false, gen_to_50pct: 2 },
  },
};

function renderResult() {
  return render(
    <MemoryRouter initialEntries={["/experiments/exp-1"]}>
      <Routes>
        <Route path="/" element={<div>home</div>} />
        <Route path="/experiments/:id" element={<ExperimentResult />} />
      </Routes>
    </MemoryRouter>
  );
}

async function renderDone() {
  fetchExperimentMock.mockResolvedValue(doneExp);
  renderResult();
  await act(async () => {});
}

beforeEach(() => {
  window.localStorage?.clear();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("2D/3D view switch", () => {
  it("starts in 2D and renders the 2D canvas arena", async () => {
    await renderDone();
    expect(screen.getByTestId("view-2d")).toBeInTheDocument();
    expect(screen.getByTestId("view-3d")).toBeInTheDocument();
    expect(screen.getByTestId("evolution-canvas")).toBeInTheDocument();
    expect(screen.queryByTestId("arena3d-canvas")).not.toBeInTheDocument();
  });

  it("switches to 3D and back, persisting the preference", async () => {
    await renderDone();

    fireEvent.click(screen.getByTestId("view-3d"));
    expect(await screen.findByTestId("arena3d-canvas", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.queryByTestId("evolution-canvas")).not.toBeInTheDocument();
    expect(window.localStorage.getItem("simlab.arenaView")).toBe("3d");

    fireEvent.click(screen.getByTestId("view-2d"));
    await act(async () => {});
    expect(screen.getByTestId("evolution-canvas")).toBeInTheDocument();
    expect(window.localStorage.getItem("simlab.arenaView")).toBe("2d");
  });

  it("shares currentGen between the 3D view and the controls", async () => {
    await renderDone();
    fireEvent.click(screen.getByTestId("view-3d"));
    await act(async () => {});

    // ArenaControls is shared: stepping forward updates the readout and the
    // chart-synced currentGen state inside the 3D view too.
    fireEvent.click(screen.getByTestId("step-forward"));
    expect(screen.getByTestId("readout")).toHaveTextContent("Generation 2 / 2");
    expect(screen.getByTestId("fixation-note")).toHaveTextContent(
      "Resistance fixed at generation 2"
    );

    fireEvent.click(screen.getByTestId("skip-to-end"));
    expect(screen.getByTestId("readout")).toHaveTextContent("Generation 2 / 2");
  });

  it("species selector persists the chosen species (visualization only)", async () => {
    await renderDone();
    fireEvent.click(screen.getByTestId("view-3d"));
    await act(async () => {});

    fireEvent.click(screen.getByTestId("species-beetle"));
    expect(window.localStorage.getItem("simlab.arena3d.species")).toBe("beetle");
    fireEvent.click(screen.getByTestId("species-fruit_fly"));
    expect(window.localStorage.getItem("simlab.arena3d.species")).toBe("fruit_fly");

    // The species choice never leaks into the experiment params.
    expect(doneExp.params).not.toHaveProperty("species");
  });
});

describe("WebGL unavailability fallback", () => {
  it("falls back to the 2D arena with a friendly note", async () => {
    webglState.supported = false;
    try {
      await renderDone();
      fireEvent.click(screen.getByTestId("view-3d"));
      await act(async () => {});
      // Arena3D detects the missing context on mount and asks the page to
      // switch back; the 2D arena renders with an explanatory note.
      await act(async () => {});
      expect(screen.getByTestId("evolution-canvas")).toBeInTheDocument();
      expect(screen.getByText(/WebGL is not available/i)).toBeInTheDocument();
      expect(window.localStorage.getItem("simlab.arenaView")).toBe("2d");
    } finally {
      webglState.supported = true;
    }
  });
});
