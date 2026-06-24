# kindle_dict\src\dictionary\forms.py

"""
Forms for the Dictionary app.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from .models import Dictionary, DictionarySuggestion, SMTPConfiguration, ContactMessage, CaptchaConfiguration, Task
from django.core.validators import FileExtensionValidator


APPROVABLE_GROUP_NAMES = ['Dictionary Creator', 'Dictionary Edit', 'Dictionary Admin']

class DictionaryForm(forms.ModelForm):
    """Form for uploading a new dictionary"""
    
    # You can also provide content via textarea instead of a file
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 15, 'class': 'form-control'}),
        required=False,
        label=_("Zawartość słownika"),
        help_text=_("Wklej tutaj wpisy słownika lub prześlij plik poniżej.")
    )
    
    # Add validators to ensure only .txt files are uploaded
    source_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        label=_("Plik źródłowy"),
        help_text=_("Prześlij plik .txt z wpisami słownika."),
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Dictionary
        fields = ['name', 'description', 'creator_name', 'notification_email', 'language_code', 'is_public', 'source_file']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'creator_name': forms.TextInput(attrs={'class': 'form-control'}),
            'notification_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'language_code': forms.TextInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': _('Nazwa'),
            'description': _('Opis'),
            'creator_name': _('Autor słownika'),
            'notification_email': _('Adres e-mail do powiadomień'),
            'language_code': _('Kod języka'),
            'is_public': _('Publiczny'),
        }
        help_texts = {
            'notification_email': _('Opcjonalny adres e-mail, na który zostanie wysłane powiadomienie o utworzeniu słownika.'),
            'language_code': _('Np. pl dla polskiego, en dla angielskiego.'),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        source_file = cleaned_data.get("source_file")
        
        # Either content or source_file must be provided
        if not content and not source_file:
            raise forms.ValidationError(_("Musisz albo podać zawartość, albo przesłać plik."))
        
        return cleaned_data


class ContactMessageForm(forms.ModelForm):
    """Form for contact messages"""
    
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Twoje imię (opcjonalnie)')}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Twój adres e-mail (opcjonalnie)')}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': _('Twoja wiadomość')}),
        }
        labels = {
            'name': _('Imię i nazwisko'),
            'email': _('Adres e-mail'),
            'message': _('Wiadomość'),
        }
        help_texts = {
            'email': _('Opcjonalny adres e-mail, który zostanie użyty jako Reply-to w powiadomieniu.'),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        message = cleaned_data.get("message")
        
        # Message is required
        if not message or not message.strip():
            raise forms.ValidationError(_("Wiadomość jest wymagana."))
        
        return cleaned_data

class SMTPConfigurationForm(forms.ModelForm):
    """Form for configuring SMTP settings"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        label=_("Hasło SMTP"),
        help_text=_("Hasło do konta SMTP.")
    )
    
    test_email = forms.EmailField(
        required=False,
        label=_("Adres e-mail do testu"),
        help_text=_("Adres e-mail, na który zostanie wysłana testowa wiadomość."),
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = SMTPConfiguration
        fields = [
            'host', 'port', 'encryption', 'auto_tls', 'authentication',
            'username', 'password', 'from_email', 'from_name'
        ]
        widgets = {
            'host': forms.TextInput(attrs={'class': 'form-control'}),
            'port': forms.NumberInput(attrs={'class': 'form-control'}),
            'encryption': forms.RadioSelect(),
            'auto_tls': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'authentication': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'from_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'from_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'host': _('Adres serwera SMTP, np. smtp.gmail.com'),
            'port': _('Port serwera SMTP, np. 587 dla TLS, 465 dla SSL, 25 dla braku szyfrowania'),
            'encryption': _('Rodzaj szyfrowania używany przez serwer SMTP'),
            'auto_tls': _('Automatycznie używaj TLS, jeśli serwer go obsługuje'),
            'authentication': _('Czy serwer SMTP wymaga uwierzytelniania'),
            'username': _('Nazwa użytkownika do konta SMTP'),
            'from_email': _('Adres e-mail, z którego będą wysyłane wiadomości'),
            'from_name': _('Nazwa nadawcy, która będzie wyświetlana w wiadomościach e-mail'),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        authentication = cleaned_data.get('authentication')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        # If authentication is enabled, username and password are required
        if authentication:
            if not username:
                self.add_error('username', _('Nazwa użytkownika jest wymagana przy włączonym uwierzytelnianiu.'))
            
            # Sprawdź, czy to jest edycja istniejącej konfiguracji
            instance = getattr(self, 'instance', None)
            
            # Jeśli to edycja istniejącej konfiguracji i hasło jest puste,
            # nie wymagaj hasła - zostanie zachowane poprzednie
            if not password and not (instance and instance.pk):
                self.add_error('password', _('Hasło jest wymagane przy włączonym uwierzytelnianiu.'))
        
        return cleaned_data


class CaptchaConfigurationForm(forms.ModelForm):
    """Form for configuring CAPTCHA settings"""
    
    secret_key = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        label=_("Klucz tajny (Secret Key)"),
        help_text=_("Klucz tajny używany do weryfikacji odpowiedzi CAPTCHA.")
    )
    
    class Meta:
        model = CaptchaConfiguration
        fields = [
            'provider', 'site_key', 'secret_key', 'is_enabled',
            'enable_login', 'enable_contact', 'enable_suggest'
        ]
        widgets = {
            'provider': forms.RadioSelect(),
            'site_key': forms.TextInput(attrs={'class': 'form-control'}),
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_login': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_contact': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_suggest': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'provider': _('Wybierz dostawcę usługi CAPTCHA.'),
            'site_key': _('Klucz witryny (Site Key) używany do wyświetlania CAPTCHA na stronie.'),
            'is_enabled': _('Włącz lub wyłącz CAPTCHA globalnie.'),
            'enable_login': _('Włącz CAPTCHA na stronie logowania.'),
            'enable_contact': _('Włącz CAPTCHA w formularzu kontaktowym.'),
            'enable_suggest': _('Włącz CAPTCHA w formularzu propozycji słownika.'),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Sprawdź, czy to jest edycja istniejącej konfiguracji
        instance = getattr(self, 'instance', None)
        secret_key = cleaned_data.get('secret_key')
        
        # Jeśli to edycja istniejącej konfiguracji i klucz tajny jest pusty,
        # zachowaj poprzedni klucz
        if not secret_key and instance and instance.pk:
            # Pobierz aktualny klucz tajny z bazy danych
            current_config = CaptchaConfiguration.objects.get(pk=instance.pk)
            cleaned_data['secret_key'] = current_config.secret_key
        
        return cleaned_data

class DictionaryUpdateForm(forms.ModelForm):
    """Form for updating an existing dictionary"""
    
    # You can also provide content via textarea instead of a file
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 15, 'class': 'form-control'}),
        required=False,
        label=_("Zawartość słownika"),
        help_text=_("Wklej tutaj wpisy słownika lub prześlij plik poniżej.")
    )
    
    # Add validators to ensure only .txt files are uploaded
    source_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        label=_("Plik źródłowy"),
        help_text=_("Prześlij plik .txt z wpisami słownika."),
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Dictionary
        fields = ['name', 'description', 'creator_name', 'updater_name', 'notification_email', 'language_code', 'is_public', 'source_file']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'creator_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'updater_name': forms.TextInput(attrs={'class': 'form-control'}),
            'notification_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'language_code': forms.TextInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': _('Nazwa'),
            'description': _('Opis'),
            'creator_name': _('Autor słownika'),
            'updater_name': _('Autor modyfikacji'),
            'notification_email': _('Adres e-mail do powiadomień'),
            'language_code': _('Kod języka'),
            'is_public': _('Publiczny'),
        }
        help_texts = {
            'creator_name': _('Autor oryginalnego słownika (tylko do odczytu).'),
            'updater_name': _('Osoba, która dokonała ostatniej modyfikacji słownika.'),
            'notification_email': _('Opcjonalny adres e-mail, na który zostanie wysłane powiadomienie o aktualizacji słownika.'),
            'language_code': _('Np. pl dla polskiego, en dla angielskiego.'),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        source_file = cleaned_data.get("source_file")
        
        # Either content or source_file must be provided
        if not content and not source_file:
            raise forms.ValidationError(_("Musisz albo podać zawartość, albo przesłać plik."))
        
        return cleaned_data


class TaskForm(forms.ModelForm):
    """Form for creating or updating a task"""
    
    class Meta:
        model = Task
        fields = ['title', 'description', 'task_type', 'status', 'email', 'content', 'source_file', 'assigned_to']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'task_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'source_file': forms.FileInput(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': _('Tytuł'),
            'description': _('Opis'),
            'task_type': _('Typ zadania'),
            'status': _('Status'),
            'email': _('Email zgłaszającego'),
            'content': _('Zawartość'),
            'source_file': _('Plik źródłowy'),
            'assigned_to': _('Przypisane do'),
        }


