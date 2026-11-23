"""WSGI config for the SimLab project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "simlab.settings")

application = get_wsgi_application()
