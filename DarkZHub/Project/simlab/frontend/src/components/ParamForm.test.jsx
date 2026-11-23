import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import ParamForm, { validateParams } from "./ParamForm.jsx";

const schema = {
  population: { type: "integer", default: 10000, min: 1, max: 10000000 },
  pesticide_kill: { type: "number", default: 0.8, min: 0, max: 1 },
  seed: { type: "integer", default: 42, min: 0 },
};

const defaults = { population: 10000, pesticide_kill: 0.8, seed: 42 };

/** Render ParamForm with live state so validation reacts to edits. */
function renderControlledForm() {
  const onSubmit = vi.fn();
  function Harness() {
    const [params, setParams] = useState(defaults);
    return (
      <ParamForm
        schema={schema}
        params={params}
        onChange={(name, value) => setParams((prev) => ({ ...prev, [name]: value }))}
        onSubmit={onSubmit}
      />
    );
  }
  return { onSubmit, ...render(<Harness />) };
}

function numberInput(fieldName) {
  return within(screen.getByTestId(`field-${fieldName}`)).getByRole("spinbutton");
}

describe("ParamForm", () => {
  it("renders one field per schema entry with default values", () => {
    renderControlledForm();
    for (const name of Object.keys(schema)) {
      expect(screen.getByTestId(`field-${name}`)).toBeInTheDocument();
    }
    expect(numberInput("population")).toHaveValue(10000);
    expect(numberInput("pesticide_kill")).toHaveValue(0.8);
    expect(numberInput("seed")).toHaveValue(42);
  });

  it("gives bounded params a slider and unbounded ones none", () => {
    renderControlledForm();
    expect(within(screen.getByTestId("field-population")).getByRole("slider")).toBeInTheDocument();
    expect(within(screen.getByTestId("field-pesticide_kill")).getByRole("slider")).toBeInTheDocument();
    expect(within(screen.getByTestId("field-seed")).queryByRole("slider")).not.toBeInTheDocument();
  });

  it("blocks out-of-range values: error shown, Run disabled, submit blocked", () => {
    const { onSubmit } = renderControlledForm();
    const run = screen.getByRole("button", { name: /run experiment/i });
    expect(run).toBeEnabled();

    fireEvent.change(numberInput("pesticide_kill"), { target: { value: "1.5" } });

    expect(screen.getByText(/pesticide_kill must be <= 1/)).toBeInTheDocument();
    expect(run).toBeDisabled();
    fireEvent.click(run);
    expect(onSubmit).not.toHaveBeenCalled();

    // Back in range -> error clears and Run works again.
    fireEvent.change(numberInput("pesticide_kill"), { target: { value: "0.9" } });
    expect(screen.queryByText(/must be <= 1/)).not.toBeInTheDocument();
    expect(run).toBeEnabled();
    fireEvent.click(run);
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("blocks empty values", () => {
    renderControlledForm();
    fireEvent.change(numberInput("population"), { target: { value: "" } });
    expect(screen.getByText(/population value required/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run experiment/i })).toBeDisabled();
  });

  it("notifies the parent with (name, value) on change", () => {
    const onChange = vi.fn();
    render(
      <ParamForm schema={schema} params={defaults} onChange={onChange} onSubmit={vi.fn()} />
    );
    fireEvent.change(numberInput("seed"), { target: { value: "7" } });
    expect(onChange).toHaveBeenCalledWith("seed", 7);
  });
});

describe("validateParams", () => {
  it("accepts in-range values", () => {
    expect(validateParams(schema, defaults)).toEqual({});
  });

  it("flags below-min, above-max and missing values", () => {
    const errors = validateParams(schema, {
      population: 0,
      pesticide_kill: 1.5,
      seed: "",
    });
    expect(Object.keys(errors)).toEqual(
      expect.arrayContaining(["population", "pesticide_kill", "seed"])
    );
  });
});
