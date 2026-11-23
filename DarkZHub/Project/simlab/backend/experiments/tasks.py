"""Celery tasks: run engines outside the request/response cycle."""

import logging
import statistics
from itertools import product as cartesian

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.db import transaction
from django.utils import timezone

from engines.registry import get_engine

from .models import Experiment, SimulationStatus, SweepExperiment, SweepRun

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- #
# Single experiment runs
# --------------------------------------------------------------------- #
@shared_task(bind=True, soft_time_limit=110, time_limit=120)
def run_experiment(self, experiment_id: str) -> str:
    """Execute one experiment to completion.

    Status flow: pending -> running -> done | failed.  The engine output
    is stored on the row; any failure is persisted in ``error`` and
    re-raised so Celery also records the task failure.
    """
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
    except Experiment.DoesNotExist:
        logger.error("run_experiment: experiment %s not found", experiment_id)
        return "not_found"

    experiment.status = SimulationStatus.RUNNING
    experiment.save(update_fields=["status"])

    try:
        engine = get_engine(experiment.engine)
        result = engine.run(experiment.params)
    except SoftTimeLimitExceeded:
        experiment.status = SimulationStatus.FAILED
        experiment.error = "Simulation exceeded the 110s soft time limit."
        experiment.finished_at = timezone.now()
        experiment.save(update_fields=["status", "error", "finished_at"])
        raise
    except Exception as exc:  # noqa: BLE001 -- failures must reach the DB
        experiment.status = SimulationStatus.FAILED
        experiment.error = f"{type(exc).__name__}: {exc}"
        experiment.finished_at = timezone.now()
        experiment.save(update_fields=["status", "error", "finished_at"])
        raise

    experiment.result = result
    experiment.engine_version = engine.version
    experiment.status = SimulationStatus.DONE
    experiment.finished_at = timezone.now()
    experiment.save(
        update_fields=["result", "engine_version", "status", "finished_at"]
    )
    return "done"


# --------------------------------------------------------------------- #
# Parameter sweeps
# --------------------------------------------------------------------- #
def sweep_combos(sweep: dict) -> list[dict]:
    """Cartesian product of the sweep lists in enumeration order.

    ``combo_index`` in SweepRun refers to a position in this list.  The
    order matches SweepCreateSerializer: last key varies fastest.
    """
    names = list(sweep.keys())
    return [dict(zip(names, values)) for values in cartesian(*(sweep[n] for n in names))]


def combo_indices(sweep: dict, combo_index: int) -> tuple[int, int | None]:
    """(a_index, b_index) for a combo index; b is None for 1-axis sweeps."""
    names = list(sweep.keys())
    if len(names) < 2:
        return combo_index, None
    b_len = len(sweep[names[1]])
    return combo_index // b_len, combo_index % b_len


@shared_task(bind=True, soft_time_limit=110, time_limit=120)
def run_sweep_point(self, sweep_id: str, combo_index: int, replicate: int) -> str:
    """Run one (combination, replicate) cell of a sweep.

    A failed run never fails the sweep: the error is recorded on the
    run's own SweepRun row and counted in the cell's ``n_failed``.  The
    task touches only its own run row; when it notices that no run is
    unfinished anymore it finalizes the sweep with one conditional
    UPDATE (see ``complete_sweep_run``).
    """
    try:
        sweep = SweepExperiment.objects.get(pk=sweep_id)
    except SweepExperiment.DoesNotExist:
        logger.error("run_sweep_point: sweep %s not found", sweep_id)
        return "not_found"

    combos = sweep_combos(sweep.sweep)
    if not 0 <= combo_index < len(combos):
        logger.error(
            "run_sweep_point: sweep %s has no combo_index %s", sweep_id, combo_index
        )
        return "bad_combo_index"

    run_row = SweepRun.objects.filter(
        sweep_id=sweep_id, combo_index=combo_index, replicate=replicate
    ).first()
    if run_row is None:
        logger.error(
            "run_sweep_point: sweep %s has no run (combo %s, replicate %s)",
            sweep_id,
            combo_index,
            replicate,
        )
        return "run_not_found"

    combo = combos[combo_index]
    params = {**sweep.base_params, **combo}
    # Replicate i of base_seed is a deterministic, reproducible run; the
    # seed was fixed when the run row was created and must not drift.
    if run_row.seed is not None:
        params["seed"] = run_row.seed

    fields = {}
    try:
        summary = get_engine(sweep.engine).run(params)["summary"]
        fields = {
            "final_freq": summary["final_freq"],
            "gen_to_50pct": summary["gen_to_50pct"],
            "generations_run": summary["generations_run"],
            "extinct": summary["extinct"],
        }
    except Exception as exc:  # noqa: BLE001 -- recorded, sweep continues
        fields = {"error": f"{type(exc).__name__}: {exc}"}

    complete_sweep_run(sweep_id, combo_index, replicate, fields)
    return "ok"


