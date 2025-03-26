# kindle_dict\src\dictionary\models.py

"""
Models for the Dictionary app.
"""

import os
import uuid
from django.contrib.auth import get_user_model
# kindle_dict\src\dictionary\models.py

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

class CaptchaConfiguration(models.Model):
    """Model to store CAPTCHA configuration"""
    
    PROVIDER_CHOICES = (
        ('cloudflare', _('Cloudflare Turnstile')),
        ('google', _('Google reCAPTCHA')),
    )
    
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='cloudflare',
        verbose_name=_("Dostawca CAPTCHA")
    )
    site_key = models.CharField(
        max_length=255,
        verbose_name=_("Klucz witryny (Site Key)")
    )
    secret_key = models.CharField(
        max_length=255,
        verbose_name=_("Klucz tajny (Secret Key)")
    )
    is_enabled = models.BooleanField(
        default=True,
        verbose_name=_("Włączone")
    )
    enable_login = models.BooleanField(
        default=True,
        verbose_name=_("Włącz dla logowania")
    )
    enable_contact = models.BooleanField(
        default=True,
        verbose_name=_("Włącz dla formularza kontaktowego")
    )
    enable_suggest = models.BooleanField(
        default=True,
        verbose_name=_("Włącz dla formularza propozycji słownika")
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
        verbose_name = _("Konfiguracja CAPTCHA")
        verbose_name_plural = _("Konfiguracje CAPTCHA")
    
    def __str__(self):
        return f"{self.get_provider_display()} ({self.site_key})"
    
    def clean(self):
        """Validate that only one configuration exists"""
        if not self.pk and CaptchaConfiguration.objects.exists():
            raise ValidationError(_("Może istnieć tylko jedna konfiguracja CAPTCHA."))
        return super().clean()
    
    def save(self, *args, **kwargs):
        """Ensure only one configuration exists"""
        self.full_clean()
        super().save(*args, **kwargs)


class ContactMessage(models.Model):
    """Model for contact messages from users"""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID")
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Imię i nazwisko")
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_("Adres e-mail"),
        help_text=_("Opcjonalny adres e-mail, który zostanie użyty jako Reply-to w powiadomieniu.")
    )
    message = models.TextField(
        verbose_name=_("Wiadomość")
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Data utworzenia")
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_("Przeczytana")
    )
    
    class Meta:
        verbose_name = _("Wiadomość kontaktowa")
        verbose_name_plural = _("Wiadomości kontaktowe")
        ordering = ['-created_at']
    
    def __str__(self):
        if self.name:
            return f"{self.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        return f"Wiadomość - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class Task(models.Model):
    """Model for tasks in the system"""
    
    TASK_TYPE_CHOICES = (
        ('dictionary_suggestion', _('Sugestia słownika')),
        ('dictionary_change', _('Propozycja zmian w słowniku')),
        # W przyszłości można dodać więcej typów zadań
    )
    
    STATUS_CHOICES = (
        ('new', _('Nowe')),
        ('accepted', _('Zaakceptowane')),
        ('rejected', _('Odrzucone')),
        ('completed', _('Zrealizowane')),
    )
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID")
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Tytuł")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Opis")
    )
    task_type = models.CharField(
        max_length=50,
        choices=TASK_TYPE_CHOICES,
        default='dictionary_suggestion',
        verbose_name=_("Typ zadania")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name=_("Status")
    )
    
    # Pola dla zadań typu 'dictionary_suggestion' i 'dictionary_change'
    content = models.TextField(
        blank=True,
        verbose_name=_("Zawartość słownika")
    )
    source_file = models.FileField(
        upload_to='tasks/suggestions/',
        null=True,
        blank=True,
        verbose_name=_("Plik źródłowy")
    )
    author_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Autor słownika")
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_("Powód odrzucenia")
    )
    
    # Pola dla zadań typu 'dictionary_change'
    original_content = models.TextField(
        blank=True,
        verbose_name=_("Oryginalna zawartość słownika")
    )
    
    # Pola dla powiadomień
    email = models.EmailField(
        blank=True,
        verbose_name=_("Email zgłaszającego")
    )
    
    # Pola dla śledzenia
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Data utworzenia")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Data aktualizacji")
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Data realizacji")
    )
    
    # Powiązania
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
        verbose_name=_("Utworzone przez")
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name=_("Przypisane do")
    )
    
    # Powiązanie z utworzonym słownikiem (dla zadań typu 'dictionary_suggestion')
    related_dictionary = models.ForeignKey(
        'Dictionary',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_tasks',
        verbose_name=_("Powiązany słownik")
    )
    
    class Meta:
        verbose_name = _("Zadanie")
        verbose_name_plural = _("Zadania")
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def is_archived(self):
        """Sprawdza, czy zadanie jest w archiwum (zrealizowane lub odrzucone)"""
        return self.status in ['completed', 'rejected']
    
    def is_pending(self):
        """Sprawdza, czy zadanie oczekuje na realizację (zaakceptowane)"""
        return self.status == 'accepted'
    
    def is_new(self):
        """Sprawdza, czy zadanie jest nowe"""
        return self.status == 'new'
    
    def mark_as_accepted(self, user=None):
        """Oznacza zadanie jako zaakceptowane"""
        self.status = 'accepted'
        if user:
            self.assigned_to = user
        self.save()
    
    def mark_as_rejected(self):
        """Oznacza zadanie jako odrzucone"""
        self.status = 'rejected'
        self.save()
    
    def mark_as_completed(self, dictionary=None):
        """Oznacza zadanie jako zrealizowane"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if dictionary:
            self.related_dictionary = dictionary
        self.save()


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
    author_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Autor słownika")
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
    
    # Powiązanie z zadaniem
    task = models.OneToOneField(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dictionary_suggestion',
        verbose_name=_("Powiązane zadanie")
    )
    
    class Meta:
        verbose_name = _("Dictionary Suggestion")
        verbose_name_plural = _("Dictionary Suggestions")
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def create_task(self):
        """Tworzy zadanie na podstawie sugestii słownika"""
        if not self.task:
            task = Task.objects.create(
                title=f"Sugestia słownika: {self.name}",
                description=self.description,
                task_type='dictionary_suggestion',
                content=self.content,
                email=self.email,
                author_name=self.author_name,
                status='new'
            )
            
            # Jeśli istnieje plik źródłowy, skopiuj go do zadania
            if self.source_file:
                from django.core.files.base import ContentFile
                task.source_file.save(
                    self.source_file.name,
                    ContentFile(self.source_file.read()),
                    save=True
                )
            
            self.task = task
            self.save()
            
            return task
        
        return self.task


class UserSettings(models.Model):
    """Model for user settings"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='settings',
        verbose_name=_("Użytkownik")
    )
    
    # Ustawienia powiadomień email
    email_dictionary_notifications = models.BooleanField(
        default=True,
        verbose_name=_("Powiadomienia o utworzeniu słownika"),
        help_text=_("Otrzymuj powiadomienia email o utworzeniu słownika.")
    )
    email_task_notifications = models.BooleanField(
        default=True,
        verbose_name=_("Powiadomienia o nowych zadaniach"),
        help_text=_("Otrzymuj powiadomienia email o nowych zadaniach i zmianach statusu zadań.")
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Data utworzenia")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Data aktualizacji")
    )
    
    class Meta:
        verbose_name = _("Ustawienia użytkownika")
        verbose_name_plural = _("Ustawienia użytkowników")
    
    def __str__(self):
        return f"Ustawienia użytkownika: {self.user.username}"
    
    @classmethod
    def get_for_user(cls, user):
        """Get or create settings for user"""
        settings, created = cls.objects.get_or_create(user=user)
        return settings
