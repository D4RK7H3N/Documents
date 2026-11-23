import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import SweepResult from "./SweepResult.jsx";

const { fetchSweepMock } = vi.hoisted(() => ({ fetchSweepMock: vi.fn() }));
vi.mock("../api.js", () => ({ fetchSweep: fetchSweepMock }));

const axes2d = {
  param_a: "kill",
  param_b: "cost",
  values_a: [0.2, 0.8],
  values_b: [0.0, 0.1, 0.2],
};

function cell(aIdx, bIdx, extra = {}) {
  return {
    a_index: aIdx,
    b_index: bIdx,
    a: axes2d.values_a[aIdx],
    b: axes2d.values_b[bIdx],
    n: 2,
    n_failed: 0,
    n_never_reached: 0,
    final_freq_mean: 0.9 + 0.01 * (aIdx * 3 + bIdx),
    final_freq_std: 0.01,
    gen50_mean: 10 + aIdx * 5 + bIdx,
    gen50_std: 1,
    ...extra,
  };
}

const cells2d = [
  cell(0, 0),
  cell(0, 1),
  cell(0, 2),
  cell(1, 0),
  cell(1, 1, { n_never_reached: 1 }),
  cell(1, 2),
];

const doneSweep2d = {
  id: "s1",
  engine: "insect_evo",
  engine_version: "1.0.0",
  status: "done",
  replicates: 2,
  base_params: { seed: 42, population: 100 },
  created_at: "2026-01-01T00:00:00Z",
  sweep: { kill: [0.2, 0.8], cost: [0.0, 0.1, 0.2] },
  progress: { completed: 12, total: 12 },
  axes: axes2d,
  cells: cells2d,
};

const doneSweep1d = {
  ...doneSweep2d,
  sweep: { kill: [0.2, 0.5, 0.8] },
  axes: { param_a: "kill", param_b: null, values_a: [0.2, 0.5, 0.8], values_b: [] },
  cells: [cell(0, 0), cell(1, 0), cell(2, 0)],
};

function renderResult() {
  return render(
    <MemoryRouter initialEntries={["/sweeps/s1"]}>
      <Routes>
        <Route path="/" element={<div>home</div>} />
        <Route path="/sweeps/:id" element={<SweepResult />} />
      </Routes>
    </MemoryRouter>
  );
}

async function flush() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("SweepResult heatmap (2D)", () => {
  it("renders exactly values_a x values_b cells plus axis headers", async () => {
    fetchSweepMock.mockResolvedValue(doneSweep2d);
    renderResult();
    await flush();

    expect(screen.getAllByTestId("heat-cell")).toHaveLength(6); // 2 x 3
    expect(screen.getAllByTestId("row-header")).toHaveLength(2);
    expect(screen.getAllByTestId("col-header")).toHaveLength(3);
    expect(screen.getByText("Simulation result, not experimental evidence.")).toBeInTheDocument();
  });

  it("metric toggle changes the displayed cell values", async () => {
    fetchSweepMock.mockResolvedValue(doneSweep2d);
    renderResult();
    await flush();

    // Default metric: mean gen to 50% -> cell (0,0) shows 10.0.
    const firstCell = screen.getAllByTestId("heat-cell")[0];
    expect(within(firstCell).getByText("10.0")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("metric-final_freq"));
    // Same cell now shows the final-frequency mean 0.900.
    expect(within(screen.getAllByTestId("heat-cell")[0]).getByText("0.900")).toBeInTheDocument();
    expect(within(screen.getAllByTestId("heat-cell")[0]).queryByText("10.0")).not.toBeInTheDocument();
  });

  it("shows the never-reached marker on cells with n_never_reached > 0", async () => {
    fetchSweepMock.mockResolvedValue(doneSweep2d);
    renderResult();
    await flush();

    const marked = screen.getAllByTestId("heat-cell")[4]; // cell (1,1)
    expect(within(marked).getByTestId("never-marker")).toBeInTheDocument();
    const unmarked = screen.getAllByTestId("heat-cell")[0];
    expect(within(unmarked).queryByTestId("never-marker")).not.toBeInTheDocument();
  });
});

describe("SweepResult line chart (1D)", () => {
  it("renders a line chart with error bars instead of a heatmap", async () => {
    fetchSweepMock.mockResolvedValue(doneSweep1d);
    const { container } = renderResult();
    await flush();

    expect(screen.queryAllByTestId("heat-cell")).toHaveLength(0); // no heatmap
    expect(container.querySelector(".recharts-surface")).not.toBeNull();
    expect(container.querySelector(".recharts-line-curve")).not.toBeNull();
    expect(container.querySelector(".recharts-errorBar")).not.toBeNull();
  });
});
