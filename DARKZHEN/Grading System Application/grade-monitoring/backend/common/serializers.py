from django.conf import settings
from django.db import transaction
from rest_framework import serializers

from audit.services import record_audit

from .models import SystemConfig


class SystemConfigSerializer(serializers.ModelSerializer):
    logo_url = serializers.CharField(read_only=True)

    class Meta:
        model = SystemConfig
        fields = ["school_name", "short_name", "logo", "logo_url", "default_school_year", "updated_at"]
        read_only_fields = ["logo_url", "updated_at"]

    def validate_logo(self, value):
        if value is None:
            return value
        allowed = (".png", ".jpg", ".jpeg", ".svg", ".webp")
        if not value.name.lower().endswith(allowed):
            raise serializers.ValidationError("Logo must be a PNG, JPG, SVG or WEBP file.")
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Logo must be smaller than 2 MB.")
        return value

    def update(self, instance, validated_data):
        old = {
            "school_name": instance.school_name,
            "short_name": instance.short_name,
            "default_school_year": instance.default_school_year,
            "logo": instance.logo.name if instance.logo else None,
        }
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            instance.updated_by = self.context["request"].user
            instance.save(update_fields=["updated_by"])
            record_audit(
                actor=self.context["request"].user,
                action="system_config.update",
                entity="system_config",
                entity_id=instance.id,
                old_values=old,
                new_values={
                    "school_name": instance.school_name,
                    "short_name": instance.short_name,
                    "default_school_year": instance.default_school_year,
                    "logo": instance.logo.name if instance.logo else None,
                },
            )
        return instance
