# src/dictionary/tasks.py

"""
Celery tasks for the Dictionary app.
"""

import os
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task
def process_dictionary(dictionary_id):
    """
    Process a dictionary to generate all necessary files.
    """
    # Import here to avoid circular imports
    from .models import Dictionary
    from .dictionary_creator import create_dictionary_files
    
    logger.info(f"Starting to process dictionary: {dictionary_id}")
    
    try:
        # Get the dictionary object
        dictionary = Dictionary.objects.get(pk=dictionary_id)
        
        # Update status to processing
        dictionary.status = 'processing'
        dictionary.save(update_fields=['status', 'updated_at'])
        
        # Process the dictionary
        success = create_dictionary_files(dictionary)
        
        if success:
            # Update dictionary status to completed
            dictionary.status = 'completed'
            dictionary.built_at = timezone.now()
            dictionary.save(update_fields=['status', 'built_at', 'updated_at'])
            
            logger.info(f"Successfully processed dictionary: {dictionary_id}")
            return True
        else:
            logger.error(f"Failed to process dictionary: {dictionary_id}")
            return False
        
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