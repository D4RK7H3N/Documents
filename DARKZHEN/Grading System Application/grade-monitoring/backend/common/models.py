from django.conf import settings
from django.db import models


class SystemConfig(models.Model):
    school_name = models.CharField(max_length=150, default="Sagay National High School")
    short_name = models.CharField(max_length=20, default="SNHS")
    logo = models.FileField(upload_to="branding/", blank=True, null=True)
    default_school_year = models.CharField(max_length=9, default="2026-2027")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System configuration"

    @classmethod
    def load(cls):
        config = cls.objects.first()
        if config is None:
            config = cls.objects.create()
        return config

    @property
    def logo_url(self):
        if self.logo and self.logo.name:
            return self.logo.url
        return None
