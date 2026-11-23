"""Tests for base Engine validation and the engine registry."""

import pytest

from engines.base import EngineValidationError
from engines.registry import get_engine, list_engines


@pytest.fixture()
def engine():
    return get_engine("insect_evo")


class TestParamValidation:
    """Engine.validate must fill defaults and reject invalid input."""

    def test_defaults_are_filled(self, engine):
        params = engine.validate({})
        assert params["population"] == 10000
        assert params["generations"] == 200
        assert params["mutation_rate"] == 1e-4
        assert params["pesticide_kill"] == 0.8
        assert params["resistance_cost"] == 0.1
        assert params["start_freq"] == 0.01
        assert params["seed"] == 42

    def test_user_values_override_defaults(self, engine):
        params = engine.validate({"population": 500, "seed": 7})
        assert params["population"] == 500
        assert params["seed"] == 7
        assert params["generations"] == 200  # untouched default

    def test_unknown_parameter_is_rejected(self, engine):
        with pytest.raises(EngineValidationError):
            engine.validate({"populaton": 100})  # typo must fail loudly

    def test_value_below_min_is_rejected(self, engine):
        with pytest.raises(EngineValidationError):
            engine.validate({"population": 0})

    def test_value_above_max_is_rejected(self, engine):
        with pytest.raises(EngineValidationError):
            engine.validate({"pesticide_kill": 1.5})

    def test_wrong_type_is_rejected(self, engine):
        with pytest.raises(EngineValidationError):
            engine.validate({"population": "ten thousand"})

    def test_boolean_is_not_an_integer(self, engine):
        with pytest.raises(EngineValidationError):
            engine.validate({"population": True})

    def test_boundary_values_are_accepted(self, engine):
        params = engine.validate(
            {"pesticide_kill": 1.0, "mutation_rate": 0.0, "population": 1}
        )
        assert params["pesticide_kill"] == 1.0
        assert params["mutation_rate"] == 0.0
        assert params["population"] == 1

    def test_error_message_names_the_parameter(self, engine):
        with pytest.raises(EngineValidationError, match="pesticide_kill"):
            engine.validate({"pesticide_kill": 42})


class TestRegistry:
    def test_get_engine_returns_configured_instance(self):
        engine = get_engine("insect_evo")
        assert engine.name == "insect_evo"
        assert "population" in engine.param_schema

    def test_unknown_engine_raises_key_error(self):
        with pytest.raises(KeyError, match="does_not_exist"):
            get_engine("does_not_exist")

    def test_list_engines_includes_insect_evo(self):
        descriptors = {d["name"]: d for d in list_engines()}
        assert "insect_evo" in descriptors
        assert descriptors["insect_evo"]["param_schema"]["population"]["default"] == 10000
