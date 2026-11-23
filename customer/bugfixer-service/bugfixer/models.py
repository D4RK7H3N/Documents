import secrets

from django.db import models


def new_public_key():
    return secrets.token_urlsafe(24)


def new_status_token():
    return secrets.token_urlsafe(24)


class Project(models.Model):
    name = models.CharField(max_length=200)
    public_key = models.CharField(max_length=128, unique=True, default=new_public_key, db_index=True)
    allowed_origins = models.JSONField(default=list, blank=True)
    repo_url = models.CharField(max_length=500)
    base_branch = models.CharField(max_length=200, default="main")
    test_command = models.CharField(max_length=500, blank=True)
    forbidden_paths = models.JSONField(default=list, blank=True)
    extra_instructions = models.TextField(blank=True)
    triage_enabled = models.BooleanField(default=True)
    vision_enabled = models.BooleanField(default=False)
    auto_pr = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Status(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    FIX_READY = "fix_ready", "Fix ready"
    FAILED = "failed", "Failed"
    REJECTED = "rejected", "Rejected"


STATUS_MESSAGES = {
    Status.QUEUED: "We received your report and it is queued for review.",
    Status.RUNNING: "We are working on a fix for your report.",
    Status.FIX_READY: "A fix is ready and is awaiting approval.",
    Status.FAILED: "We could not produce an automatic fix for this report.",
    Status.REJECTED: "Thanks for the report, but it is not something we can auto-fix.",
}


class BugReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="reports")
    reporter_id = models.CharField(max_length=200, blank=True)
    reporter_email = models.EmailField(blank=True)
    message = models.TextField()
    screenshot = models.ImageField(upload_to="screenshots/", blank=True, null=True)
    page_url = models.TextField(blank=True)
    user_agent = models.TextField(blank=True)
    console_log = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    classification = models.CharField(max_length=40, blank=True)
    screenshot_description = models.TextField(blank=True)
    branch = models.CharField(max_length=300, blank=True)
    pr_url = models.URLField(blank=True)
    result_log = models.TextField(blank=True)
    status_token = models.CharField(max_length=128, unique=True, default=new_status_token, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report #{self.pk} ({self.project.name})"

    @property
    def friendly_message(self):
        return STATUS_MESSAGES.get(self.status, "We are reviewing your report.")
