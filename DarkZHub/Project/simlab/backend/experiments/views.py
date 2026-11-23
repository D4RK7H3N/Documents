"""API views: the engine catalog, experiments and sweeps."""

from django.db import transaction
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from engines.registry import list_engines

from .models import Experiment, SimulationStatus, SweepExperiment, SweepRun
from .serializers import (
    ExperimentListSerializer,
    ExperimentSerializer,
    SweepCreateSerializer,
    SweepDetailSerializer,
    SweepListSerializer,
)
from .tasks import run_experiment, run_sweep_point


class EngineListView(APIView):
    """GET /api/engines/ -- every registered engine with its param_schema."""

    def get(self, request):
        return Response(list_engines())


class ExperimentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """POST/GET /api/experiments/ and GET /api/experiments/{id}/."""

    queryset = Experiment.objects.all()
    serializer_class = ExperimentSerializer
    # Only create/read: experiments are immutable once submitted.
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        # History lists use a lightweight serializer without results.
        if self.action == "list":
            return ExperimentListSerializer
        return ExperimentSerializer

    def perform_create(self, serializer) -> None:
        """Persist the validated experiment, then enqueue the run."""
        experiment = serializer.save()
        run_experiment.delay(str(experiment.id))


class SweepViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """POST/GET /api/sweeps/ and GET /api/sweeps/{id}/."""

    queryset = SweepExperiment.objects.all()
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return SweepCreateSerializer
        if self.action == "list":
            return SweepListSerializer
        return SweepDetailSerializer

    def perform_create(self, serializer) -> None:
        """Persist the sweep with every run row, then fan out the tasks.

        All SweepRun rows are created ``pending`` in the same transaction
        as the sweep, so each task only ever updates its own row and the
        final task finalizes via a conditional UPDATE (see tasks.py).
        Works in eager mode too: tasks execute inline after the commit,
        and the last one aggregates and finalizes the sweep.
        """
        run_keys = serializer.sweep_run_keys
        with transaction.atomic():
            sweep = serializer.save()
            sweep.status = SimulationStatus.RUNNING
            sweep.save(update_fields=["status"])
            base_seed = int(sweep.base_params.get("seed", 0))
            SweepRun.objects.bulk_create(
                SweepRun(
                    sweep=sweep,
                    combo_index=combo_index,
                    replicate=replicate,
                    seed=base_seed + replicate,
                )
                for combo_index, replicate in run_keys
            )
        for combo_index, replicate in run_keys:
            run_sweep_point.delay(str(sweep.id), combo_index, replicate)
        # In eager mode the tasks above already finished against the DB row;
        # re-read so the 201 response carries the final status and cells.
        # With a real broker this is a harmless no-op re-read.
        sweep.refresh_from_db()
