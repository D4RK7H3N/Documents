"""Insect-evolution engine: haploid model with one resistance allele.

Model (Wright-Fisher style, per generation):

1. **Survival** -- resistant individuals always survive; non-resistant
   individuals survive with probability ``1 - pesticide_kill``.
2. **Extinction** -- if nobody survived, record the generation with
   ``freq = 0`` and ``size = 0`` and stop.
3. **Reproduction** -- sample exactly ``population`` offspring from the
   survivors.  Parent weights: ``1 - resistance_cost`` for resistant
   parents, ``1.0`` for non-resistant parents.
4. **Mutation** -- each offspring flips its allele with probability
   ``mutation_rate``.
5. **Record** -- ``{"gen", "freq", "size", "resistant_survivors",
   "normal_survivors"}`` where ``freq`` is the resistant-allele frequency
   among the newly produced generation (the state carried into the next
   generation), ``size`` is the number of individuals that survived the
   pesticide during this generation, and ``resistant_survivors`` /
   ``normal_survivors`` split ``size`` by type (they always sum to
   ``size``; added in engine 1.1.0 -- older stored results lack them and
   consumers must fall back to deriving counts from ``freq``/``size``).

All randomness flows through ``numpy.random.default_rng(seed)``, so a run
is fully reproducible from its parameters alone.
"""

from __future__ import annotations

import numpy as np

from .base import Engine
from .registry import register


@register
class InsectEvolution(Engine):
    """Haploid, single-locus pesticide-resistance evolution model."""

    name = "insect_evo"
    version = "1.1.0"

    param_schema = {
        "population": {
            "type": "integer",
            "default": 10000,
            "min": 1,
            "max": 10_000_000,
        },
        "generations": {
            "type": "integer",
            "default": 200,
            "min": 1,
            "max": 100_000,
        },
        "mutation_rate": {
            "type": "number",
            "default": 1e-4,
            "min": 0.0,
            "max": 1.0,
        },
        "pesticide_kill": {
            "type": "number",
            "default": 0.8,
            "min": 0.0,
            "max": 1.0,
        },
        "resistance_cost": {
            "type": "number",
            "default": 0.1,
            "min": 0.0,
            "max": 1.0,
        },
        "start_freq": {
            "type": "number",
            "default": 0.01,
            "min": 0.0,
            "max": 1.0,
        },
        "seed": {
            "type": "integer",
            "default": 42,
            "min": 0,
        },
    }

    def run(self, params: dict) -> dict:
        """Run the simulation and return ``{"generations", "summary"}``."""
        p = self.validate(params)  # Never trust raw input, even internally.
        rng = np.random.default_rng(p["seed"])
        population = p["population"]

        # Initial allele vector: 1 = resistant, 0 = sensitive.  The first
        # round(start_freq * population) individuals are resistant.
        n_resistant = int(round(p["start_freq"] * population))
        alleles = np.zeros(population, dtype=np.int8)
        if n_resistant > 0:
            alleles[:n_resistant] = 1

        generations_out: list[dict] = []
        extinct = False
        gen_to_50pct: int | None = None

        for gen in range(1, p["generations"] + 1):
            # 1. Survival: resistant always survive; non-resistant survive
            #    with probability (1 - pesticide_kill).
            survive = (alleles == 1) | (
                rng.random(population) >= p["pesticide_kill"]
            )
            survivors = alleles[survive]

            # 2. Extinction: nobody alive -> record this generation and stop.
            if survivors.size == 0:
                generations_out.append(
                    {
                        "gen": gen,
                        "freq": 0.0,
                        "size": 0,
                        "resistant_survivors": 0,
                        "normal_survivors": 0,
                    }
                )
                extinct = True
                break

            # Survivor counts by type.  Counting consumes no randomness, so
            # gen/freq/size stay bit-identical to engine 1.0.0 output.
            resistant_survivors = int((survivors == 1).sum())
            normal_survivors = int(survivors.size) - resistant_survivors

            # 3. Reproduction: sample the next generation from the survivors
            #    with parent weights (1 - resistance_cost) vs 1.0.
            weights = np.where(
                survivors == 1, 1.0 - p["resistance_cost"], 1.0
            )
            total = float(weights.sum())
            # Degenerate case (e.g. every parent resistant with cost 1.0):
            # fall back to uniform sampling instead of dividing by zero.
            probs = weights / total if total > 0 else None
            offspring = rng.choice(survivors, size=population, p=probs)

            # 4. Mutation: flip each offspring's allele with prob mutation_rate.
            flips = rng.random(population) < p["mutation_rate"]
            offspring[flips] ^= 1

            # 5. Record this generation.
            freq = float(offspring.mean())
            generations_out.append(
                {
                    "gen": gen,
                    "freq": freq,
                    "size": int(survivors.size),
                    "resistant_survivors": resistant_survivors,
                    "normal_survivors": normal_survivors,
                }
            )
            if gen_to_50pct is None and freq >= 0.5:
                gen_to_50pct = gen

            alleles = offspring

        summary = {
            "final_freq": generations_out[-1]["freq"],
            "generations_run": len(generations_out),
            "extinct": extinct,
            "gen_to_50pct": gen_to_50pct,
        }
        return {"generations": generations_out, "summary": summary}
