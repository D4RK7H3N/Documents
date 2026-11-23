"""Standalone Phase-1 demo: run the insect-evolution engine and plot it.

Run from the ``backend`` directory:

    python scripts/run_insect_evo.py
    python scripts/run_insect_evo.py --population 5000 --generations 100 --seed 7
    python scripts/run_insect_evo.py --pesticide-kill 1.0 --start-freq 0
    python scripts/run_insect_evo.py --save out.png --no-show

Omitted parameters fall back to the engine's schema defaults.  The plot is
labelled "Simulation result, not experimental evidence." to match the
SimLab product rule.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running the script directly from a checkout: put ``backend/`` (the
# parent of this ``scripts/`` folder) on sys.path so ``engines`` imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines import get_engine  # noqa: E402  (import after sys.path setup)

# Dark, near-black theme shared with the future frontend.
BG_COLOR = "#121016"
PANEL_COLOR = "#1c1826"
ACCENT_COLOR = "#a78bfa"  # purple
TEXT_COLOR = "#d4d0dc"
MUTED_COLOR = "#8b8494"
GRID_COLOR = "#3a3444"


def build_parser() -> argparse.ArgumentParser:
    """CLI options mirror the engine's param_schema (all optional)."""
    parser = argparse.ArgumentParser(
        description="Run the InsectEvolution engine and plot the results."
    )
    parser.add_argument("--population", type=int, help="Population size (default 10000)")
    parser.add_argument("--generations", type=int, help="Number of generations (default 200)")
    parser.add_argument(
        "--mutation-rate", type=float, help="Per-individual flip probability (default 1e-4)"
    )
    parser.add_argument(
        "--pesticide-kill", type=float, help="Kill probability for non-resistant (default 0.8)"
    )
    parser.add_argument(
        "--resistance-cost", type=float, help="Fitness cost of resistance (default 0.1)"
    )
    parser.add_argument(
        "--start-freq", type=float, help="Initial resistant frequency (default 0.01)"
    )
    parser.add_argument("--seed", type=int, help="RNG seed for reproducibility (default 42)")
    parser.add_argument("--save", type=Path, help="Save the plot to this PNG path")
    parser.add_argument(
        "--no-show", action="store_true", help="Do not open an interactive window"
    )
    return parser


def plot(result: dict, params: dict, save_path: Path | None, show: bool) -> None:
    """Draw frequency (purple) and surviving population (grey) over time."""
    # Headless-safe backend is enough when we only write a file.
    if save_path is not None:
        import matplotlib

        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    gens = result["generations"]
    x = [g["gen"] for g in gens]
    freq = [g["freq"] for g in gens]
    size = [g["size"] for g in gens]

    fig, ax1 = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(BG_COLOR)
    ax1.set_facecolor(BG_COLOR)

    # Primary axis: resistant-allele frequency per generation.
    ax1.plot(x, freq, color=ACCENT_COLOR, linewidth=1.8, label="Resistant allele frequency")
    ax1.set_xlabel("Generation", color=TEXT_COLOR)
    ax1.set_ylabel("Frequency", color=ACCENT_COLOR)
    ax1.set_ylim(-0.02, 1.02)
    ax1.tick_params(colors=TEXT_COLOR)
    ax1.grid(True, color=GRID_COLOR, alpha=0.4)

    # Secondary axis: surviving population size per generation.
    ax2 = ax1.twinx()
    ax2.plot(
        x, size, color="#9ca3af", linewidth=1.2, linestyle="--",
        label="Surviving population",
    )
    ax2.set_ylabel("Population size", color=MUTED_COLOR)
    ax2.tick_params(colors=MUTED_COLOR)

    ax1.set_title(
        f"Insect evolution - seed {params['seed']}, "
        f"pesticide_kill {params['pesticide_kill']}, "
        f"resistance_cost {params['resistance_cost']}",
        color="#e5e1ec",
    )
    # Mandatory SimLab disclaimer on every result view.
    fig.text(
        0.5, 0.01,
        "Simulation result, not experimental evidence.",
        ha="center", fontsize=9, color=MUTED_COLOR,
    )

    for spine in (*ax1.spines.values(), *ax2.spines.values()):
        spine.set_color(GRID_COLOR)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    leg = ax1.legend(
        lines1 + lines2, labels1 + labels2, loc="upper left",
        facecolor=PANEL_COLOR, edgecolor=GRID_COLOR,
    )
    for text in leg.get_texts():
        text.set_color(TEXT_COLOR)

    fig.tight_layout(rect=(0, 0.03, 1, 1))

    if save_path is not None:
        fig.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
        print(f"Plot saved to {save_path}")
    if show:
        plt.show()


def main() -> int:
    args = build_parser().parse_args()

    # Collect only the parameters the user actually provided; the engine's
    # validate() fills in schema defaults for the rest.
    provided = {
        "population": args.population,
        "generations": args.generations,
        "mutation_rate": args.mutation_rate,
        "pesticide_kill": args.pesticide_kill,
        "resistance_cost": args.resistance_cost,
        "start_freq": args.start_freq,
        "seed": args.seed,
    }
    params = {key: value for key, value in provided.items() if value is not None}

    engine = get_engine("insect_evo")
    validated = engine.validate(params)  # Full params for display purposes.
    result = engine.run(validated)       # run() validates internally too.

    print(json.dumps(result["summary"], indent=2))

    if args.no_show and args.save is None:
        return 0  # Summary-only mode.

    plot(result, validated, args.save, show=not args.no_show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
