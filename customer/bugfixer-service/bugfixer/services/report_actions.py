from ..models import Status
from .git_repo import create_pull_request


def requeue(queryset):
    """Reset a report so the worker can claim it again."""
    return queryset.update(status=Status.QUEUED, result_log="", branch="", pr_url="")


def reject(queryset):
    return queryset.update(status=Status.REJECTED)


def approve_pr(queryset):
    """Open PRs for eligible fix_ready reports. Shared by admin and dashboard API."""
    opened = skipped = failed = 0
    errors = []
    for report in queryset.select_related("project"):
        if (
            report.project.auto_pr
            or report.status != Status.FIX_READY
            or not report.branch
            or report.pr_url
        ):
            skipped += 1
            continue
        try:
            report.pr_url = create_pull_request(report.project, report)
            report.save(update_fields=["pr_url", "updated_at"])
            opened += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Report #{report.pk}: {exc}")
    return {"opened": opened, "skipped": skipped, "failed": failed, "errors": errors}
