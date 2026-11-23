"""Reap sweeps whose worker was lost mid-run.

A sweep stuck in pending/running with an ``updated_at`` heartbeat older
than the threshold has no live worker (tasks bump the heartbeat every
time they record a run).  The reaper marks such sweeps ``failed`` and
their unfinished run rows ``failed`` with a distinguishable error.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from experiments.models import SimulationStatus, SweepExperiment, SweepRun

REAP_ERROR = "reaped: worker lost"


class Command(BaseCommand):
    help = (
        "Mark sweeps stuck in pending/running with a stale updated_at "
        "heartbeat as failed, along with their unfinished runs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-age-minutes",
            type=float,
            default=30,
            help="Reap sweeps whose updated_at is older than this many minutes.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be reaped without writing anything.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(minutes=options["max_age_minutes"])
        live_statuses = [SimulationStatus.PENDING, SimulationStatus.RUNNING]

        # The conditional-update pattern: re-check status AND age in the
        # UPDATE itself, so a sweep finished or heartbeated between the
        # listing and the write is never touched.
        stale_ids = list(
            SweepExperiment.objects.filter(
                status__in=live_statuses, updated_at__lt=cutoff
            ).values_list("id", flat=True)
        )

        if options["dry_run"]:
            for sweep_id in stale_ids:
                self.stdout.write(f"would reap: {sweep_id}")
            self.stdout.write(f"{len(stale_ids)} sweep(s) would be reaped")
            return

        sweep_updated = SweepExperiment.objects.filter(
            id__in=stale_ids, status__in=live_statuses, updated_at__lt=cutoff
        ).update(status=SimulationStatus.FAILED)
        runs_updated = (
            SweepRun.objects.filter(
                sweep_id__in=stale_ids,
                status__in=[SweepRun.RunStatus.PENDING, SweepRun.RunStatus.RUNNING],
            )
            .update(
                status=SweepRun.RunStatus.FAILED,
                error=REAP_ERROR,
                updated_at=timezone.now(),
            )
            if stale_ids
            else 0
        )

        self.stdout.write(
            f"reaped {sweep_updated} sweep(s), failed {runs_updated} unfinished run(s)"
        )
