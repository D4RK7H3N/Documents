from django.conf import settings
from django.db import transaction

from ..models import BugReport, Status
from .email import notify_fix
from .git_repo import add_worktree, changed_files, commit_and_push, create_pull_request, remove_worktree
from .guards import find_forbidden
from .opencode import run_opencode, run_tests
from .prompt import build_prompt
from .triage import classify
from .vision import describe_screenshot


def truncate(text, limit=None):
    return (text or "")[: limit or settings.RESULT_LOG_MAX_CHARS]


def claim_report():
    """Atomically claim a single queued report without blocking other workers."""
    with transaction.atomic():
        report = (
            BugReport.objects.select_for_update(skip_locked=True)
            .filter(status=Status.QUEUED)
            .order_by("created_at")
            .first()
        )
        if report is not None:
            report.status = Status.RUNNING
            report.save(update_fields=["status", "updated_at"])
    return report


def process_report(report):
    project = report.project
    logs = []
    worktree = None
    prompt_file = None
    try:
        if project.triage_enabled:
            report.classification = classify(report.message)
            if report.classification != "bug":
                report.status = Status.REJECTED
                logs.append(f"Triaged as {report.classification}; no fix attempted.")
                return

        description = ""
        if project.vision_enabled and report.screenshot:
            description = describe_screenshot(report.screenshot.path)
        report.screenshot_description = description

        worktree, branch = add_worktree(project, report)
        report.branch = branch

        prompt_dir = settings.WORKDIR / "prompts"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = prompt_dir / f"report-{report.pk}.txt"
        prompt_file.write_text(build_prompt(report, description), encoding="utf-8")

        logs.append(run_opencode(worktree, prompt_file.read_text(encoding="utf-8")))
        if project.test_command:
            logs.append(run_tests(worktree, project.test_command))

        changed = changed_files(worktree)
        if not changed:
            raise RuntimeError("The agent produced no changes (empty diff).")
        forbidden = find_forbidden(changed, project.forbidden_paths)
        if forbidden:
            raise RuntimeError("Diff touches forbidden paths: " + ", ".join(forbidden))

        commit_and_push(project, report, worktree, branch)
        if project.auto_pr:
            report.pr_url = create_pull_request(project, report)
        report.status = Status.FIX_READY
    except Exception as exc:
        report.status = Status.FAILED
        logs.append(f"ERROR: {exc}")
    finally:
        if worktree is not None:
            try:
                remove_worktree(report.pk, project)
            except Exception as exc:
                logs.append(f"cleanup warning: {exc}")
        if prompt_file is not None:
            try:
                prompt_file.unlink(missing_ok=True)
            except Exception:
                pass
        report.result_log = truncate("\n".join(logs))
        report.save()
        if report.status == Status.FIX_READY:
            try:
                notify_fix(report)
            except Exception as exc:
                report.result_log = truncate(report.result_log + f"\nemail warning: {exc}")
                report.save(update_fields=["result_log"])
