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
        widget=forms.Textarea(attrs={'rows': 15}),
        required=False,
        label=_("Dictionary Content"),
        help_text=_("Paste dictionary entries here, or upload a file below.")
    )
    
    # Add validators to ensure only .txt files are uploaded
    source_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        label=_("Source File"),
        help_text=_("Upload a .txt file with dictionary entries.")
    )
    
    class Meta:
        model = Dictionary
        fields = ['name', 'description', 'creator_name', 'language_code', 'is_public', 'source_file']
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        source_file = cleaned_data.get("source_file")
        
        # Either content or source_file must be provided
        if not content and not source_file:
            raise forms.ValidationError(_("You must either provide content or upload a file."))
        
        return cleaned_data

class DictionarySuggestionForm(forms.ModelForm):
    """Form for submitting a dictionary suggestion"""
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 15}),
        required=False,
        label=_("Dictionary Content"),
        help_text=_("Paste dictionary entries here, or upload a file below.")
    )
    
    source_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        label=_("Source File"),
        help_text=_("Upload a .txt file with dictionary entries.")
    )
    
    class Meta:
        model = DictionarySuggestion
        fields = ['name', 'description', 'email', 'content', 'source_file']
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        source_file = cleaned_data.get("source_file")
        
        # Either content or source_file must be provided
        if not content and not source_file:
            raise forms.ValidationError(_("You must either provide content or upload a file."))
        
        return cleaned_data