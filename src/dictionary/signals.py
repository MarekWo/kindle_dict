# src\dictionary\signals.py

"""
Signal handlers for the Dictionary app.
"""

import os
import logging
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Dictionary

logger = logging.getLogger(__name__)

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

@receiver(pre_save, sender=Dictionary)
def auto_delete_files_on_change(sender, instance, **kwargs):
    """
    Delete old files from filesystem when Dictionary instance is updated
    with new files.
    """
    # Skip for new instances
    if not instance.pk:
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
    
    except Exception as e:
        logger.error(f"Error handling file changes for Dictionary {instance.id}: {e}")