"""
School Configuration Models
Allows customization of school branding, name, logo, and contact information.
"""
from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.cache import cache


class SchoolConfiguration(models.Model):
    school_name = models.CharField(
        max_length=200,
        default="My School",
        help_text="Official school name"
    )
    school_short_name = models.CharField(
        max_length=50,
        default="SMS",
        help_text="School acronym or short name"
    )
    tagline = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="School motto or tagline"
    )

    address_line1 = models.CharField(
        max_length=200,
        default="",
        blank=True,
        help_text="Street address"
    )
    address_line2 = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Barangay, subdivision, or additional address info"
    )
    city = models.CharField(max_length=100, default="", blank=True)
    province = models.CharField(max_length=100, default="", blank=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default="Philippines")

    phone_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Primary contact number"
    )
    mobile_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Mobile contact number"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Official school email"
    )
    website = models.URLField(
        blank=True,
        null=True,
        help_text="School website URL"
    )

    logo = models.ImageField(
        upload_to='school_config/logos/',
        blank=True,
        null=True,
        # 'svg' removed: an uploaded SVG is same-origin active content and was
        # a stored-XSS vector (the media URL is publicly reachable).
        validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg', 'webp'])],
        help_text="School logo (recommended: 500x500px, PNG with transparent background)"
    )
    header_logo = models.ImageField(
        upload_to='school_config/headers/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg'])],
        help_text="Header logo for receipts and documents (recommended: 1200x300px)"
    )

    receipt_header_text = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Custom text for receipt headers"
    )
    receipt_footer_text = models.TextField(
        blank=True,
        null=True,
        help_text="Footer text for receipts (e.g., 'Thank you for your payment')"
    )

    student_id_prefix = models.CharField(
        max_length=10,
        default="STU",
        help_text="Prefix for student IDs (e.g., 'STU' for STU-2024-001')"
    )

    # Student list / section list print layout. Stored as a JSON array of
    # {"label": "...", "name": "...", "section": "..."} so the number of
    # signatories is not fixed at three. A signatory with an empty section
    # applies to every section; one with a section only prints on that list.
    list_print_signatories = models.TextField(
        blank=True,
        null=True,
        help_text=(
            "JSON array of signatories printed at the bottom of student lists. "
            'e.g. [{"label": "Adviser", "name": "", "section": "Zephaniah"}, '
            '{"label": "Principal/Director", "name": "", "section": ""}]'
        )
    )
    list_print_signature_label = models.CharField(
        max_length=100,
        default="Name and Signature",
        blank=True,
        help_text="Caption printed under each signature line",
    )
    list_print_show_generated_at = models.BooleanField(
        default=True,
        help_text="Print the 'Document generated on ...' timestamp",
    )
    list_print_show_signatures = models.BooleanField(
        default=True,
        help_text="Print the signature block at the bottom of student lists",
    )

    current_academic_year = models.CharField(
        max_length=20,
        default="2025-2026",
        help_text="Current academic year (e.g. 2025-2026)"
    )

    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)

    maintenance_mode = models.BooleanField(
        default=False,
        help_text="When enabled, an announcement banner is shown to all logged-in users"
    )
    maintenance_message = models.TextField(
        blank=True,
        null=True,
        help_text="Message shown to users while maintenance mode is on"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "School Configuration"
        verbose_name_plural = "School Configuration"

    def __str__(self):
        return f"{self.school_name} Configuration"

    def save(self, *args, **kwargs):
        if not self.pk and SchoolConfiguration.objects.exists():
            config = SchoolConfiguration.objects.first()
            self.pk = config.pk

        super().save(*args, **kwargs)
        cache.delete('school_configuration')

    @classmethod
    def get_config(cls):
        config = cache.get('school_configuration')
        if config is None:
            config, created = cls.objects.get_or_create(pk=1)
            cache.set('school_configuration', config, 3600)
        return config

    def get_full_address(self):
        address_parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.province,
            self.zip_code,
            self.country
        ]
        return ", ".join(filter(None, address_parts))

    def get_contact_info(self):
        contacts = []
        if self.phone_number:
            contacts.append(f"Tel: {self.phone_number}")
        if self.mobile_number:
            contacts.append(f"Mobile: {self.mobile_number}")
        if self.email:
            contacts.append(f"Email: {self.email}")
        return " | ".join(contacts)