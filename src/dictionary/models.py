# kindle_dict\src\dictionary\models.py

"""
Models for the Dictionary app.
"""

import os
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings

def dictionary_file_path(instance, filename):
    """Generate file path for dictionary files"""
    # Generate a path based on dictionary name and file type
    ext = filename.split('.')[-1]
    filename = f"{instance.name}.{ext}"
    return os.path.join('dictionaries', str(instance.id), filename)

class Dictionary(models.Model):
    """Model to store dictionary data"""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID")
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Name")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    language_code = models.CharField(
        max_length=10,
        default='pl',
        verbose_name=_("Language Code")
    )
    creator_name = models.CharField(
        max_length=255,
        verbose_name=_("Creator Name")
    )
    build_version = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Build Version")
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name=_("Public")
    )
    
    # Files
    source_file = models.FileField(
        upload_to=dictionary_file_path,
        verbose_name=_("Source File")
    )
    html_file = models.FileField(
        upload_to=dictionary_file_path,
        null=True,
        blank=True,
        verbose_name=_("HTML File")
    )
    opf_file = models.FileField(
        upload_to=dictionary_file_path,
        null=True,
        blank=True,
        verbose_name=_("OPF File")
    )
    jpg_file = models.FileField(
        upload_to=dictionary_file_path,
        null=True,
        blank=True,
        verbose_name=_("Cover Image")
    )
    mobi_file = models.FileField(
        upload_to=dictionary_file_path,
        null=True,
        blank=True,
        verbose_name=_("MOBI File")
    )
    json_file = models.FileField(
        upload_to=dictionary_file_path,
        null=True,
        blank=True,
        verbose_name=_("JSON Metadata")
    )
    zip_file = models.FileField(
        upload_to=dictionary_file_path,
        null=True,
        blank=True,
        verbose_name=_("ZIP Package")
    )
    
    # Status and dates
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Status")
    )
    status_message = models.TextField(
        blank=True,
        verbose_name=_("Status Message")
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )
    built_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Built At")
    )
    
    class Meta:
        verbose_name = _("Dictionary")
        verbose_name_plural = _("Dictionaries")
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
    
    def increment_build_version(self):
        """Increment the build version of the dictionary"""
        self.build_version += 1
        self.save(update_fields=['build_version', 'updated_at'])

class DictionarySuggestion(models.Model):
    """Model for dictionary suggestions from anonymous users"""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID")
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Name")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    content = models.TextField(
        blank=True,
        verbose_name=_("Dictionary Content")
    )
    source_file = models.FileField(
        upload_to='suggestions/',
        null=True,
        blank=True,
        verbose_name=_("Source File")
    )
    
    # Contact info
    email = models.EmailField(
        blank=True,
        verbose_name=_("Email")
    )
    
    # Status and dates
    STATUS_CHOICES = (
        ('pending', _('Pending Review')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Status")
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Created At")
    )
    
    class Meta:
        verbose_name = _("Dictionary Suggestion")
        verbose_name_plural = _("Dictionary Suggestions")
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name