"""Tests for the InsectEvolution engine.

Covers the Phase-1 acceptance criteria: reproducibility (determinism),
extinction handling, and the shape/invariants of run() output.
"""

import pytest

from engines.base import EngineValidationError
from engines.registry import get_engine


@pytest.fixture()
def engine():
    return get_engine("insect_evo")


class TestDeterminism:
    def test_same_seed_gives_identical_results(self, engine):
        result_a = engine.run({"seed": 123})
        result_b = engine.run({"seed": 123})
        assert result_a == result_b

    def test_different_seed_gives_different_trajectory(self, engine):
        small = {"population": 500, "generations": 50, "mutation_rate": 0.0}
        freqs_a = [g["freq"] for g in engine.run({**small, "seed": 1})["generations"]]
        freqs_b = [g["freq"] for g in engine.run({**small, "seed": 2})["generations"]]
        assert freqs_a != freqs_b


class TestExtinction:
    def test_immediate_extinction_recorded_once(self, engine):
        # No resistant individuals and total kill: everything dies in
        # generation 1, leaving exactly one record with freq 0 / size 0.
        result = engine.run(
            {"start_freq": 0.0, "pesticide_kill": 1.0, "generations": 10}
        )
        assert result["generations"] == [
            {"gen": 1, "freq": 0.0, "size": 0, "resistant_survivors": 0, "normal_survivors": 0}
        ]
        assert result["summary"]["extinct"] is True
        assert result["summary"]["generations_run"] == 1
        assert result["summary"]["final_freq"] == 0.0

    def test_sensitive_population_dies_out_without_mutation(self, engine):
        # No resistant allele and no mutation: the population must go
        # extinct well before the generation cap.  A small population is
        # required because reproduction restores `population` offspring
        # each generation, so extinction needs every individual to fail
        # survival in the same generation (prob = kill ** population).
        result = engine.run(
            {
                "population": 15,
                "pesticide_kill": 0.8,
                "mutation_rate": 0.0,
                "generations": 100,
                "seed": 11,
            }
        )
        assert result["summary"]["extinct"] is True
        assert result["summary"]["generations_run"] < 100
        last = result["generations"][-1]
        assert last["freq"] == 0.0
        assert last["size"] == 0

    def test_resistant_population_survives_total_kill(self, engine):
        # 10% resistant, everyone else killed instantly, no mutation:
        # the resistant subpopulation recovers to fixation.
        result = engine.run(
            {
                "start_freq": 0.1,
                "pesticide_kill": 1.0,
                "mutation_rate": 0.0,
                "resistance_cost": 0.0,
                "generations": 5,
            }
        )
        assert result["summary"]["extinct"] is False
        assert result["summary"]["final_freq"] == 1.0
        assert result["summary"]["gen_to_50pct"] == 1


class TestDynamics:
    def test_full_mutation_flips_every_generation(self, engine):
        # mutation_rate = 1.0 flips every allele after reproduction, so the
        # frequency must oscillate 0, 1, 0, 1 deterministically.
        result = engine.run(
            {
                "start_freq": 1.0,
                "pesticide_kill": 0.0,
                "mutation_rate": 1.0,
                "generations": 4,
            }
        )
        freqs = [g["freq"] for g in result["generations"]]
        assert freqs == [0.0, 1.0, 0.0, 1.0]

    def test_gen_to_50pct_is_first_crossing(self, engine):
        result = engine.run(
            {"start_freq": 0.6, "pesticide_kill": 0.5, "generations": 10}
        )
        first = next(g["gen"] for g in result["generations"] if g["freq"] >= 0.5)
        assert result["summary"]["gen_to_50pct"] == first

    def test_gen_to_50pct_none_when_allele_is_lost(self, engine):
        # Tiny population, strong resistance cost, no mutation: drift plus
        # selection eliminates the allele and 50% is never reached.
        result = engine.run(
            {
                "population": 100,
                "start_freq": 0.04,
                "mutation_rate": 0.0,
                "resistance_cost": 0.9,
                "pesticide_kill": 0.0,
                "generations": 50,
                "seed": 7,
            }
        )
        assert result["summary"]["gen_to_50pct"] is None
        assert result["summary"]["extinct"] is False


class TestResultShape:
    def test_result_structure_with_defaults(self, engine):
        result = engine.run({})
        assert set(result.keys()) == {"generations", "summary"}

        gens = result["generations"]
        assert len(gens) == 200
        for i, record in enumerate(gens, start=1):
            assert record["gen"] == i
            assert 0.0 <= record["freq"] <= 1.0
            assert 0 < record["size"] <= 10000

        summary = result["summary"]
        assert set(summary.keys()) == {
            "final_freq",
            "generations_run",
            "extinct",
            "gen_to_50pct",
        }
        assert summary["generations_run"] == 200
        assert summary["extinct"] is False
        assert summary["final_freq"] == gens[-1]["freq"]

    def test_run_rejects_invalid_params(self, engine):
        with pytest.raises(EngineValidationError):
            engine.run({"pesticide_kill": 2.0})


