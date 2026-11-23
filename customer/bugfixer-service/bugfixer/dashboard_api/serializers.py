from django.conf import settings
from rest_framework import serializers

from ..models import BugReport, Project


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=200, write_only=True)


class ProjectSerializer(serializers.ModelSerializer):
    embed_snippet = serializers.SerializerMethodField(read_only=True)
    allowed_origins = serializers.ListField(child=serializers.CharField(), required=False)
    forbidden_paths = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Project
        fields = [
            "id", "name", "public_key", "embed_snippet", "allowed_origins", "repo_url",
            "base_branch", "test_command", "forbidden_paths", "extra_instructions",
            "triage_enabled", "vision_enabled", "auto_pr", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["public_key", "created_at", "updated_at"]

    def get_embed_snippet(self, obj):
        src = settings.WIDGET_URL or "https://YOUR-HOST/widget.js"
        return f'<script src="{src}" data-key="{obj.public_key}" defer></script>'


class ReportListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = BugReport
        fields = [
            "id", "project", "project_name", "status", "classification", "message",
            "reporter_email", "created_at", "updated_at", "pr_url",
        ]


class ReportDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    screenshot_url = serializers.SerializerMethodField()

    class Meta:
        model = BugReport
        fields = [
            "id", "project", "project_name", "status", "classification", "message",
            "reporter_id", "reporter_email", "page_url", "user_agent", "console_log",
            "screenshot_url", "screenshot_description", "branch", "pr_url", "result_log",
            "status_token", "created_at", "updated_at",
        ]

    def get_screenshot_url(self, obj):
        if not obj.screenshot:
            return None
        return f"/api/dashboard/reports/{obj.pk}/screenshot/"
