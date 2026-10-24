# src\dictionary\signals.py

"""
Signal handlers for the Dictionary app.
"""

import os
import logging
from django.db.models.signals import post_delete, pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Dictionary, DictionarySuggestion, Task, UserSettings
from .email_utils import send_dictionary_completion_email, send_task_notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=get_user_model())
def ensure_user_settings(sender, instance, created, **kwargs):
    """Create a UserSettings row whenever a new User is created.

    Eliminates the lazy `UserSettings.get_for_user` pattern for new
    accounts and gives downstream code (registration flow, profile,
    email-2FA) a guaranteed-present settings row to read/write.
    """
    if created:
        UserSettings.objects.get_or_create(user=instance)

@receiver(post_delete, sender=Dictionary)
def auto_delete_files_on_delete(sender, instance, **kwargs):
    """
    Delete files from filesystem when Dictionary instance is deleted.
    """
    try:
        # Delete source file
        if instance.source_file and os.path.isfile(instance.source_file.path):
            os.remove(instance.source_file.path)
        
        # Delete generated files
        if instance.html_file and os.path.isfile(instance.html_file.path):
            os.remove(instance.html_file.path)
        
        if instance.opf_file and os.path.isfile(instance.opf_file.path):
            os.remove(instance.opf_file.path)
        
        if instance.jpg_file and os.path.isfile(instance.jpg_file.path):
            os.remove(instance.jpg_file.path)
        
        if instance.mobi_file and os.path.isfile(instance.mobi_file.path):
            os.remove(instance.mobi_file.path)
        
        if instance.json_file and os.path.isfile(instance.json_file.path):
            os.remove(instance.json_file.path)
        
        if instance.zip_file and os.path.isfile(instance.zip_file.path):
            os.remove(instance.zip_file.path)
        
        # Try to remove the parent directory as well
        directory = os.path.dirname(instance.source_file.path) if instance.source_file else None
        if directory and os.path.exists(directory):
            os.rmdir(directory)
    
    except Exception as e:
        logger.error(f"Error deleting files for Dictionary {instance.id}: {e}")

GENERATED_FILE_FIELDS = (
    'html_file', 'opf_file', 'jpg_file', 'mobi_file', 'json_file', 'zip_file',
)


def _delete_replaced_generated_files(old_instance, instance, update_fields):
    """Delete generated files that this save replaces with newer ones.

    A rebuild stores fresh files under new names (the storage adds a random
    suffix because the previous file still exists), so without this every
    rebuild leaves the previous build behind on disk.
    """
    for field in GENERATED_FILE_FIELDS:
        if update_fields is not None and field not in update_fields:
            continue
        old_file = getattr(old_instance, field)
        new_file = getattr(instance, field)
        if not old_file or not new_file or old_file.name == new_file.name:
            continue
        # Only delete once the replacement is on disk, so saving a stale
        # in-memory instance can never wipe out the current build.
        if not new_file.storage.exists(new_file.name):
            continue
        if old_file.storage.exists(old_file.name):
            old_file.storage.delete(old_file.name)
            logger.info(f"Deleted replaced {field} for Dictionary {instance.pk}: {old_file.name}")


@receiver(pre_save, sender=Dictionary)
def auto_delete_files_on_change(sender, instance, update_fields=None, **kwargs):
    """
    Delete old files from filesystem when Dictionary instance is updated
    with new files.
    """
    # Skip for new instances (the UUID pk is already set before the first save)
    if instance._state.adding or not instance.pk:
        return

    try:
        # Get old instance
        old_instance = Dictionary.objects.get(pk=instance.pk)
        
        # Delete source file if changed
        if old_instance.source_file and instance.source_file and old_instance.source_file != instance.source_file:
            if os.path.isfile(old_instance.source_file.path):
                os.remove(old_instance.source_file.path)
        
        # Delete generated files if source file changed
        if old_instance.source_file != instance.source_file:
            # HTML file
            if old_instance.html_file and os.path.isfile(old_instance.html_file.path):
                os.remove(old_instance.html_file.path)
                instance.html_file = None
            
            # OPF file
            if old_instance.opf_file and os.path.isfile(old_instance.opf_file.path):
                os.remove(old_instance.opf_file.path)
                instance.opf_file = None
            
            # JPG file
            if old_instance.jpg_file and os.path.isfile(old_instance.jpg_file.path):
                os.remove(old_instance.jpg_file.path)
                instance.jpg_file = None
            
            # MOBI file
            if old_instance.mobi_file and os.path.isfile(old_instance.mobi_file.path):
                os.remove(old_instance.mobi_file.path)
                instance.mobi_file = None
            
            # JSON file
            if old_instance.json_file and os.path.isfile(old_instance.json_file.path):
                os.remove(old_instance.json_file.path)
                instance.json_file = None
            
            # ZIP file
            if old_instance.zip_file and os.path.isfile(old_instance.zip_file.path):
                os.remove(old_instance.zip_file.path)
                instance.zip_file = None

        # Same source, new build: drop the files this build replaces
        _delete_replaced_generated_files(old_instance, instance, update_fields)

    except Exception as e:
        logger.error(f"Error handling file changes for Dictionary {instance.id}: {e}")

@receiver(post_save, sender=Dictionary)
def dictionary_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for Dictionary model post_save event.
    Sends email notification when dictionary is completed.
    """
    # Check if the dictionary is completed
    if instance.status == 'completed':
        # Sprawdź, czy słownik jest powiązany z zadaniem
        tasks = Task.objects.filter(
            task_type='dictionary_suggestion',
            related_dictionary=instance
        )
        
        # Jeśli słownik jest powiązany z zadaniem, nie wysyłaj dodatkowego powiadomienia
        # ponieważ powiadomienie zostanie wysłane przez task_update_status
        if not tasks.exists():
            # Send email notification tylko jeśli słownik nie jest powiązany z zadaniem
            send_dictionary_completion_email(instance)
        
        # Update related tasks if any
        for task in tasks:
            if task.status != 'completed':
                task.mark_as_completed()

@receiver(post_save, sender=DictionarySuggestion)
def dictionary_suggestion_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for DictionarySuggestion model post_save event.
    Creates a task for new dictionary suggestions.
    """
    # Only create a task for new suggestions
    if created:
        # Create a task for this suggestion
        instance.create_task()
        
        # Nie wysyłamy powiadomienia tutaj, ponieważ jest już wysyłane w widoku DictionarySuggestionCreateView
