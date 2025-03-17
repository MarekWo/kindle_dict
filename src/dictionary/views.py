# kindle_dict\src\dictionary\views.py

"""
Views for the Dictionary app.
"""

import os
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings

from .models import Dictionary, DictionarySuggestion, SMTPConfiguration
from .forms import DictionaryForm, DictionarySuggestionForm, SMTPConfigurationForm, DictionaryUpdateForm
from .tasks import process_dictionary
from .email_utils import send_test_email

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

class DictionaryCreateView(LoginRequiredMixin, CreateView):
    """View to create a new dictionary"""
    model = Dictionary
    form_class = DictionaryForm
    template_name = 'dictionary/create.html'
    success_url = reverse_lazy('dictionary:list')
    login_url = reverse_lazy('login')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has Dictionary Creator or Dictionary Admin role"""
        if not (request.user.groups.filter(name='Dictionary Creator').exists() or 
                request.user.groups.filter(name='Dictionary Admin').exists() or
                request.user.is_superuser):
            messages.error(request, _("Nie masz uprawnień do tworzenia słowników."))
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_initial(self):
        """Set initial values for the form"""
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            # Set creator_name to the user's full name
            user = self.request.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            if full_name:  # Only set if the user has a name
                initial['creator_name'] = full_name
        return initial
    
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
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user is not authenticated"""
        if request.user.is_authenticated:
            messages.info(request, _("Zalogowani użytkownicy nie mogą proponować słowników. Skontaktuj się z administratorem, aby uzyskać rolę Dictionary Creator."))
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
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
    
    # Prawidłowe kodowanie nazwy pliku w nagłówku Content-Disposition
    # Obsługa znaków specjalnych zgodnie z RFC 5987
    import urllib.parse
    encoded_filename = urllib.parse.quote(filename)
    response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"; filename*=UTF-8\'\'{encoded_filename}'
    
    return response

class SMTPConfigurationView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View to configure SMTP settings"""
    model = SMTPConfiguration
    form_class = SMTPConfigurationForm
    template_name = 'dictionary/smtp_config.html'
    success_url = reverse_lazy('dictionary:smtp_config')
    
    def test_func(self):
        """Only allow superusers to access this view"""
        return self.request.user.is_superuser
    
    def get_object(self, queryset=None):
        """Get the SMTP configuration object or create a new one if it doesn't exist"""
        config = SMTPConfiguration.objects.first()
        if not config:
            # Tworzymy obiekt, ale nie zapisujemy go jeszcze - zostanie zapisany przez formularz
            config = SMTPConfiguration(
                host='smtp.example.com',
                port=587,
                encryption='tls',
                auto_tls=True,
                authentication=True,
                username='user@example.com',
                password='password',
                from_email='noreply@example.com',
                from_name='Kindle Dictionary Creator'
            )
        return config
    
    def form_valid(self, form):
        """Process the form if it's valid"""
        # Check if we need to send a test email
        test_email = form.cleaned_data.get('test_email')
        
        # Sprawdź, czy hasło zostało wprowadzone
        password = form.cleaned_data.get('password')
        
        # Zapisz obiekt, ale nie zapisuj pustego hasła
        self.object = form.save(commit=False)
        
        # Jeśli hasło jest puste i obiekt już istnieje w bazie danych,
        # zachowaj poprzednie hasło
        if not password and self.object.pk:
            # Pobierz aktualne hasło z bazy danych
            current_config = SMTPConfiguration.objects.get(pk=self.object.pk)
            self.object.password = current_config.password
        
        # Zapisz konfigurację
        self.object.save()
        
        # Show success message
        messages.success(self.request, _("Konfiguracja SMTP została zapisana."))
        
        # If a test email was provided, send it
        if test_email:
            success = send_test_email(test_email, self.object)
            if success:
                messages.success(self.request, _("Wiadomość testowa została wysłana."))
            else:
                messages.error(self.request, _("Nie udało się wysłać wiadomości testowej. Sprawdź konfigurację SMTP i logi serwera."))
        
        return redirect(self.get_success_url())

def dictionary_delete(request, pk):
    """View to delete a dictionary"""
    # Get the dictionary object
    dictionary = get_object_or_404(Dictionary, pk=pk)
    
    # Check if user has permission to delete dictionaries
    if not (request.user.is_superuser or request.user.groups.filter(name='Dictionary Admin').exists()):
        messages.error(request, _("Nie masz uprawnień do usuwania słowników."))
        return redirect('dictionary:detail', pk=pk)
    
    if request.method == 'POST':
        # Get the media path for the dictionary
        media_path = os.path.join(settings.MEDIA_ROOT, 'dictionaries', str(dictionary.id))
        
        # Delete the dictionary from the database
        dictionary.delete()
        
        # Delete the dictionary folder from the media directory
        import shutil
        if os.path.exists(media_path):
            shutil.rmtree(media_path)
        
        messages.success(request, _("Słownik został pomyślnie usunięty."))
        return redirect('dictionary:list')
    
    # If not POST, show confirmation page
    return render(request, 'dictionary/delete_confirm.html', {'dictionary': dictionary})

class DictionaryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View to update an existing dictionary"""
    model = Dictionary
    form_class = DictionaryUpdateForm
    template_name = 'dictionary/update.html'
    login_url = reverse_lazy('login')
    
    def get_success_url(self):
        """Return to the dictionary detail page after update"""
        return reverse_lazy('dictionary:detail', kwargs={'pk': self.object.pk})
    
    def test_func(self):
        """Check if user has permission to edit dictionaries"""
        return (self.request.user.is_superuser or 
                self.request.user.groups.filter(name='Dictionary Admin').exists() or
                self.request.user.groups.filter(name='Dictionary Edit').exists())
    
    def get_initial(self):
        """Set initial values for the form"""
        initial = super().get_initial()
        
        # If the dictionary has a source file, try to read its content
        dictionary = self.get_object()
        if dictionary.source_file:
            try:
                with open(dictionary.source_file.path, 'r', encoding='utf-8') as f:
                    initial['content'] = f.read()
            except:
                pass
        
        # Set updater_name to the user's full name
        if self.request.user.is_authenticated:
            user = self.request.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            if full_name:  # Only set if the user has a name
                initial['updater_name'] = full_name
                
        return initial
    
    def form_valid(self, form):
        """Process the form if it's valid"""
        # Save the dictionary instance first
        self.object = form.save(commit=False)
        
        # Increment build version
        self.object.build_version += 1
        
        # Set updater_name if not provided
        if not self.object.updater_name and self.request.user.is_authenticated:
            user = self.request.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            if full_name:
                self.object.updater_name = full_name
        
        # Handle content from textarea if provided
        content = form.cleaned_data.get('content')
        if content:
            # Create a temporary file and save the content to it
            import tempfile
            
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
        messages.success(self.request, _("Słownik został zaktualizowany i jest przetwarzany."))
        
        return redirect(self.get_success_url())


@user_passes_test(lambda u: u.is_superuser)
def test_smtp_email(request):
    """View to send a test email"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email address is required'})
        
        # Get the SMTP configuration
        config = SMTPConfiguration.objects.first()
        if not config:
            return JsonResponse({'success': False, 'error': 'SMTP configuration not found'})
        
        # Send the test email
        success = send_test_email(email, config)
        
        if success:
            return JsonResponse({'success': True, 'message': 'Test email sent successfully'})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to send test email'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
