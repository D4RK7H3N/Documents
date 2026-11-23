from .models import SchoolConfiguration


def school_config(request):
    try:
        config = SchoolConfiguration.get_config()
        return {
            'school_config': config,
            'school_name': config.school_name,
            'school_logo_url': request.build_absolute_uri(config.logo.url) if config.logo else None,
            'school_short_name': config.school_short_name,
        }
    except Exception:
        return {
            'school_config': None,
            'school_name': 'School Management System',
            'school_logo_url': None,
            'school_short_name': 'SMS',
        }