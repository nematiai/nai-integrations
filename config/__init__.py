"""Django project package.

Importing the Celery app here ensures @shared_task decorators bind
to the 'nemi' app at Django startup.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
