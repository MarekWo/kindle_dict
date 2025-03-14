# kindle_dict\src\kindle_dict\__init__.py

"""
Kindle Dictionary Creator project initialization.
"""

# Import celery app for proper initialization
from .celery import app as celery_app

__all__ = ('celery_app',)