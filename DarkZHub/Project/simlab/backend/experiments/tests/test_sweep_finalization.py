"""Finalization semantics for sweeps: conditional UPDATE + concurrency.

The concurrency test runs REAL threads against a FILE-BASED SQLite test
database (configured in settings, TEST NAME) with a Barrier releasing
every worker at the same moment, retrying only on SQLite's
"database is locked" (a single-writer artifact of SQLite, retried inside
this harness only -- never in production code).

What it DOES prove:
  * when N workers observe "no unfinished runs" simultaneously, exactly
    one of them wins the conditional UPDATE (rowcount == 1) and the
    others are no-ops;
  * the final status (done/partial) and the stored aggregate are correct
    and written exactly once.

What it does NOT prove:
  * PostgreSQL MVCC/lock behaviour (no PostgreSQL server is guaranteed
    on this machine -- see the Phase 4.5 report);
  * Celery redelivery semantics or worker-crash handling (the reaper
    covers that path, see test_reap_stale_sweeps.py);
  * performance under production concurrency.
"""

import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from django.db import OperationalError, close_old_connections
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from experiments.models import SweepExperiment, SweepRun

pytestmark = pytest.mark.django_db(transaction=True)


def _with_lock_retry(fn, *args, attempts=10):
    """Retry a callable on SQLite's 'database is locked' only.

    SQLite serializes writers; when several threads upgrade a deferred
    transaction at once one of them can get SQLITE_BUSY immediately
    (busy timeout does not apply to that deadlock-avoidance path).
    Production uses PostgreSQL/SQLite with short transactions; this
    helper exists purely to keep the test harness robust.
    """
    delay = 0.05
    for attempt in range(attempts):
        try:
            return fn(*args)
        except OperationalError as exc:
            if "database is locked" not in str(exc).lower():
                raise
            if attempt == attempts - 1:
                raise
            time.sleep(delay + random.random() * 0.05)
            delay = min(0.5, delay * 2)


def _make_sweep(n_runs: int) -> SweepExperiment:
    sweep = SweepExperiment.objects.create(
        engine="insect_evo",
        base_params={"population": 50, "generations": 2},
        sweep={"pesticide_kill": [0.5]},
        replicates=n_runs,
        status="running",
    )
    SweepRun.objects.bulk_create(
        SweepRun(sweep=sweep, combo_index=0, replicate=i, seed=i)
        for i in range(n_runs)
    )
    return sweep


class TestConcurrentFinalization:
    def test_exactly_one_finalizer_when_all_lands_land_together(self):
        n = 6
        sweep = _make_sweep(n)
        barrier = threading.Barrier(n, timeout=30)
        outcomes = {}
        errors = {}

        def worker(i: int):
            close_old_connections()  # each thread gets its own connection
            try:
                barrier.wait()
                # Synthetic summaries: gen 50% at 3+i, final_freq 0.5.
                fields = {
                    "final_freq": 0.5,
                    "gen_to_50pct": 3 + i,
                    "generations_run": 10,
                    "extinct": False,
                }

                def call():
                    from experiments.tasks import complete_sweep_run

                    return complete_sweep_run(str(sweep.id), 0, i, fields)

                outcomes[i] = _with_lock_retry(call)
            except Exception as exc:  # pragma: no cover - surfaced below
                errors[i] = repr(exc)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=n) as pool:
            futures = [pool.submit(worker, i) for i in range(n)]
            for f in futures:
                f.result(timeout=60)

        assert not errors, f"worker failures: {errors}"
        finalizers = [i for i, r in outcomes.items() if r == "finalized"]
        assert len(finalizers) == 1, outcomes

        sweep.refresh_from_db()
        assert sweep.status == "done"
        assert sweep.engine_version  # written by the single finalizer

        cells = sweep.results["aggregate"]["cells"]
        assert len(cells) == 1
        cell = cells[0]
        assert cell["n"] == n
        assert cell["n_failed"] == 0
        assert cell["n_never_reached"] == 0
        assert cell["final_freq_mean"] == 0.5
        assert cell["final_freq_std"] == 0.0
        assert cell["gen50_mean"] == 5.5  # mean(3..8)
        assert cell["gen50_std"] == pytest.approx(1.707825)

        assert sweep.runs.filter(status=SweepRun.RunStatus.DONE).count() == n
        assert (
            sweep.runs.filter(
                status__in=[SweepRun.RunStatus.PENDING, SweepRun.RunStatus.RUNNING]
            ).count()
            == 0
        )

    def test_exactly_one_finalizer_with_partial_failures(self):
        n = 5
        sweep = _make_sweep(n)
        barrier = threading.Barrier(n, timeout=30)
        outcomes = {}
        errors = {}

        def worker(i: int):
            close_old_connections()
            try:
                barrier.wait()
                if i == 0:
                    fields = {"error": "RuntimeError: boom"}
                else:
                    fields = {
                        "final_freq": 0.5,
                        "gen_to_50pct": 4,
                        "generations_run": 10,
                        "extinct": False,
                    }

                def call():
                    from experiments.tasks import complete_sweep_run

                    return complete_sweep_run(str(sweep.id), 0, i, fields)

                outcomes[i] = _with_lock_retry(call)
            except Exception as exc:  # pragma: no cover
                errors[i] = repr(exc)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=n) as pool:
            futures = [pool.submit(worker, i) for i in range(n)]
            for f in futures:
                f.result(timeout=60)

        assert not errors, f"worker failures: {errors}"
        assert len([r for r in outcomes.values() if r == "finalized"]) == 1
        sweep.refresh_from_db()
        assert sweep.status == "partial"
        cell = sweep.results["aggregate"]["cells"][0]
        assert cell["n"] == n
        assert cell["n_failed"] == 1
        assert cell["final_freq_mean"] == 0.5
        assert cell["gen50_mean"] == 4.0


class TestFinalizeRaceSemantics:
    def test_late_finalize_after_done_is_a_no_op(self):
        """A straggler attempting to finalize an already-done sweep loses
        the conditional UPDATE (rowcount 0) and must not touch the sweep."""
        sweep = _make_sweep(2)
        from experiments.tasks import complete_sweep_run

        assert (
            complete_sweep_run(
                str(sweep.id),
                0,
                0,
                {"final_freq": 0.5, "gen_to_50pct": 3, "generations_run": 5, "extinct": False},
            )
            == "recorded"
        )
        assert (
            complete_sweep_run(
                str(sweep.id),
                0,
                1,
                {"final_freq": 0.6, "gen_to_50pct": 4, "generations_run": 5, "extinct": False},
            )
            == "finalized"
        )
        sweep.refresh_from_db()
        assert sweep.status == "done"
        first_results = sweep.results

        # The straggler: everything done already -> conditional UPDATE misses.
        assert (
            complete_sweep_run(
                str(sweep.id),
                0,
                1,
                {"final_freq": 0.6, "gen_to_50pct": 4, "generations_run": 5, "extinct": False},
            )
            == "already_finalized"
        )
        sweep.refresh_from_db()
        assert sweep.status == "done"
        assert sweep.results == first_results  # aggregate written exactly once

    def test_zero_unfinished_runs_required_to_finalize(self):
        """A finalizer attempt while another run is still pending must NOT
        finalize, and the pending run's own completion must."""
        sweep = _make_sweep(2)
        from experiments.tasks import complete_sweep_run

        outcome = complete_sweep_run(
            str(sweep.id),
            0,
            0,
            {"final_freq": 0.5, "gen_to_50pct": 3, "generations_run": 5, "extinct": False},
        )
        assert outcome == "recorded"
        sweep.refresh_from_db()
        assert sweep.status == "running"
        assert sweep.results is None  # nothing aggregated yet

        outcome = complete_sweep_run(
            str(sweep.id),
            0,
            1,
            {"final_freq": 0.5, "gen_to_50pct": 3, "generations_run": 5, "extinct": False},
        )
        assert outcome == "finalized"
        sweep.refresh_from_db()
        assert sweep.status == "done"
        assert sweep.results is not None
