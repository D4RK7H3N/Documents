"""Database models for experiments and parameter sweeps."""

import uuid

from django.db import models


class SimulationStatus(models.TextChoices):
    """Lifecycle shared by experiments and sweeps."""

    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    DONE = "done", "Done"
    PARTIAL = "partial", "Partial"  # sweep finished, some runs failed
    FAILED = "failed", "Failed"


class Experiment(models.Model):
    """A single simulation run: engine + validated params -> result."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    engine = models.CharField(max_length=100, help_text="Registered engine name")
    params = models.JSONField(default=dict, help_text="Validated engine parameters")
    status = models.CharField(
        max_length=20,
        choices=SimulationStatus.choices,
        default=SimulationStatus.PENDING,
        db_index=True,
    )
    result = models.JSONField(
        null=True, blank=True, help_text="Engine output: {generations, summary}"
    )
    error = models.TextField(blank=True, default="", help_text="Failure reason, if any")
    engine_version = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.engine} experiment {self.id} ({self.status})"


class SweepExperiment(models.Model):
    """A parameter sweep over the cartesian product of ``sweep`` lists."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    engine = models.CharField(max_length=100, help_text="Registered engine name")
    base_params = models.JSONField(
        default=dict, help_text="Parameters shared by every combination"
    )
    sweep = models.JSONField(
        help_text='Parameter lists to combine, e.g. {"pesticide_kill": [0.2, 0.8]}'
    )
    replicates = models.PositiveSmallIntegerField(
        default=3, help_text="Runs per combination; replicate i uses seed base_seed + i"
    )
    status = models.CharField(
        max_length=20,
        choices=SimulationStatus.choices,
        default=SimulationStatus.PENDING,
        db_index=True,
    )
    results = models.JSONField(
        null=True,
        blank=True,
        help_text="Final aggregate written once by the finalizer: {aggregate: {cells}}",
    )
    engine_version = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    # Liveness heartbeat: tasks bump this when they record a run, so the
    # reaper can distinguish a working sweep from a lost worker.  Updated
    # explicitly by QuerySet.update() calls (auto_now only fires on save()).
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.engine} sweep {self.id} ({self.status})"


class SweepRun(models.Model):
    """One (combination, replicate) run of a sweep.

    Rows are created up front together with the sweep, all ``pending``.
    Each worker claims and updates ONLY its own row; the last worker to
    finish notices zero unfinished rows and finalizes the sweep with a
    single conditional UPDATE (no JSON read-modify-write anywhere).
    """

    class RunStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    sweep = models.ForeignKey(
        SweepExperiment, on_delete=models.CASCADE, related_name="runs"
    )
    combo_index = models.PositiveIntegerField(
        help_text="Index into the sweep's cartesian product of parameter lists"
    )
    replicate = models.PositiveSmallIntegerField()
    seed = models.IntegerField(null=True, blank=True, help_text="base_seed + replicate")
    status = models.CharField(
        max_length=20,
        choices=RunStatus.choices,
        default=RunStatus.PENDING,
    )
    final_freq = models.FloatField(null=True, blank=True)
    gen_to_50pct = models.IntegerField(null=True, blank=True)
    generations_run = models.PositiveIntegerField(null=True, blank=True)
    extinct = models.BooleanField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sweep", "combo_index", "replicate"],
                name="uniq_sweeprun_sweep_combo_replicate",
            )
        ]
        indexes = [
            models.Index(fields=["sweep", "status"]),
        ]
        ordering = ["combo_index", "replicate"]

    def __str__(self) -> str:
        return f"{self.sweep_id} combo {self.combo_index} rep {self.replicate} ({self.status})"
