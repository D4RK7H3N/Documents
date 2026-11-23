"""DRF serializers for the experiments and sweeps APIs."""

from rest_framework import serializers

from engines.registry import get_engine

from .models import Experiment, SweepExperiment, SweepRun
from .tasks import sweep_combos

# Maximum total runs (combinations x replicates) allowed per sweep.
MAX_SWEEP_RUNS = 300
# Max swept parameters per sweep.
MAX_SWEEP_PARAMS = 2


# --------------------------------------------------------------------- #
# Experiments
# --------------------------------------------------------------------- #
class ExperimentListSerializer(serializers.ModelSerializer):
    """Lightweight experiment representation for the History page."""

    class Meta:
        model = Experiment
        fields = [
            "id",
            "engine",
            "params",
            "status",
            "error",
            "engine_version",
            "created_at",
            "finished_at",
        ]


class ExperimentSerializer(serializers.ModelSerializer):
    # ``params`` is optional on input: the engine's validate() fills any
    # missing value with its schema default before persisting.
    params = serializers.JSONField(
        required=False,
        help_text="Engine parameters; omitted values use engine defaults",
    )

    class Meta:
        model = Experiment
        fields = [
            "id",
            "engine",
            "params",
            "status",
            "result",
            "error",
            "engine_version",
            "created_at",
            "finished_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "result",
            "error",
            "engine_version",
            "created_at",
            "finished_at",
        ]

    def validate_engine(self, value: str) -> str:
        """Reject engine names that are not in the registry (400)."""
        try:
            get_engine(value)
        except KeyError:
            raise serializers.ValidationError(
                f"Unknown engine '{value}'."
            ) from None
        return value

    def validate(self, attrs: dict) -> dict:
        """Validate params with the target engine and store the full dict.

        Engine validation errors surface as a clear 400 on the ``params``
        field instead of failing later inside the Celery task.
        """
        engine = get_engine(attrs["engine"])
        try:
            attrs["params"] = engine.validate(attrs.get("params") or {})
        except ValueError as exc:
            raise serializers.ValidationError({"params": str(exc)}) from None
        return attrs


# --------------------------------------------------------------------- #
# Sweeps
# --------------------------------------------------------------------- #
class SweepListSerializer(serializers.ModelSerializer):
    """Lightweight sweep representation for lists / History page."""

    class Meta:
        model = SweepExperiment
        fields = ["id", "engine", "status", "replicates", "sweep", "created_at"]


class SweepDetailSerializer(serializers.ModelSerializer):
    """Full sweep representation with progress, axes and aggregate cells."""

    progress = serializers.SerializerMethodField()
    axes = serializers.SerializerMethodField()
    cells = serializers.SerializerMethodField()

    class Meta:
        model = SweepExperiment
        fields = [
            "id",
            "engine",
            "engine_version",
            "status",
            "replicates",
            "base_params",
            "sweep",
            "created_at",
            "progress",
            "axes",
            "cells",
        ]

    def _sweep_param_names(self, sweep: dict) -> list:
        return list(sweep.keys())

    def _total_runs(self, sweep: dict, replicates: int) -> int:
        combos = 1
        for values in sweep.values():
            combos *= len(values)
        return combos * replicates

    def get_progress(self, obj) -> dict:
        total = self._total_runs(obj.sweep, obj.replicates)
        completed = obj.runs.filter(
            status__in=[SweepRun.RunStatus.DONE, SweepRun.RunStatus.FAILED]
        ).count()
        return {"completed": completed, "total": total}

    def get_axes(self, obj) -> dict:
        names = self._sweep_param_names(obj.sweep)
        return {
            "param_a": names[0],
            "param_b": names[1] if len(names) > 1 else None,
            "values_a": obj.sweep[names[0]],
            "values_b": obj.sweep[names[1]] if len(names) > 1 else [],
        }

    def get_cells(self, obj):
        aggregate = (obj.results or {}).get("aggregate")
        return aggregate.get("cells") if aggregate else None


class SweepCreateSerializer(SweepDetailSerializer):
    """Validates a sweep request; creation pre-creates every run row.

    ``sweep_run_keys`` (populated during validation) lists every
    ``(combo_index, replicate)`` pair: one SweepRun row is created for
    each before any task is dispatched.
    """

    replicates = serializers.IntegerField(min_value=1, max_value=10, required=False)

    def validate(self, attrs: dict) -> dict:
        engine = get_engine(attrs["engine"])
        schema = engine.param_schema

        # Base params: validated and defaults filled before anything is created.
        try:
            attrs["base_params"] = engine.validate(attrs.get("base_params") or {})
        except ValueError as exc:
            raise serializers.ValidationError({"base_params": str(exc)}) from None
        base = attrs["base_params"]

        sweep = attrs.get("sweep")
        if not isinstance(sweep, dict) or not 1 <= len(sweep) <= MAX_SWEEP_PARAMS:
            raise serializers.ValidationError(
                {"sweep": f"Provide 1 or {MAX_SWEEP_PARAMS} sweep parameters."}
            )
        for name, values in sweep.items():
            if name not in schema:
                raise serializers.ValidationError(
                    {"sweep": f"Unknown sweep parameter '{name}'."}
                )
            if name == "seed":
                raise serializers.ValidationError(
                    {"sweep": "Cannot sweep 'seed': it is derived per replicate."}
                )
            if not isinstance(values, list) or not values:
                raise serializers.ValidationError(
                    {"sweep": f"'{name}' must be a non-empty list of values."}
                )

        names = list(sweep.keys())
        b_name = names[1] if len(names) > 1 else None
        b_values = sweep[b_name] if b_name else [None]

        # Same enumeration order the run rows and aggregation use.
        combos = [
            ({names[0]: a_val, **({b_name: b_val} if b_name else {})}, a_i, b_i if b_name else None)
            for a_i, a_val in enumerate(sweep[names[0]])
            for b_i, b_val in enumerate(b_values)
        ]

        replicates = attrs.get("replicates", 3)
        total = len(combos) * replicates
        if total > MAX_SWEEP_RUNS:
            raise serializers.ValidationError(
                {
                    "sweep": (
                        f"{total} runs exceeds the cap of {MAX_SWEEP_RUNS} "
                        f"({len(combos)} combinations x {replicates} replicates)."
                    )
                }
            )

        # Validate every (combination, replicate) with the engine BEFORE
        # creating anything; report the exact failing combination.
        for combo_index, (combo, _a_i, _b_i) in enumerate(combos):
            full = {**base, **combo}
            if "seed" in schema:
                full["seed"] = base.get("seed", 0)
            try:
                engine.validate(full)
            except ValueError as exc:
                raise serializers.ValidationError(
                    {
                        "sweep": (
                            f"Invalid combination {combo} "
                            f"(combo_index {combo_index}): {exc}"
                        )
                    }
                ) from None

        self.sweep_run_keys = [
            (combo_index, replicate)
            for combo_index in range(len(combos))
            for replicate in range(replicates)
        ]
        return attrs
