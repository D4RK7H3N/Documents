from django.contrib import admin, messages
from django.utils.html import format_html

from .models import BugReport, Project
from .services import report_actions


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "public_key",
        "base_branch",
        "auto_pr",
        "triage_enabled",
        "vision_enabled",
        "is_active",
    )
    list_filter = ("auto_pr", "triage_enabled", "vision_enabled", "is_active")
    search_fields = ("name", "public_key", "repo_url")
    readonly_fields = ("public_key", "created_at", "updated_at")


@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "status", "classification", "reporter_email", "created_at")
    list_filter = ("status", "classification", "project")
    search_fields = ("id", "message", "reporter_id", "reporter_email", "page_url", "branch")
    readonly_fields = (
        "screenshot_preview",
        "status_token",
        "result_log",
        "branch",
        "pr_url",
        "classification",
        "screenshot_description",
        "created_at",
        "updated_at",
    )
    actions = ("requeue_reports", "mark_rejected", "approve_and_open_pr")

    @admin.display(description="Screenshot")
    def screenshot_preview(self, obj):
        if not obj.screenshot:
            return "—"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener"><img src="{}" style="max-height:220px" /></a>',
            obj.screenshot.url,
            obj.screenshot.url,
        )

    @admin.action(description="Re-queue selected reports")
    def requeue_reports(self, request, queryset):
        count = report_actions.requeue(queryset)
        self.message_user(request, f"Re-queued {count} report(s).", messages.SUCCESS)

    @admin.action(description="Mark selected reports as rejected")
    def mark_rejected(self, request, queryset):
        count = report_actions.reject(queryset)
        self.message_user(request, f"Marked {count} report(s) as rejected.", messages.SUCCESS)

    @admin.action(description="Approve and open PR (non-auto_pr projects)")
    def approve_and_open_pr(self, request, queryset):
        result = report_actions.approve_pr(queryset)
        for error in result["errors"]:
            self.message_user(request, error, messages.ERROR)
        self.message_user(
            request,
            f"Opened {result['opened']} PR(s), skipped {result['skipped']}, failed {result['failed']}.",
            messages.SUCCESS,
        )
