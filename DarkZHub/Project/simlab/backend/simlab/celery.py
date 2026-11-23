"""Celery application for SimLab background simulation tasks."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "simlab.settings")

app = Celery("simlab")

# Read config from Django settings with the CELERY_ namespace prefix
# (e.g. settings.CELERY_TASK_ALWAYS_EAGER -> task_always_eager).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover tasks in every installed app's tasks.py.
app.autodiscover_tasks()
