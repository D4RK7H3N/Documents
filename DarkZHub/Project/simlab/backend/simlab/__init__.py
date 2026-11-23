"""SimLab Django project package.

Importing the Celery application here ensures ``@shared_task`` decorators
resolve against this project's app instance.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
