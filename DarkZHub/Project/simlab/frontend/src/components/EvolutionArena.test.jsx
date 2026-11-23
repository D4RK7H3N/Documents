import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import EvolutionArena from "./EvolutionArena.jsx";

const experiment = {
  id: "exp-1",
  engine: "insect_evo",
  engine_version: "1.1.0",
  status: "done",
  params: {
    population: 10000,
    generations: 200,
    pesticide_kill: 0.8,
    start_freq: 0.01,
    seed: 42,
  },
  result: {
    summary: {
      final_freq: 0.9999,
      generations_run: 3,
      extinct: false,
      gen_to_50pct: 4,
    },
    generations: [
      { gen: 1, freq: 0.0429, size: 2040, resistant_survivors: 100, normal_survivors: 1940 },
      { gen: 2, freq: 0.5, size: 4000, resistant_survivors: 2000, normal_survivors: 2000 },
      { gen: 3, freq: 0.9999, size: 10000, resistant_survivors: 9999, normal_survivors: 1 },
    ],
  },
};

/** Harness owning currentGen like ExperimentResult does. */
function Harness({ exp }) {
  const [currentGen, setCurrentGen] = useState(1);
  return (
    <EvolutionArena
      experiment={exp ?? experiment}
      currentGen={currentGen}
      onCurrentGenChange={setCurrentGen}
    />
  );
}

const rafAvailable = typeof window.requestAnimationFrame === "function";
const cafAvailable = typeof window.cancelAnimationFrame === "function";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("EvolutionArena controls", () => {
  it("renders controls, scrubber, scale label and live readout", () => {
    render(<Harness />);
    expect(screen.getByTestId("play-pause")).toBeInTheDocument();
    expect(screen.getByTestId("step-forward")).toBeInTheDocument();
    expect(screen.getByTestId("step-back")).toBeInTheDocument();
    expect(screen.getByTestId("restart")).toBeInTheDocument();
    expect(screen.getByTestId("loop-toggle")).toBeInTheDocument();
    expect(screen.getByTestId("scrubber")).toBeInTheDocument();
    expect(screen.getByTestId("readout")).toHaveTextContent("Generation 1 / 3");
    expect(screen.getByText(/1 dot = 25 insects/)).toBeInTheDocument();
    expect(
      screen.getByText(/Colors and counts come from the simulation data/)
    ).toBeInTheDocument();
  });

  it("scrubber changes the displayed generation", () => {
    render(<Harness />);
    fireEvent.change(screen.getByTestId("scrubber"), { target: { value: "2" } });
    expect(screen.getByTestId("readout")).toHaveTextContent("Generation 2 / 3");
    fireEvent.change(screen.getByTestId("scrubber"), { target: { value: "3" } });
    expect(screen.getByTestId("readout")).toHaveTextContent("Generation 3 / 3");
  });

  it("step forward/back move one generation at a time", () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("step-forward"));
    expect(screen.getByTestId("readout")).toHaveTextContent("Generation 2 / 3");
    fireEvent.click(screen.getByTestId("step-back"));
    expect(screen.getByTestId("readout")).toHaveTextContent("Generation 1 / 3");
  });

  it("restart returns to generation 1", () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId("step-forward"));
    fireEvent.click(screen.getByTestId("restart"));
    expect(screen.getByTestId("readout")).toHaveTextContent("Generation 1 / 3");
  });

  it("pause stops advancing and cancels the animation frame", () => {
    const cancelSpy = cafAvailable ? vi.spyOn(window, "cancelAnimationFrame") : null;
    render(<Harness />);
    const toggle = screen.getByTestId("play-pause");
    fireEvent.click(toggle); // pause
    expect(toggle).toHaveTextContent("Play");
    if (cancelSpy) expect(cancelSpy).toHaveBeenCalled();

    const rafSpy = rafAvailable ? vi.spyOn(window, "requestAnimationFrame") : null;
    if (rafSpy) rafSpy.mockClear();
    fireEvent.click(toggle); // play again
    expect(toggle).toHaveTextContent("Pause");
    if (rafSpy) expect(rafSpy).toHaveBeenCalled();
  });

  it("pause stops the generation from advancing while time passes", () => {
    vi.useFakeTimers();
    const { unmount } = render(<Harness />);
    const toggle = screen.getByTestId("play-pause");
    fireEvent.click(toggle); // pause
    const before = screen.getByTestId("readout").textContent;
    // Even with passing time, a paused arena never advances.
    vi.advanceTimersByTime(5000);
    expect(screen.getByTestId("readout").textContent).toBe(before);
    unmount();
    vi.useRealTimers();
  });

  it("unmount cancels the animation frame", () => {
    const cancelSpy = cafAvailable ? vi.spyOn(window, "cancelAnimationFrame") : null;
    const { unmount } = render(<Harness />);
    unmount();
    if (cancelSpy) expect(cancelSpy).toHaveBeenCalled();
  });

  it("shows the extinct overlay when paused on an extinct generation", () => {
    const extinctExperiment = {
      ...experiment,
      result: {
        summary: {
          final_freq: 0.0,
          generations_run: 2,
          extinct: true,
          gen_to_50pct: null,
        },
        generations: [
          { gen: 1, freq: 0.0, size: 2, resistant_survivors: 0, normal_survivors: 2 },
          { gen: 2, freq: 0.0, size: 0, resistant_survivors: 0, normal_survivors: 0 },
        ],
      },
    };
    render(<Harness exp={extinctExperiment} />);
    // Start on the extinction generation (gen 2), then pause so the final
    // state is displayed.
    fireEvent.change(screen.getByTestId("scrubber"), { target: { value: "2" } });
    fireEvent.click(screen.getByTestId("play-pause"));
    expect(screen.getByTestId("extinct-overlay")).toHaveTextContent(
      "Population extinct"
    );
  });
});