class TaskStatusForm(forms.ModelForm):
    """Form for updating task status"""
    
    class Meta:
        model = Task
        fields = ['status', 'assigned_to', 'rejection_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'status': _('Status'),
            'assigned_to': _('Przypisane do'),
            'rejection_reason': _('Powód odrzucenia'),
        }
        help_texts = {
            'rejection_reason': _('Wymagane przy odrzuceniu zadania. Powód zostanie wysłany do zgłaszającego.'),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        # Jeśli status to "odrzucone", powód odrzucenia jest wymagany
        if status == 'rejected' and not rejection_reason:
            self.add_error('rejection_reason', _('Powód odrzucenia jest wymagany przy odrzucaniu zadania.'))
        
        return cleaned_data


class DictionarySuggestionForm(forms.ModelForm):
    """Form for submitting a dictionary suggestion"""
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 15, 'class': 'form-control'}),
        required=False,
        label=_("Zawartość słownika"),
        help_text=_("Wklej tutaj wpisy słownika lub prześlij plik poniżej.")
    )
    
    source_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        label=_("Plik źródłowy"),
        help_text=_("Prześlij plik .txt z wpisami słownika."),
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = DictionarySuggestion
        fields = ['name', 'description', 'author_name', 'email', 'content', 'source_file']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'author_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': _('Nazwa'),
            'description': _('Opis'),
            'author_name': _('Autor słownika'),
            'email': _('Adres e-mail'),
        }
        help_texts = {
            'author_name': _('Opcjonalne pole. Jeśli nie zostanie wypełnione, autor zostanie oznaczony jako "Nieznany".'),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        source_file = cleaned_data.get("source_file")
        
        # Either content or source_file must be provided
        if not content and not source_file:
            raise forms.ValidationError(_("Musisz albo podać zawartość, albo przesłać plik."))
        
        return cleaned_data


class DictionaryChangeForm(forms.Form):
    """Form for submitting a dictionary change proposal"""
    
    author_name = forms.CharField(
        max_length=255,
        required=False,
        label=_("Autor modyfikacji"),
        help_text=_("Opcjonalne pole. Jeśli nie zostanie wypełnione, autor zostanie oznaczony jako \"Nieznany\"."),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    email = forms.EmailField(
        required=False,
        label=_("Adres e-mail"),
        help_text=_("Opcjonalny adres e-mail, na który zostanie wysłane powiadomienie o akceptacji lub odrzuceniu propozycji."),
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    description = forms.CharField(
        required=False,
        label=_("Opis zmian"),
        help_text=_("Opcjonalny opis wprowadzonych zmian."),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5})
    )
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 15, 'class': 'form-control'}),
        required=False,
        label=_("Zawartość słownika"),
        help_text=_("Wklej tutaj wpisy słownika lub prześlij plik poniżej.")
    )
    
    source_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        label=_("Plik źródłowy"),
        help_text=_("Prześlij plik .txt z wpisami słownika."),
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        source_file = cleaned_data.get("source_file")
        
        # Either content or source_file must be provided
        if not content and not source_file:
            raise forms.ValidationError(_("Musisz albo podać zawartość, albo przesłać plik."))
        
        return cleaned_data


