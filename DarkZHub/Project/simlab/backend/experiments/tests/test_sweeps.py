"""Tests for the sweep API, execution and aggregation.

Celery runs eagerly in the test settings, so a POST to /api/sweeps/
executes every run inline: the response already carries the aggregate.
"""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from engines.registry import get_engine

from experiments.models import SweepExperiment, SweepRun
from experiments.tasks import build_sweep_aggregate

pytestmark = pytest.mark.django_db


@pytest.fixture()
def api():
    return APIClient()


def sweep_payload(**overrides):
    payload = {
        "engine": "insect_evo",
        "base_params": {"population": 500, "generations": 20},
        "sweep": {"pesticide_kill": [0.2, 0.8], "resistance_cost": [0.0, 0.1]},
        "replicates": 2,
    }
    payload.update(overrides)
    return payload


class TestSweepCreation:
    def test_cartesian_product_count(self, api):
        resp = api.post("/api/sweeps/", sweep_payload(), format="json")
        assert resp.status_code == 201
        # 2 kill values x 2 cost values x 2 replicates = 8 runs, 4 cells.
        assert resp.data["progress"]["total"] == 8
        assert resp.data["progress"]["completed"] == 8  # eager: done inline
        assert resp.data["status"] == "done"
        assert resp.data["engine_version"] == "1.1.0"
        assert len(resp.data["cells"]) == 4
        for cell in resp.data["cells"]:
            assert cell["n"] == 2
            assert cell["n_failed"] == 0

        # Replicate i must use seed = base_seed + i.
        sweep = SweepExperiment.objects.get(pk=resp.data["id"])
        seeds = sorted({run.seed for run in sweep.runs.all()})
        assert seeds == [42, 43]
        # Every run row exists up front as a distinct (combo, replicate).
        assert sweep.runs.count() == 8
        assert (
            sweep.runs.filter(
                sweep=sweep,
                combo_index=0,
                replicate=0,
                status="done",
            ).count()
            == 1
        )

    def test_one_param_sweep_has_single_axis(self, api):
        resp = api.post(
            "/api/sweeps/",
            sweep_payload(sweep={"pesticide_kill": [0.2, 0.5, 0.8]}),
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["axes"]["param_a"] == "pesticide_kill"
        assert resp.data["axes"]["param_b"] is None
        assert resp.data["progress"]["total"] == 6
        assert len(resp.data["cells"]) == 3
        assert all(cell["b_index"] is None for cell in resp.data["cells"])

    def test_sweep_list_is_lightweight(self, api):
        api.post("/api/sweeps/", sweep_payload(), format="json")
        listing = api.get("/api/sweeps/")
        assert listing.status_code == 200
        assert len(listing.data) == 1
        assert "cells" not in listing.data[0]
        assert listing.data[0]["replicates"] == 2


class TestSweepValidation:
    def test_cap_enforcement_301_runs_returns_400(self, api):
        # 51 combinations x 6 replicates = 306 runs > cap of 300.
        resp = api.post(
            "/api/sweeps/",
            sweep_payload(sweep={"generations": list(range(1, 52))}, replicates=6),
            format="json",
        )
        assert resp.status_code == 400
        assert "300" in str(resp.data)

    def test_cap_boundary_300_runs_allowed(self, api):
        # 50 combinations x 6 replicates = exactly 300 runs.
        resp = api.post(
            "/api/sweeps/",
            sweep_payload(
                sweep={"generations": list(range(1, 51))},
                replicates=6,
                base_params={"population": 50},
            ),
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["progress"]["total"] == 300

    def test_validation_error_names_failing_combination(self, api):
        resp = api.post(
            "/api/sweeps/",
            sweep_payload(sweep={"pesticide_kill": [0.5, 1.5], "resistance_cost": [0.0]}),
            format="json",
        )
        assert resp.status_code == 400
        text = str(resp.data)
        assert "1.5" in text  # the failing value
        assert "pesticide_kill" in text  # the failing parameter

    def test_seed_cannot_be_swept(self, api):
        resp = api.post(
            "/api/sweeps/", sweep_payload(sweep={"seed": [1, 2]}), format="json"
        )
        assert resp.status_code == 400

    def test_unknown_sweep_param_rejected(self, api):
        resp = api.post("/api/sweeps/", sweep_payload(sweep={"bogus": [1]}), format="json")
        assert resp.status_code == 400

    def test_three_sweep_params_rejected(self, api):
        resp = api.post(
            "/api/sweeps/",
            sweep_payload(
                sweep={
                    "pesticide_kill": [0.5],
                    "resistance_cost": [0.0],
                    "mutation_rate": [0.0],
                }
            ),
            format="json",
        )
        assert resp.status_code == 400

    def test_replicates_out_of_range_rejected(self, api):
        resp = api.post("/api/sweeps/", sweep_payload(replicates=11), format="json")
        assert resp.status_code == 400

    def test_invalid_base_params_rejected(self, api):
        resp = api.post(
            "/api/sweeps/", sweep_payload(base_params={"population": -5}), format="json"
        )
        assert resp.status_code == 400


class TestSweepDeterminism:
    def test_same_request_gives_same_aggregate(self, api):
        # Replicate seeds derive from base_seed, so identical requests must
        # produce identical per-cell statistics.
        first = api.post("/api/sweeps/", sweep_payload(), format="json")
        second = api.post("/api/sweeps/", sweep_payload(), format="json")
        assert first.data["cells"] == second.data["cells"]


class TestSweepFailureHandling:
    def test_failed_run_records_n_failed_and_keeps_sweep_done(self, api):
        # A run that raises must not fail the sweep: the error is recorded
        # per run and the cell reports n_failed; the sweep ends "partial".
        real_engine = get_engine("insect_evo")

        class FlakyEngine:
            name = real_engine.name
            version = real_engine.version
            param_schema = real_engine.param_schema

            def validate(self, params):
                return real_engine.validate(params)

            def run(self, params):
                # Replicate 1 (seed 42 + 1) of every combination fails.
                if params.get("seed") == 43:
                    raise RuntimeError("boom")
                return real_engine.run(params)

        with mock.patch("experiments.tasks.get_engine", return_value=FlakyEngine()):
            resp = api.post("/api/sweeps/", sweep_payload(replicates=2), format="json")

        assert resp.status_code == 201
        assert resp.data["status"] == "partial"
        for cell in resp.data["cells"]:
            assert cell["n"] == 2
            assert cell["n_failed"] == 1
            # Statistics still computed from the surviving replicate.
            assert cell["final_freq_mean"] is not None
            assert cell["final_freq_std"] == 0.0  # single sample


class TestAggregation:
    def _sweep_with_runs(self, sweep_dict, run_specs):
        sweep = SweepExperiment.objects.create(
            engine="insect_evo",
            base_params={},
            sweep=sweep_dict,
            replicates=max(r["replicate"] for r in run_specs) + 1,
            status="done",
        )
        for spec in run_specs:
            kwargs = {
                **spec,
                "status": (
                    SweepRun.RunStatus.FAILED
                    if spec.get("error")
                    else SweepRun.RunStatus.DONE
                ),
                "generations_run": spec.get("generations_run", 10),
                "extinct": spec.get("extinct", False),
                "error": spec.get("error", ""),
            }
            SweepRun.objects.create(sweep=sweep, **kwargs)
        return sweep

    def test_gen50_mean_excludes_never_reached_runs(self):
        sweep = self._sweep_with_runs(
            {"kill": [0.2]},
            [
                {"combo_index": 0, "replicate": 0, "seed": 0,
                 "final_freq": 1.0, "gen_to_50pct": 3},
                {"combo_index": 0, "replicate": 1, "seed": 1,
                 "final_freq": 0.5, "gen_to_50pct": None},
                {"combo_index": 0, "replicate": 2, "seed": 2,
                 "final_freq": 0.2, "gen_to_50pct": 5},
            ],
        )
        cell = build_sweep_aggregate(sweep)["cells"][0]
        assert cell["n"] == 3
        assert cell["n_never_reached"] == 1
        # Mean over the two runs that reached 50% only: (3 + 5) / 2.
        assert cell["gen50_mean"] == pytest.approx(4.0)
        assert cell["gen50_std"] == pytest.approx(1.0)
        # final_freq uses all successful runs.
        assert cell["final_freq_mean"] == pytest.approx((1.0 + 0.5 + 0.2) / 3)

    def test_failed_runs_counted_and_excluded_from_means(self):
        sweep = self._sweep_with_runs(
            {"kill": [0.2]},
            [
                {"combo_index": 0, "replicate": 0, "seed": 0,
                 "final_freq": 0.8, "gen_to_50pct": 4},
                {"combo_index": 0, "replicate": 1, "seed": 1,
                 "error": "RuntimeError: boom"},
            ],
        )
        cell = build_sweep_aggregate(sweep)["cells"][0]
        assert cell["n"] == 2
        assert cell["n_failed"] == 1
        assert cell["final_freq_mean"] == pytest.approx(0.8)
        assert cell["gen50_mean"] == pytest.approx(4.0)

    def test_all_failed_cell_has_null_means(self):
        sweep = self._sweep_with_runs(
            {"kill": [0.2]},
            [
                {"combo_index": 0, "replicate": 0, "seed": 0,
                 "error": "RuntimeError: boom"},
            ],
        )
        cell = build_sweep_aggregate(sweep)["cells"][0]
        assert cell["n_failed"] == 1
        assert cell["final_freq_mean"] is None
        assert cell["gen50_mean"] is None
        assert cell["n_never_reached"] == 0