class TestSurvivorFields:
    """Engine 1.1.0 records per-type survivor counts per generation."""

    def test_survivor_counts_sum_to_size(self, engine):
        result = engine.run({"seed": 42})
        for record in result["generations"]:
            assert (
                record["resistant_survivors"] + record["normal_survivors"]
                == record["size"]
            )

    def test_extinction_record_has_zero_survivors(self, engine):
        result = engine.run({"start_freq": 0.0, "pesticide_kill": 1.0, "generations": 5})
        assert result["generations"] == [
            {
                "gen": 1,
                "freq": 0.0,
                "size": 0,
                "resistant_survivors": 0,
                "normal_survivors": 0,
            }
        ]

    def test_determinism_still_holds(self, engine):
        assert engine.run({"seed": 7}) == engine.run({"seed": 7})

    def test_old_fields_match_engine_1_0_0_golden_values(self, engine):
        # Adding survivor counting consumes no randomness, so gen/freq/size
        # must stay bit-identical to engine 1.0.0 output (recorded from the
        # 1.0.0 engine before the fields were introduced).
        result = engine.run({"seed": 42})  # all other params default
        assert result["summary"] == {
            "final_freq": 0.9999,
            "generations_run": 200,
            "extinct": False,
            "gen_to_50pct": 4,
        }
        assert result["generations"][0] == {
            "gen": 1,
            "freq": 0.0429,
            "size": 2040,
            "resistant_survivors": 100,  # all 100 resistant always survive
            "normal_survivors": 1940,
        }
        assert result["generations"][1]["gen"] == 2
        assert result["generations"][1]["freq"] == 0.17
        assert result["generations"][1]["size"] == 2328


class TestSelectionMath:
    """Science sanity checks against the hand-derived selection recursion."""

    def test_first_generation_matches_deterministic_formula(self, engine):
        # Derivation from the engine's actual survival-then-reproduction
        # order, with mutation_rate = 0:
        #
        #   1. Survival: resistant individuals survive with probability 1, so
        #      n_r survive; normal individuals survive with probability
        #      (1 - kill), giving n_s * (1 - kill) in expectation.
        #   2. Reproduction: offspring are sampled from survivors with parent
        #      weights (1 - cost) for resistant and 1.0 for normal, so the
        #      expected resistant frequency among offspring is
        #
        #      freq_1 = (1-cost) * n_r / ((1-cost) * n_r + (1-kill) * n_s)
        #
        #      where n_r = round(start_freq * N) and n_s = N - n_r.
        #
        # With N = 1e6 both sampling steps concentrate tightly on these
        # expectations.  Residual noise: reproduction is Binomial(N, p) with
        # sd = sqrt(N p (1-p)) / N ~ 5e-4, plus ~1.4e-4 from survival, so a
        # 2e-3 tolerance is ~4 sigma of sampling noise.
        population = 1_000_000
        params = {
            "population": population,
            "generations": 1,
            "mutation_rate": 0.0,
            "pesticide_kill": 0.7,
            "resistance_cost": 0.2,
            "start_freq": 0.3,
            "seed": 5,
        }
        n_r = round(params["start_freq"] * population)
        n_s = population - n_r
        expected = (1 - params["resistance_cost"]) * n_r / (
            (1 - params["resistance_cost"]) * n_r
            + (1 - params["pesticide_kill"]) * n_s
        )

        observed = engine.run(params)["generations"][0]["freq"]
        assert abs(observed - expected) < 2e-3

    def test_no_pesticide_with_cost_decreases_frequency(self, engine):
        # With pesticide_kill = 0 everyone survives, so the only force is the
        # fitness cost against resistance.  The recursion becomes
        #   freq_{t+1} = (1-cost) * f / ((1-cost) * f + (1-f))
        # which is strictly below f for any 0 < f < 1 and cost > 0: the
        # frequency must decrease over time.
        params = {
            "population": 100_000,
            "generations": 25,
            "mutation_rate": 0.0,
            "pesticide_kill": 0.0,
            "resistance_cost": 0.1,
            "start_freq": 0.5,
            "seed": 3,
        }
        freqs = [g["freq"] for g in engine.run(params)["generations"]]
        assert all(b < a for a, b in zip(freqs, freqs[1:])), freqs
