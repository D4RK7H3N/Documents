import bugfixer.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("public_key", models.CharField(db_index=True, default=bugfixer.models.new_public_key, max_length=128, unique=True)),
                ("allowed_origins", models.JSONField(blank=True, default=list)),
                ("repo_url", models.CharField(max_length=500)),
                ("base_branch", models.CharField(default="main", max_length=200)),
                ("test_command", models.CharField(blank=True, max_length=500)),
                ("forbidden_paths", models.JSONField(blank=True, default=list)),
                ("extra_instructions", models.TextField(blank=True)),
                ("triage_enabled", models.BooleanField(default=True)),
                ("vision_enabled", models.BooleanField(default=False)),
                ("auto_pr", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BugReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reporter_id", models.CharField(blank=True, max_length=200)),
                ("reporter_email", models.EmailField(blank=True, max_length=254)),
                ("message", models.TextField()),
                ("screenshot", models.ImageField(blank=True, null=True, upload_to="screenshots/")),
                ("page_url", models.TextField(blank=True)),
                ("user_agent", models.TextField(blank=True)),
                ("console_log", models.TextField(blank=True)),
                ("status", models.CharField(
                    choices=[("queued", "Queued"), ("running", "Running"), ("fix_ready", "Fix ready"),
                             ("failed", "Failed"), ("rejected", "Rejected")],
                    db_index=True, default="queued", max_length=20,
                )),
                ("classification", models.CharField(blank=True, max_length=40)),
                ("screenshot_description", models.TextField(blank=True)),
                ("branch", models.CharField(blank=True, max_length=300)),
                ("pr_url", models.URLField(blank=True, max_length=200)),
                ("result_log", models.TextField(blank=True)),
                ("status_token", models.CharField(db_index=True, default=bugfixer.models.new_status_token, max_length=128, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="bugfixer.project"
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
