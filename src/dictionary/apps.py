# kindle_dict\src\dictionary\apps.py

"""
App configuration for the Dictionary app.
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class DictionaryConfig(AppConfig):
    """Configuration for Dictionary app"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dictionary'
    verbose_name = _('Dictionary')
    
    def ready(self):
        """Code to run when app is ready"""
        import dictionary.signals  # noqa