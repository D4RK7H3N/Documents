import contextlib
import signal
import time
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from bugfixer.models import BugReport, Status
from bugfixer.services import report_actions
from bugfixer.services.pipeline import claim_report, process_report


@contextlib.contextmanager
def job_timeout(seconds):
    """Hard wall-clock limit for one job (Unix only; no-op on Windows)."""
    if not hasattr(signal, "SIGALRM") or seconds <= 0:
        yield
        return

    def handle_alarm(_signum, _frame):
        raise TimeoutError(f"job exceeded hard timeout of {seconds}s")

    previous = signal.signal(signal.SIGALRM, handle_alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class Command(BaseCommand):
    help = "Poll for queued bug reports and process one at a time."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process at most one report then exit.")
        parser.add_argument("--interval", type=int, default=10, help="Seconds between polls (default: 10).")

    def quota_exceeded(self, project):
        since = timezone.now() - timedelta(hours=1)
        return (
            BugReport.objects.filter(
                project=project,
                updated_at__gte=since,
            )
            .exclude(status=Status.QUEUED)
            .count()
            >= settings.MAX_JOBS_PER_PROJECT_PER_HOUR
        )

    def handle(self, *args, **options):
        self.stdout.write("BugFixer worker started.")
        try:
            while True:
                close_old_connections()
                report = claim_report()
                if report is not None:
                    if self.quota_exceeded(report.project):
                        self.stdout.write(f"Hourly quota reached for project #{report.project_id}; re-queuing.")
                        report_actions.requeue(BugReport.objects.filter(pk=report.pk))
                        time.sleep(60)
                        continue
                    self.stdout.write(f"Processing report #{report.pk}")
                    try:
                        with job_timeout(settings.WORKER_JOB_TIMEOUT):
                            process_report(report)
                    except TimeoutError as exc:
                        self.stderr.write(str(exc))
                    self.stdout.write(f"Report #{report.pk} -> {report.status}")
                if options["once"]:
                    break
                time.sleep(options["interval"])
        except KeyboardInterrupt:
            self.stdout.write("Worker stopped.")
