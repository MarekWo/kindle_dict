# kindle_dict\src\kindle_dict\celery.py

"""
Celery configuration for async task processing.
"""

import os
from celery import Celery

# Set default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kindle_dict.settings.dev')

# Create Celery app
app = Celery('kindle_dict')

# Use Django settings for Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """Basic task for testing Celery"""
    print(f'Request: {self.request!r}')