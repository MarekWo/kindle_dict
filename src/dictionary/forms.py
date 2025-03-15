# kindle_dict\src\dictionary\forms.py

"""
Forms for the Dictionary app.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Dictionary, DictionarySuggestion
from django.core.validators import FileExtensionValidator

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
        fields = ['name', 'description', 'creator_name', 'language_code', 'is_public', 'source_file']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'creator_name': forms.TextInput(attrs={'class': 'form-control'}),
            'language_code': forms.TextInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': _('Nazwa'),
            'description': _('Opis'),
            'creator_name': _('Nazwa twórcy'),
            'language_code': _('Kod języka'),
            'is_public': _('Publiczny'),
        }
        help_texts = {
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
        fields = ['name', 'description', 'email', 'content', 'source_file']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': _('Nazwa'),
            'description': _('Opis'),
            'email': _('Adres e-mail'),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        source_file = cleaned_data.get("source_file")
        
        # Either content or source_file must be provided
        if not content and not source_file:
            raise forms.ValidationError(_("Musisz albo podać zawartość, albo przesłać plik."))
        
        return cleaned_data