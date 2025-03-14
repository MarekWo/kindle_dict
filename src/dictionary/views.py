# kindle_dict\src\dictionary\views.py

"""
Views for the Dictionary app.
"""

import os
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import FileResponse, Http404
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings

from .models import Dictionary, DictionarySuggestion
from .forms import DictionaryForm, DictionarySuggestionForm
from .tasks import process_dictionary

class DictionaryListView(ListView):
    """View to display a list of public dictionaries"""
    model = Dictionary
    template_name = 'dictionary/list.html'
    context_object_name = 'dictionaries'
    
    def get_queryset(self):
        """Filter to show only public dictionaries"""
        return Dictionary.objects.filter(is_public=True, status='completed')

class DictionaryDetailView(DetailView):
    """View to display details of a dictionary"""
    model = Dictionary
    template_name = 'dictionary/detail.html'
    context_object_name = 'dictionary'
    
    def get_context_data(self, **kwargs):
        """Add additional data to context"""
        context = super().get_context_data(**kwargs)
        # Add any additional data here
        return context

class DictionaryCreateView(CreateView):
    """View to create a new dictionary"""
    model = Dictionary
    form_class = DictionaryForm
    template_name = 'dictionary/create.html'
    success_url = reverse_lazy('dictionary:list')
    
    def form_valid(self, form):
        """Process the form if it's valid"""
        # Save the dictionary instance first
        self.object = form.save(commit=False)
        
        # Handle content from textarea if provided
        content = form.cleaned_data.get('content')
        if content and not self.object.source_file:
            # Create a temporary file and save the content to it
            import tempfile
            import uuid
            
            # Create a temporary file with the content
            content_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
            content_file.write(content.encode('utf-8'))
            content_file.close()
            
            # Set the source_file field to this file
            from django.core.files import File
            with open(content_file.name, 'rb') as f:
                filename = f"{self.object.name}.txt"
                self.object.source_file.save(filename, File(f), save=False)
            
            # Clean up the temporary file
            os.unlink(content_file.name)
        
        # Set status and save the object
        self.object.status = 'pending'
        self.object.save()
        
        # Start the Celery task for processing the dictionary
        process_dictionary.delay(str(self.object.id))
        
        # Show success message
        messages.success(self.request, _("Dictionary submitted successfully and is being processed."))
        
        return redirect(self.get_success_url())

class DictionarySuggestionCreateView(CreateView):
    """View for anonymous users to submit dictionary suggestions"""
    model = DictionarySuggestion
    form_class = DictionarySuggestionForm
    template_name = 'dictionary/suggest.html'
    success_url = reverse_lazy('home')
    
    def form_valid(self, form):
        """Process the form if it's valid"""
        # Save the suggestion instance first
        self.object = form.save(commit=False)
        
        # Handle content from textarea if provided
        content = form.cleaned_data.get('content')
        if content and not self.object.source_file:
            # Store the content directly in the model field
            self.object.content = content
        
        # Set status and save the object
        self.object.status = 'pending'
        self.object.save()
        
        # Show success message
        messages.success(self.request, _("Thank you for your suggestion! It will be reviewed by our administrators."))
        
        return redirect(self.get_success_url())

def dictionary_download(request, pk, file_type):
    """View to download dictionary files"""
    # Get the dictionary object
    dictionary = get_object_or_404(Dictionary, pk=pk)
    
    # Check if the requested file exists
    file_field = None
    filename = None
    
    if file_type == 'source':
        file_field = dictionary.source_file
        filename = f"{dictionary.name}.txt"
    elif file_type == 'html':
        file_field = dictionary.html_file
        filename = f"{dictionary.name}.html"
    elif file_type == 'opf':
        file_field = dictionary.opf_file
        filename = f"{dictionary.name}.opf"
    elif file_type == 'jpg':
        file_field = dictionary.jpg_file
        filename = f"{dictionary.name}.jpg"
    elif file_type == 'mobi':
        file_field = dictionary.mobi_file
        filename = f"{dictionary.name}.mobi"
    elif file_type == 'json':
        file_field = dictionary.json_file
        filename = f"{dictionary.name}.json"
    elif file_type == 'zip':
        file_field = dictionary.zip_file
        filename = f"{dictionary.name}.zip"
    else:
        raise Http404(_("File not found"))
    
    # Check if the file exists
    if not file_field or not os.path.exists(file_field.path):
        raise Http404(_("File not found"))
    
    # Return the file as a response
    response = FileResponse(open(file_field.path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response