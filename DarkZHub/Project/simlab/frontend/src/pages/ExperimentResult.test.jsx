import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ExperimentResult from "./ExperimentResult.jsx";

// Mock the API layer so polling can be scripted per test.
const { fetchExperimentMock } = vi.hoisted(() => ({ fetchExperimentMock: vi.fn() }));
vi.mock("../api.js", () => ({ fetchExperiment: fetchExperimentMock }));

// Capture navigate() calls (run-again buttons) without real routing.
const { navigateMock } = vi.hoisted(() => ({ navigateMock: vi.fn() }));
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => navigateMock };
});

const base = {
  id: "exp-1",
  engine: "insect_evo",
  params: { seed: 42, population: 100 },
  status: "pending",
  result: null,
  error: "",
  engine_version: "",
  created_at: "2026-01-01T00:00:00Z",
  finished_at: null,
};

const pendingExp = { ...base };
const runningExp = { ...base, status: "running" };
const failedExp = { ...base, status: "failed", error: "boom: engine exploded" };
const doneExp = {
  ...base,
  status: "done",
  engine_version: "1.0.0",
  finished_at: "2026-01-01T00:00:05Z",
  result: {
    generations: [
      { gen: 1, freq: 0.4, size: 100 },
      { gen: 2, freq: 0.6, size: 100 },
    ],
    summary: { final_freq: 0.6, generations_run: 2, extinct: false, gen_to_50pct: null },
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

/** Advance fake timers inside act() so state updates settle. */
async function flush(ms = 1) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("ExperimentResult status rendering", () => {
  it("renders pending and keeps polling every 1.5s", async () => {
    fetchExperimentMock.mockResolvedValue(pendingExp);
    renderResult();
    await flush();

    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText(/polling every 1.5s/i)).toBeInTheDocument();
    expect(fetchExperimentMock).toHaveBeenCalledTimes(1);

    await flush(1500);
    expect(fetchExperimentMock).toHaveBeenCalledTimes(2);
  });

  it("renders running state", async () => {
    fetchExperimentMock.mockResolvedValue(runningExp);
    renderResult();
    await flush();

    expect(screen.getByText("running")).toBeInTheDocument();
    expect(screen.getByText(/Simulation running/i)).toBeInTheDocument();
  });

  it("renders done: chart section, summary, 'never' for null gen_to_50pct, run-again button", async () => {
    fetchExperimentMock.mockResolvedValue(doneExp);
    renderResult();
    await flush();

    expect(screen.getByText("done")).toBeInTheDocument();
    expect(screen.getByText("Simulation result, not experimental evidence.")).toBeInTheDocument();
    expect(screen.getByText("Trajectory")).toBeInTheDocument();
    expect(screen.getByText("0.6000")).toBeInTheDocument();
    expect(screen.getByText("never")).toBeInTheDocument(); // gen_to_50pct null
    expect(screen.getByText("No")).toBeInTheDocument(); // extinct false
    expect(
      screen.getByRole("button", { name: /run again with these params/i })
    ).toBeInTheDocument();
  });

  it("renders failed: error text and 'Run again with same params' navigating home with state", async () => {
    fetchExperimentMock.mockResolvedValue(failedExp);
    renderResult();
    await flush();

    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(screen.getByText(/Simulation failed: boom: engine exploded/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /run again with same params/i }));
    expect(navigateMock).toHaveBeenCalledWith("/", {
      state: { engine: "insect_evo", params: failedExp.params },
    });
  });

  it("renders 'Experiment not found.' on 404", async () => {
    const err = new Error("request failed");
    err.response = { status: 404 };
    fetchExperimentMock.mockRejectedValue(err);
    renderResult();
    await flush();

    expect(screen.getByText(/Experiment not found./)).toBeInTheDocument();
  });
});

describe("ExperimentResult polling lifecycle", () => {
  it("stops polling once status is done", async () => {
    fetchExperimentMock
      .mockResolvedValueOnce(pendingExp)
      .mockResolvedValue(doneExp);
    renderResult();
    await flush(); // initial fetch -> pending
    await flush(1500); // second fetch -> done

    expect(screen.getByText("done")).toBeInTheDocument();
    await flush(10000);
    expect(fetchExperimentMock).toHaveBeenCalledTimes(2); // no further polls
  });

  it("stops polling once status is failed", async () => {
    fetchExperimentMock
      .mockResolvedValueOnce(pendingExp)
      .mockResolvedValue(failedExp);
    renderResult();
    await flush();
    await flush(1500);

    expect(screen.getByText("failed")).toBeInTheDocument();
    await flush(10000);
    expect(fetchExperimentMock).toHaveBeenCalledTimes(2);
  });

  it("stops polling on unmount", async () => {
    fetchExperimentMock.mockResolvedValue(pendingExp);
    const { unmount } = renderResult();
    await flush();

    unmount();
    await flush(10000);
    expect(fetchExperimentMock).toHaveBeenCalledTimes(1);
  });
});