class UserSettingsForm(forms.ModelForm):
    """Form for user settings"""

    class Meta:
        from .models import UserSettings
        model = UserSettings
        fields = ['email_dictionary_notifications', 'email_task_notifications']
        widgets = {
            'email_dictionary_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_task_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UserRegistrationForm(UserCreationForm):
    """Self-registration form. Extends Django's UserCreationForm with
    required first_name/last_name/email and email uniqueness validation."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label=_("Imię"),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label=_("Nazwisko"),
    )
    email = forms.EmailField(
        required=True,
        label=_("Adres e-mail"),
        help_text=_("Na ten adres wyślemy link aktywacyjny."),
    )

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css_class = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' ' + css_class).strip()

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Konto z tym adresem e-mail już istnieje."))
        return email


class EmailOTPForm(forms.Form):
    """Six-digit one-time code used by email-based 2FA."""

    code = forms.CharField(
        label=_("Kod jednorazowy"),
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'inputmode': 'numeric',
            'pattern': '[0-9]{6}',
            'autocomplete': 'one-time-code',
            'autofocus': 'autofocus',
        }),
    )

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip()
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError(_("Kod musi się składać z 6 cyfr."))
        return code


class ProfileEditForm(forms.ModelForm):
    """Lets a logged-in user edit their first/last name and email."""

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email')
        labels = {
            'first_name': _("Imię"),
            'last_name': _("Nazwisko"),
            'email': _("Adres e-mail"),
        }
        help_texts = {
            'email': _("Zmiana adresu wymaga ponownego potwierdzenia — wyślemy nowy link aktywacyjny."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' form-control').strip()

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            raise forms.ValidationError(_("Adres e-mail jest wymagany."))
        qs = get_user_model().objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Konto z tym adresem e-mail już istnieje."))
        return email


class UserApprovalForm(forms.Form):
    """Pick which app groups a freshly verified user should land in."""

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Przyznane role"),
        help_text=_("Bez zaznaczenia żadnej roli użytkownik zalogowany ma dostęp tylko do propozycji słowników i kontaktu (jak anonim)."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['groups'].queryset = Group.objects.filter(
            name__in=APPROVABLE_GROUP_NAMES
        ).order_by('name')


class UserRejectionForm(forms.Form):
    """Optional rejection reason — included in the rejection email."""

    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label=_("Powód odrzucenia (opcjonalnie)"),
        help_text=_("Treść zostanie dołączona do e-maila informującego użytkownika o odrzuceniu konta."),
    )