def complete_sweep_run(sweep_id, combo_index: int, replicate: int, fields: dict) -> str:
    """Record one finished run and finalize the sweep when it is the last.

    Atomicity strategy (no locks held across engine work, no JSON
    read-modify-write):

    1. UPDATE the caller's own SweepRun row (done | failed + summary).
    2. Bump the sweep's ``updated_at`` heartbeat.
    3. COUNT runs still pending/running -- zero means this worker may be
       the last.
    4. Attempt finalization with ONE conditional UPDATE restricted to
       ``status IN (pending, running)``.  ``rowcount == 1`` means this
       worker finalized; ``rowcount == 0`` means another worker already
       did, so this one does nothing.

    Returns ``"finalized"`` for the single winning worker, or
    ``"recorded"`` / ``"already_finalized"`` otherwise.
    """
    now = timezone.now()
    run_status = (
        SweepRun.RunStatus.FAILED if fields.get("error") else SweepRun.RunStatus.DONE
    )

    with transaction.atomic():
        SweepRun.objects.filter(
            sweep_id=sweep_id, combo_index=combo_index, replicate=replicate
        ).update(
            status=run_status,
            final_freq=fields.get("final_freq"),
            gen_to_50pct=fields.get("gen_to_50pct"),
            generations_run=fields.get("generations_run"),
            extinct=fields.get("extinct"),
            error=fields.get("error", ""),
            updated_at=now,
        )
        # Heartbeat: proves a live worker is still making progress, so the
        # reaper only fires on genuinely lost sweeps.
        SweepExperiment.objects.filter(pk=sweep_id).update(updated_at=now)

        unfinished = SweepRun.objects.filter(
            sweep_id=sweep_id,
            status__in=[SweepRun.RunStatus.PENDING, SweepRun.RunStatus.RUNNING],
        ).count()
        if unfinished:
            return "recorded"

        sweep = SweepExperiment.objects.filter(pk=sweep_id).first()
        if sweep is None:
            return "recorded"

        any_failed = SweepRun.objects.filter(
            sweep_id=sweep_id, status=SweepRun.RunStatus.FAILED
        ).exists()
        final_status = (
            SimulationStatus.PARTIAL if any_failed else SimulationStatus.DONE
        )
        # Single conditional UPDATE: at most one concurrent worker sees
        # rowcount 1; everyone else loses the race and does nothing.
        finalized = SweepExperiment.objects.filter(
            pk=sweep_id,
            status__in=[SimulationStatus.PENDING, SimulationStatus.RUNNING],
        ).update(
            status=final_status,
            engine_version=get_engine(sweep.engine).version,
            results={"aggregate": build_sweep_aggregate(sweep)},
            updated_at=now,
        )
        return "finalized" if finalized == 1 else "already_finalized"


def build_sweep_aggregate(sweep: SweepExperiment) -> dict:
    """Aggregate SweepRun rows into per-cell statistics.

    Per cell:
      * final_freq mean/std over successful runs,
      * gen_to_50pct mean/std over successful runs that reached 50% only
        (never-reached runs are excluded and counted in n_never_reached),
      * n (runs), n_failed, n_never_reached.

    Std is the population std (pstdev), defined for single-run cells.
    """
    sweep_params = list(sweep.sweep.keys())
    b_name = sweep_params[1] if len(sweep_params) > 1 else None
    b_values = sweep.sweep[b_name] if b_name else [None]

    def _mean(values):
        return round(statistics.mean(values), 6) if values else None

    def _std(values):
        return round(statistics.pstdev(values), 6) if values else None

    # One query, grouped in Python by derived (a_index, b_index).
    cells_map: dict[tuple, dict] = {}
    for run in sweep.runs.all():
        a_index, b_index = combo_indices(sweep.sweep, run.combo_index)
        key = (a_index, b_index)
        cells_map.setdefault(key, []).append(run)

    cells = []
    for a_index, a_val in enumerate(sweep.sweep[sweep_params[0]]):
        for b_index, b_val in enumerate(b_values):
            cell_runs = cells_map.get(
                (a_index, b_index if b_name else None), []
            )
            done = [r for r in cell_runs if r.status == SweepRun.RunStatus.DONE]
            reached = [r.gen_to_50pct for r in done if r.gen_to_50pct is not None]
            freqs = [r.final_freq for r in done]
            cells.append(
                {
                    "a_index": a_index,
                    "b_index": b_index if b_name else None,
                    "a": a_val,
                    "b": b_val,
                    "n": len(cell_runs),
                    "n_failed": len(cell_runs) - len(done),
                    "n_never_reached": len(done) - len(reached),
                    "final_freq_mean": _mean(freqs),
                    "final_freq_std": _std(freqs),
                    "gen50_mean": _mean(reached),
                    "gen50_std": _std(reached),
                }
            )
    return {"cells": cells}
