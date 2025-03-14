"""
Celery tasks for the Dictionary app.
"""

import os
import tempfile
import shutil
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task
def process_dictionary(dictionary_id):
    """
    Process a dictionary to generate all necessary files.
    
    This is a placeholder for now - we'll implement the actual conversion logic
    based on createdict.py in the next phase.
    """
    # Import here to avoid circular imports
    from .models import Dictionary
    
    logger.info(f"Starting to process dictionary: {dictionary_id}")
    
    try:
        # Get the dictionary object
        dictionary = Dictionary.objects.get(pk=dictionary_id)
        
        # Update status to processing
        dictionary.status = 'processing'
        dictionary.save(update_fields=['status', 'updated_at'])
        
        # Get the source file path
        source_file_path = dictionary.source_file.path
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # TODO: Implement the actual conversion logic using createdict.py
            # For now, just log that we would process the file
            logger.info(f"Would process file {source_file_path} in directory {temp_dir}")
            
            # In the next phase, we'll implement:
            # 1. Call the adapted createdict.py functions
            # 2. Generate HTML, OPF, JPG, MOBI, JSON files
            # 3. Save these files to the Dictionary model
            # 4. Create a ZIP archive of all files
            
            # Mock a small delay to simulate processing
            import time
            time.sleep(5)
            
            # Update dictionary status to completed
            dictionary.status = 'completed'
            dictionary.built_at = timezone.now()
            dictionary.save(update_fields=['status', 'built_at', 'updated_at'])
            
        logger.info(f"Successfully processed dictionary: {dictionary_id}")
        return True
        
    except Dictionary.DoesNotExist:
        logger.error(f"Dictionary not found: {dictionary_id}")
        return False
    except Exception as e:
        logger.error(f"Error processing dictionary {dictionary_id}: {str(e)}")
        
        # Try to update the dictionary status to failed
        try:
            dictionary = Dictionary.objects.get(pk=dictionary_id)
            dictionary.status = 'failed'
            dictionary.status_message = str(e)
            dictionary.save(update_fields=['status', 'status_message', 'updated_at'])
        except:
            pass
            
        return False