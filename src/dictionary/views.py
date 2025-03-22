# kindle_dict\src\dictionary\views.py

"""
Views for the Dictionary app.
"""

import os
import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.db.models import Count, Q

from .models import Dictionary, DictionarySuggestion, SMTPConfiguration, ContactMessage, CaptchaConfiguration, Task
from .forms import (
    DictionaryForm, DictionarySuggestionForm, SMTPConfigurationForm, DictionaryUpdateForm, 
    ContactMessageForm, CaptchaConfigurationForm, TaskForm, TaskStatusForm
)
from .tasks import process_dictionary
from .email_utils import (
    send_test_email, send_contact_message_notification, send_task_notification,
    send_task_status_notification_to_submitter
)
from .captcha_utils import verify_captcha_response, get_captcha_context, is_captcha_enabled

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

# Funkcja pomocnicza do sprawdzania uprawnień
def can_manage_tasks(user):
    """Check if user can manage tasks"""
    return (user.is_authenticated and 
            (user.is_superuser or 
             user.groups.filter(name__in=['Dictionary Admin', 'Dictionary Creator']).exists()))

def get_new_tasks_count():
    """Get count of new tasks"""
    return Task.objects.filter(status='new').count()

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
    
    def get_context_data(self, **kwargs):
        """Add CAPTCHA context data"""
        context = super().get_context_data(**kwargs)
        context.update(get_captcha_context('suggest'))
        return context
    
    def form_valid(self, form):
        """Process the form if it's valid"""
        # Verify CAPTCHA if enabled
        if is_captcha_enabled('suggest'):
            captcha_response = self.request.POST.get('cf-turnstile-response') or self.request.POST.get('g-recaptcha-response')
            if not verify_captcha_response(captcha_response):
                form.add_error(None, _("Weryfikacja CAPTCHA nie powiodła się. Spróbuj ponownie."))
                context = self.get_context_data(form=form)
                context['captcha_error'] = _("Weryfikacja CAPTCHA nie powiodła się. Spróbuj ponownie.")
                return self.render_to_response(context)
        
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
        
        # Create a task for this suggestion
        # Nie tworzymy zadania tutaj, ponieważ jest już tworzone w sygnale post_save
        
        # Send notification about new task
        send_task_notification(self.object.task)
        
        # Show success message
        messages.success(self.request, _("Dziękujemy za Twoją propozycję! Zostanie ona sprawdzona przez naszych administratorów."))
        
        return redirect(self.get_success_url())

class TaskListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View to display a list of tasks"""
    model = Task
    template_name = 'dictionary/tasks/list.html'
    context_object_name = 'tasks'
    login_url = reverse_lazy('login')
    
    def test_func(self):
        """Check if user can manage tasks"""
        return can_manage_tasks(self.request.user)
    
    def get_queryset(self):
        """Filter tasks based on tab"""
        tab = self.kwargs.get('tab', 'new')
        
        if tab == 'new':
            return Task.objects.filter(status='new').order_by('-created_at')
        elif tab == 'pending':
            return Task.objects.filter(status='accepted').order_by('-updated_at')
        elif tab == 'archive':
            return Task.objects.filter(status__in=['completed', 'rejected']).order_by('-updated_at')
        else:
            return Task.objects.all().order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """Add additional data to context"""
        context = super().get_context_data(**kwargs)
        tab = self.kwargs.get('tab', 'new')
        context['active_tab'] = tab
        
        # Add counts for each tab
        context['new_count'] = Task.objects.filter(status='new').count()
        context['pending_count'] = Task.objects.filter(status='accepted').count()
        context['archive_count'] = Task.objects.filter(status__in=['completed', 'rejected']).count()
        
        return context

class TaskDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View to display details of a task"""
    model = Task
    template_name = 'dictionary/tasks/detail.html'
    context_object_name = 'task'
    login_url = reverse_lazy('login')
    
    def test_func(self):
        """Check if user can manage tasks"""
        return can_manage_tasks(self.request.user)
    
    def get_context_data(self, **kwargs):
        """Add additional data to context"""
        context = super().get_context_data(**kwargs)
        context['status_form'] = TaskStatusForm(instance=self.object)
        
        # Add dictionary creation form if task is a dictionary suggestion
        if self.object.task_type == 'dictionary_suggestion' and self.object.status == 'accepted':
            # Ustaw domyślną wartość dla creator_name
            creator_name = self.object.author_name if self.object.author_name else "Nieznany"
            
            initial_data = {
                'name': self.object.title.replace('Sugestia słownika: ', ''),
                'description': self.object.description,
                'creator_name': creator_name,
                'notification_email': self.object.email,
                'content': self.object.content,
            }
            
            # Jeśli zadanie ma plik źródłowy, ale nie ma zawartości, wczytaj zawartość pliku
            if self.object.source_file and not self.object.content:
                try:
                    with open(self.object.source_file.path, 'r', encoding='utf-8') as f:
                        initial_data['content'] = f.read()
                except Exception as e:
                    # W przypadku błędu, zaloguj go, ale nie przerywaj działania
                    logger = logging.getLogger(__name__)
                    logger.error(f"Nie udało się odczytać pliku źródłowego: {e}")
            
            context['dictionary_form'] = DictionaryForm(initial=initial_data)
        
        return context

@login_required
@user_passes_test(can_manage_tasks)
def task_update_status(request, pk):
    """View to update task status"""
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        form = TaskStatusForm(request.POST, instance=task)
        if form.is_valid():
            old_status = task.status
            task = form.save()
            
            # Logowanie dla debugowania
            logger = logging.getLogger(__name__)
            logger.info(f"Task status update: old_status={old_status}, new_status={task.status}")
            
            # Zawsze wysyłaj powiadomienie do zgłaszającego, niezależnie od zmiany statusu
            # Send notification to administrators
            send_task_notification(task, status_change=True)
            
            # Send notification to submitter if email is provided
            if task.email:
                logger.info(f"Sending notification to submitter: {task.email}")
                send_task_status_notification_to_submitter(task)
            
            messages.success(request, _("Status zadania został zaktualizowany."))
            
            # Redirect to appropriate tab based on new status
            if task.status == 'new':
                return redirect('dictionary:tasks', tab='new')
            elif task.status == 'accepted':
                return redirect('dictionary:tasks', tab='pending')
            elif task.status in ['completed', 'rejected']:
                return redirect('dictionary:tasks', tab='archive')
        else:
            messages.error(request, _("Wystąpił błąd podczas aktualizacji statusu zadania."))
    
    return redirect('dictionary:task_detail', pk=pk)

@login_required
@user_passes_test(can_manage_tasks)
def task_create_dictionary(request, pk):
    """View to create a dictionary from a task"""
    task = get_object_or_404(Task, pk=pk)
    
    if task.task_type != 'dictionary_suggestion' or task.status != 'accepted':
        messages.error(request, _("Nie można utworzyć słownika z tego zadania."))
        return redirect('dictionary:task_detail', pk=pk)
    
    if request.method == 'POST':
        form = DictionaryForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the dictionary
            dictionary = form.save(commit=False)
            
            # Set creator name to current user if not provided
            if not dictionary.creator_name and request.user.is_authenticated:
                user = request.user
                full_name = f"{user.first_name} {user.last_name}".strip()
                if full_name:
                    dictionary.creator_name = full_name
                else:
                    dictionary.creator_name = user.username
            
            # Handle content from textarea if provided
            content = form.cleaned_data.get('content')
            if content and not dictionary.source_file:
                # Create a temporary file and save the content to it
                import tempfile
                
                # Create a temporary file with the content
                content_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
                content_file.write(content.encode('utf-8'))
                content_file.close()
                
                # Set the source_file field to this file
                from django.core.files import File
                with open(content_file.name, 'rb') as f:
                    filename = f"{dictionary.name}.txt"
                    dictionary.source_file.save(filename, File(f), save=False)
                
                # Clean up the temporary file
                os.unlink(content_file.name)
            # Jeśli nie podano zawartości ani pliku, ale zadanie ma zawartość lub plik
            elif not content and not dictionary.source_file:
                if task.content:
                    # Utwórz plik z zawartością zadania
                    import tempfile
                    
                    content_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
                    content_file.write(task.content.encode('utf-8'))
                    content_file.close()
                    
                    from django.core.files import File
                    with open(content_file.name, 'rb') as f:
                        filename = f"{dictionary.name}.txt"
                        dictionary.source_file.save(filename, File(f), save=False)
                    
                    os.unlink(content_file.name)
                elif task.source_file:
                    # Kopiuj plik z zadania
                    from django.core.files.base import ContentFile
                    dictionary.source_file.save(
                        task.source_file.name,
                        ContentFile(task.source_file.read()),
                        save=False
                    )
            
            # Set status and save the object
            dictionary.status = 'pending'
            dictionary.save()
            
            # Start the Celery task for processing the dictionary
            process_dictionary.delay(str(dictionary.id))
            
            # Update task status and link to dictionary
            task.mark_as_completed(dictionary)
            
            # Send notification to submitter
            send_task_status_notification_to_submitter(task)
            
            messages.success(request, _("Słownik został utworzony i jest przetwarzany."))
            return redirect('dictionary:tasks', tab='archive')
        else:
            messages.error(request, _("Wystąpił błąd podczas tworzenia słownika."))
            return render(request, 'dictionary/tasks/detail.html', {
                'task': task,
                'status_form': TaskStatusForm(instance=task),
                'dictionary_form': form
            })
    
    return redirect('dictionary:task_detail', pk=pk)

def task_download_file(request, pk):
    """View to download task source file"""
    # Get the task object
    task = get_object_or_404(Task, pk=pk)
    
    # Check if the task has a source file
    if not task.source_file or not os.path.exists(task.source_file.path):
        raise Http404(_("File not found"))
    
    # Get the original filename or use a default one
    filename = os.path.basename(task.source_file.name)
    
    # Return the file as a response
    response = FileResponse(open(task.source_file.path, 'rb'))
    
    # Set Content-Disposition header to force download
    import urllib.parse
    encoded_filename = urllib.parse.quote(filename)
    response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"; filename*=UTF-8\'\'{encoded_filename}'
    
    return response

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


class ContactMessageCreateView(CreateView):
    """View for users to submit contact messages"""
    model = ContactMessage
    form_class = ContactMessageForm
    template_name = 'dictionary/contact.html'
    success_url = reverse_lazy('home')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user is not authenticated"""
        if request.user.is_authenticated:
            messages.info(request, _("Zalogowani użytkownicy nie mogą korzystać z formularza kontaktowego. Prosimy o bezpośredni kontakt z administratorem."))
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add CAPTCHA context data"""
        context = super().get_context_data(**kwargs)
        context.update(get_captcha_context('contact'))
        return context
    
    def form_valid(self, form):
        """Process the form if it's valid"""
        # Verify CAPTCHA if enabled
        if is_captcha_enabled('contact'):
            captcha_response = self.request.POST.get('cf-turnstile-response') or self.request.POST.get('g-recaptcha-response')
            if not verify_captcha_response(captcha_response):
                form.add_error(None, _("Weryfikacja CAPTCHA nie powiodła się. Spróbuj ponownie."))
                context = self.get_context_data(form=form)
                context['captcha_error'] = _("Weryfikacja CAPTCHA nie powiodła się. Spróbuj ponownie.")
                return self.render_to_response(context)
        
        # Save the contact message
        self.object = form.save()
        
        # Send notification to administrators
        send_contact_message_notification(self.object)
        
        # Show success message
        messages.success(self.request, _("Dziękujemy za wiadomość! Odpowiemy najszybciej jak to możliwe."))
        
        return redirect(self.get_success_url())


class CaptchaConfigurationView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View to configure CAPTCHA settings"""
    model = CaptchaConfiguration
    form_class = CaptchaConfigurationForm
    template_name = 'dictionary/captcha_config.html'
    success_url = reverse_lazy('dictionary:captcha_config')
    
    def test_func(self):
        """Only allow superusers to access this view"""
        return self.request.user.is_superuser
    
    def get_object(self, queryset=None):
        """Get the CAPTCHA configuration object or create a new one if it doesn't exist"""
        config = CaptchaConfiguration.objects.first()
        if not config:
            # Tworzymy obiekt, ale nie zapisujemy go jeszcze - zostanie zapisany przez formularz
            config = CaptchaConfiguration(
                provider='cloudflare',
                site_key='',
                secret_key='',
                is_enabled=True,
                enable_login=True,
                enable_contact=True,
                enable_suggest=True
            )
        return config
    
    def form_valid(self, form):
        """Process the form if it's valid"""
        # Zapisz obiekt
        self.object = form.save()
        
        # Show success message
        messages.success(self.request, _("Konfiguracja CAPTCHA została zapisana."))
        
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


class HelpSuggestView(ListView):
    """View to display help on how to suggest a new dictionary"""
    model = Dictionary  # Używamy tego modelu, ale nie będziemy wyświetlać jego danych
    template_name = 'dictionary/help/suggest.html'
    
    def get_queryset(self):
        """Return an empty queryset"""
        return Dictionary.objects.none()


class HelpPromptView(ListView):
    """View to display example AI prompt"""
    model = Dictionary  # Używamy tego modelu, ale nie będziemy wyświetlać jego danych
    template_name = 'dictionary/help/prompt.html'
    
    def get_queryset(self):
        """Return an empty queryset"""
        return Dictionary.objects.none()


class HelpKindleView(ListView):
    """View to display information about dictionaries on Kindle"""
    model = Dictionary  # Używamy tego modelu, ale nie będziemy wyświetlać jego danych
    template_name = 'dictionary/help/kindle.html'
    
    def get_queryset(self):
        """Return an empty queryset"""
        return Dictionary.objects.none()
