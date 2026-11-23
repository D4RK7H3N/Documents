"""API tests for the experiments endpoints.

Celery runs eagerly in the test settings (no broker is configured), so a
POST to /api/experiments/ executes the task inline: by the time the
response returns, the experiment is already done with a stored result.
"""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture()
def api():
    return APIClient()


class TestEnginesEndpoint:
    def test_lists_registered_engines_with_schema(self, api):
        response = api.get("/api/engines/")
        assert response.status_code == 200
        engines = {entry["name"]: entry for entry in response.data}
        assert "insect_evo" in engines
        assert engines["insect_evo"]["version"] == "1.1.0"
        assert engines["insect_evo"]["param_schema"]["population"]["default"] == 10000


class TestCreateExperiment:
    def test_valid_post_enqueues_and_completes(self, api):
        response = api.post(
            "/api/experiments/",
            {
                "engine": "insect_evo",
                "params": {"population": 500, "generations": 10, "seed": 7},
            },
            format="json",
        )
        assert response.status_code == 201
        # The POST response reports the submitted state; the client then
        # polls the detail endpoint until the run finishes.
        assert response.data["status"] in {"pending", "running", "done"}

        detail = api.get(f"/api/experiments/{response.data['id']}/")
        assert detail.status_code == 200
        assert detail.data["status"] == "done"
        assert detail.data["engine_version"] == "1.1.0"
        assert detail.data["result"]["summary"]["generations_run"] == 10
        assert len(detail.data["result"]["generations"]) == 10
        assert detail.data["finished_at"] is not None
        assert detail.data["error"] == ""

    def test_omitted_params_use_engine_defaults(self, api):
        response = api.post("/api/experiments/", {"engine": "insect_evo"}, format="json")
        assert response.status_code == 201
        assert response.data["params"]["population"] == 10000
        assert response.data["params"]["seed"] == 42

    def test_unknown_engine_returns_400(self, api):
        response = api.post("/api/experiments/", {"engine": "nope"}, format="json")
        assert response.status_code == 400
        assert "engine" in response.data

    def test_invalid_param_value_returns_400(self, api):
        response = api.post(
            "/api/experiments/",
            {"engine": "insect_evo", "params": {"pesticide_kill": 1.5}},
            format="json",
        )
        assert response.status_code == 400
        assert "pesticide_kill" in str(response.data["params"])

    def test_unknown_param_returns_400(self, api):
        response = api.post(
            "/api/experiments/",
            {"engine": "insect_evo", "params": {"bogus": 1}},
            format="json",
        )
        assert response.status_code == 400
        assert "bogus" in str(response.data["params"])

    def test_wrong_param_type_returns_400(self, api):
        response = api.post(
            "/api/experiments/",
            {"engine": "insect_evo", "params": {"population": "many"}},
            format="json",
        )
        assert response.status_code == 400


class TestReadExperiment:
    def test_list_and_retrieve(self, api):
        created = api.post("/api/experiments/", {"engine": "insect_evo"}, format="json")
        assert created.status_code == 201
        experiment_id = created.data["id"]

        listing = api.get("/api/experiments/")
        assert listing.status_code == 200
        assert any(row["id"] == experiment_id for row in listing.data)

        detail = api.get(f"/api/experiments/{experiment_id}/")
        assert detail.status_code == 200
        assert detail.data["id"] == experiment_id
        assert detail.data["status"] == "done"

    def test_retrieve_unknown_id_returns_404(self, api):
        response = api.get("/api/experiments/00000000-0000-0000-0000-000000000000/")
        assert response.status_code == 404
