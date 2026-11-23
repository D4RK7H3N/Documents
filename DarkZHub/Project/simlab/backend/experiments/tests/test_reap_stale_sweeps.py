"""Tests for the reap_stale_sweeps management command."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

import pytest

from experiments.management.commands.reap_stale_sweeps import REAP_ERROR
from experiments.models import SweepExperiment, SweepRun

pytestmark = pytest.mark.django_db


def _sweep(status="running", minutes_since_update=60.0, n_runs=2, finished=0):
    sweep = SweepExperiment.objects.create(
        engine="insect_evo",
        base_params={"population": 50, "generations": 2},
        sweep={"pesticide_kill": [0.5]},
        replicates=n_runs,
        status=status,
    )
    SweepRun.objects.bulk_create(
        SweepRun(sweep=sweep, combo_index=0, replicate=i, seed=i)
        for i in range(n_runs)
    )
    # Auto_now ignores QuerySet.update(), which is exactly what lets the
    # test backdate the heartbeat to simulate a lost worker.
    age = timedelta(minutes=minutes_since_update)
    SweepExperiment.objects.filter(pk=sweep.pk).update(
        updated_at=timezone.now() - age
    )
    for i in range(finished):
        SweepRun.objects.filter(sweep=sweep, replicate=i).update(
            status=SweepRun.RunStatus.DONE, final_freq=0.5
        )
    return sweep


def _reap(*args):
    out = StringIO()
    call_command("reap_stale_sweeps", *args, stdout=out)
    return out.getvalue()


class TestReapStaleSweeps:
    def test_stale_running_sweep_and_its_runs_are_failed(self):
        sweep = _sweep(status="running", minutes_since_update=60, n_runs=3, finished=1)

        output = _reap("--max-age-minutes", "30")

        assert "reaped 1 sweep(s)" in output
        sweep.refresh_from_db()
        assert sweep.status == "failed"
        reaped = sweep.runs.filter(status=SweepRun.RunStatus.FAILED, error=REAP_ERROR)
        assert reaped.count() == 2
        done = sweep.runs.filter(status=SweepRun.RunStatus.DONE)
        assert done.count() == 1
        assert all(r.error == "" for r in done)
        assert (
            sweep.runs.filter(
                status__in=[SweepRun.RunStatus.PENDING, SweepRun.RunStatus.RUNNING]
            ).count()
            == 0
        )

    def test_stale_pending_sweep_is_reaped(self):
        _sweep(status="pending", minutes_since_update=31)
        output = _reap("--max-age-minutes", "30")
        assert "reaped 1 sweep(s)" in output
        assert SweepExperiment.objects.get().status == "failed"

    def test_fresh_running_sweep_is_not_reaped(self):
        _sweep(status="running", minutes_since_update=5)
        output = _reap("--max-age-minutes", "30")
        assert "reaped 0 sweep(s)" in output
        assert SweepExperiment.objects.get().status == "running"

    def test_age_boundary_is_respected(self):
        # 29 minutes old with a 30 minute threshold: not stale yet.
        _sweep(status="running", minutes_since_update=29)
        output = _reap("--max-age-minutes", "30")
        assert "reaped 0 sweep(s)" in output
        assert SweepExperiment.objects.get().status == "running"

    def test_finished_sweeps_are_never_touched(self):
        _sweep(status="done", minutes_since_update=1000)
        _sweep(status="partial", minutes_since_update=1000)
        _sweep(status="failed", minutes_since_update=1000)
        output = _reap("--max-age-minutes", "30")
        assert "reaped 0 sweep(s)" in output
        statuses = set(SweepExperiment.objects.values_list("status", flat=True))
        assert statuses == {"done", "partial", "failed"}

    def test_dry_run_writes_nothing(self):
        _sweep(status="running", minutes_since_update=120, n_runs=2)
        output = _reap("--dry-run", "--max-age-minutes", "30")

        assert "would reap: " in output
        assert "1 sweep(s) would be reaped" in output
        sweep = SweepExperiment.objects.get()
        assert sweep.status == "running"
        assert sweep.runs.filter(status=SweepRun.RunStatus.PENDING).count() == 2
