from django.core.management.base import BaseCommand
from school_config.models import SchoolConfiguration
import os


class Command(BaseCommand):
    help = 'Reset school configuration to generic defaults'

    def handle(self, *args, **kwargs):
        config, created = SchoolConfiguration.objects.get_or_create(pk=1)
        config.school_name = 'My School'
        config.school_short_name = 'SMS'
        config.tagline = ''
        config.address_line1 = ''
        config.address_line2 = ''
        config.city = ''
        config.province = ''
        config.zip_code = ''
        config.country = 'Philippines'
        config.phone_number = ''
        config.mobile_number = ''
        config.email = ''
        config.website = ''
        config.receipt_header_text = ''
        config.receipt_footer_text = 'Thank you for your payment!'
        config.facebook_url = ''
        config.twitter_url = ''
        config.instagram_url = ''
        config.current_academic_year = '2025-2026'
        config.student_id_prefix = 'STU'

        if config.logo:
            if os.path.isfile(config.logo.path):
                os.remove(config.logo.path)
            config.logo = None
        if config.header_logo:
            if os.path.isfile(config.header_logo.path):
                os.remove(config.header_logo.path)
            config.header_logo = None

        config.save()
        self.stdout.write(self.style.SUCCESS('[OK] School configuration reset to defaults.'))