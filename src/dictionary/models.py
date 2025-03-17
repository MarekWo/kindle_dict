# kindle_dict\src\dictionary\models.py

"""
Models for the Dictionary app.
"""

import os
import uuid
from django.core.exceptions import ValidationError
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
    updater_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Updater Name")
    )
    notification_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name=_("Adres e-mail do powiadomień"),
        help_text=_("Opcjonalny adres e-mail, na który zostanie wysłane powiadomienie o utworzeniu słownika.")
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

class SMTPConfiguration(models.Model):
    """Model to store SMTP configuration for email sending"""
    
    ENCRYPTION_CHOICES = (
        ('none', _('Brak')),
        ('ssl', _('SSL')),
        ('tls', _('TLS')),
    )
    
    host = models.CharField(
        max_length=255,
        verbose_name=_("Host SMTP")
    )
    port = models.PositiveIntegerField(
        default=25,
        verbose_name=_("Port SMTP")
    )
    encryption = models.CharField(
        max_length=10,
        choices=ENCRYPTION_CHOICES,
        default='tls',
        verbose_name=_("Szyfrowanie")
    )
    auto_tls = models.BooleanField(
        default=True,
        verbose_name=_("Auto TLS")
    )
    authentication = models.BooleanField(
        default=True,
        verbose_name=_("Uwierzytelnianie")
    )
    username = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Nazwa użytkownika SMTP")
    )
    password = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Hasło SMTP")
    )
    from_email = models.EmailField(
        verbose_name=_("Zwrotny Adres e-mail")
    )
    from_name = models.CharField(
        max_length=255,
        verbose_name=_("Nazwa nadawcy")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Utworzono")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Zaktualizowano")
    )
    
    class Meta:
        verbose_name = _("Konfiguracja SMTP")
        verbose_name_plural = _("Konfiguracje SMTP")
    
    def __str__(self):
        return f"{self.from_name} <{self.from_email}> ({self.host})"
    
    def clean(self):
        """Validate that only one configuration exists"""
        if not self.pk and SMTPConfiguration.objects.exists():
            raise ValidationError(_("Może istnieć tylko jedna konfiguracja SMTP."))
        
        # Validate that username and password are provided if authentication is enabled
        # Tylko jeśli obiekt jest już zapisany w bazie danych (ma pk) lub jest zapisywany (ma host i from_email)
        if self.authentication and self.host and self.from_email:
            if not self.username:
                raise ValidationError({'username': _("Nazwa użytkownika jest wymagana przy włączonym uwierzytelnianiu.")})
            
            # Jeśli to nowy obiekt (nie ma pk) lub hasło jest puste i nie ma poprzedniego hasła w bazie danych
            if not self.password:
                # Jeśli to edycja istniejącego obiektu, sprawdź czy istnieje poprzednie hasło
                if self.pk:
                    try:
                        current_config = SMTPConfiguration.objects.get(pk=self.pk)
                        if not current_config.password:
                            raise ValidationError({'password': _("Hasło jest wymagane przy włączonym uwierzytelnianiu.")})
                    except SMTPConfiguration.DoesNotExist:
                        raise ValidationError({'password': _("Hasło jest wymagane przy włączonym uwierzytelnianiu.")})
                else:
                    # To nowy obiekt, więc hasło jest wymagane
                    raise ValidationError({'password': _("Hasło jest wymagane przy włączonym uwierzytelnianiu.")})
        
        return super().clean()
    
    def save(self, *args, **kwargs):
        """Ensure only one configuration exists"""
        self.full_clean()
        super().save(*args, **kwargs)

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
