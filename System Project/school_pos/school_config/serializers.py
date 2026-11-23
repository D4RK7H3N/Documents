"""
Serializers for School Configuration API.
"""
import json
from urllib.parse import urlparse

from django.conf import settings
from rest_framework import serializers

from .models import SchoolConfiguration

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "testserver"}


def _is_local_host(hostname):
    return bool(hostname) and hostname.lower() in LOCAL_HOSTS


class SchoolConfigurationSerializer(serializers.ModelSerializer):
    full_address = serializers.CharField(source='get_full_address', read_only=True)
    contact_info = serializers.CharField(source='get_contact_info', read_only=True)
    # Mission P3: plain ImageFields are rendered by DRF with
    # request.build_absolute_uri() -> an absolute backend host leaks into API
    # responses. Publish root-relative media paths instead; /media/* is served
    # by the same public origin via the proxy Worker.
    logo = serializers.SerializerMethodField()
    header_logo = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()
    header_logo_url = serializers.SerializerMethodField()
    # Stored as JSON text; exposed as a real list so the UI can bind to it
    # directly and a malformed value can never reach the print templates.
    list_print_signatories = serializers.SerializerMethodField()

    class Meta:
        model = SchoolConfiguration
        fields = [
            'id',
            'school_name',
            'school_short_name',
            'tagline',
            'address_line1',
            'address_line2',
            'city',
            'province',
            'zip_code',
            'country',
            'full_address',
            'phone_number',
            'mobile_number',
            'email',
            'website',
            'logo',
            'logo_url',
            'header_logo',
            'header_logo_url',
            'receipt_header_text',
            'receipt_footer_text',
            'list_print_signatories',
            'list_print_signature_label',
            'list_print_show_generated_at',
            'list_print_show_signatures',
            'report_checked_by',
            'student_id_prefix',
            'current_academic_year',
            'facebook_url',
            'twitter_url',
            'instagram_url',
            'maintenance_mode',
            'maintenance_message',
            'contact_info',
            'updated_at'
        ]
        read_only_fields = ['id', 'updated_at', 'full_address', 'contact_info']

    def get_list_print_signatories(self, obj):
        """Parse the stored JSON into a list of {label, name} dicts.

        Returns an empty list rather than raising so a hand-edited or corrupt
        value can never break the print view.
        """
        raw = (obj.list_print_signatories or "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if not isinstance(data, list):
            return []
        out = []
        for item in data:
            if isinstance(item, str):
                item = {"label": item}
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label:
                continue
            out.append({
                "label": label,
                "name": str(item.get("name") or "").strip(),
                # Empty section means the signatory applies to every section
                # (e.g. Principal/Director). Otherwise it only prints on the
                # matching section's list.
                "section": str(item.get("section") or "").strip(),
            })
        return out

    def _build_secure_url(self, request, url):
        """Build an absolute media URL from the canonical public origin.

        Deliberately ignores ``request``: ``build_absolute_uri()`` derives the
        scheme and host from the incoming request, which behind the Cloudflare
        tunnel yields ``http://`` asset URLs (blocked by browsers as mixed
        content) and is additionally vulnerable to Host-header injection. When
        DEBUG is on we still keep the request-derived URL so LAN/HTTP dev works.
        """
        if not url:
            return None

        if url.startswith(("http://", "https://")):
            parsed = urlparse(url)
            if parsed.scheme == "http" and not _is_local_host(parsed.hostname):
                return "https://" + url[len("http://") :]
            return url

        if settings.DEBUG and request:
            return request.build_absolute_uri(url)

        origin = (getattr(settings, "PUBLIC_ORIGIN", "") or "").rstrip("/")
        if origin:
            return origin + "/" + url.lstrip("/")
        return url

    @staticmethod
    def _relative_media_url(url):
        if not url:
            return None
        parts = urlparse(url)
        return parts.path + (f"?{parts.query}" if parts.query else "")

    def get_logo(self, obj):
        return self._relative_media_url(obj.logo.url) if obj.logo else None

    def get_header_logo(self, obj):
        return self._relative_media_url(obj.header_logo.url) if obj.header_logo else None

    def get_logo_url(self, obj):
        if obj.logo:
            return self._build_secure_url(self.context.get("request"), obj.logo.url)
        return None

    def get_header_logo_url(self, obj):
        if obj.header_logo:
            return self._build_secure_url(self.context.get("request"), obj.header_logo.url)
        return None


class SchoolConfigurationUpdateSerializer(serializers.ModelSerializer):
    # Accepts a real list from the UI and stores it as JSON text.
    list_print_signatories = serializers.JSONField(
        required=False, allow_null=True
    )

    class Meta:
        model = SchoolConfiguration
        fields = [
            'school_name',
            'school_short_name',
            'tagline',
            'address_line1',
            'address_line2',
            'city',
            'province',
            'zip_code',
            'country',
            'phone_number',
            'mobile_number',
            'email',
            'website',
            'logo',
            'header_logo',
            'receipt_header_text',
            'receipt_footer_text',
            'list_print_signature_label',
            'list_print_show_generated_at',
            'list_print_show_signatures',
            'student_id_prefix',
            'current_academic_year',
            'facebook_url',
            'twitter_url',
            'instagram_url',
            'maintenance_mode',
            'maintenance_message',
            'list_print_signatories',
            # "Checked by" on the Daily Collection & Disbursement Report.
            'report_checked_by',
        ]

    def validate_list_print_signatories(self, value):
        """Normalise to [{label, name}] and reject non-list / oversized input."""
        if value in (None, ""):
            return None
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "Must be a list of signatories, e.g. [{\"label\": \"Adviser\", \"name\": \"\"}]"
            )
        if len(value) > 8:
            raise serializers.ValidationError("A maximum of 8 signatories is allowed.")
        out = []
        for item in value:
            if isinstance(item, str):
                item = {"label": item}
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    "Each signatory must be an object with a 'label'."
                )
            label = str(item.get("label") or "").strip()
            if not label:
                continue
            out.append({
                "label": label[:100],
                "name": str(item.get("name") or "").strip()[:200],
                "section": str(item.get("section") or "").strip()[:100],
            })
        return json.dumps(out) if out else None

    def create(self, validated_data):
        return SchoolConfiguration.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance