# kindle_dict\src\dictionary\admin.py

"""
Admin configuration for the Dictionary app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from .models import Dictionary, DictionarySuggestion, SMTPConfiguration, ContactMessage, CaptchaConfiguration, Task

@admin.register(Dictionary)
class DictionaryAdmin(admin.ModelAdmin):
    """Admin for Dictionary model"""
    list_display = ('name', 'creator_name', 'updater_name', 'language_code', 'status', 'is_public', 'build_version', 'created_at', 'built_at')
    list_filter = ('status', 'is_public', 'language_code')
    search_fields = ('name', 'description', 'creator_name', 'updater_name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'built_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'description', 'creator_name', 'updater_name', 'language_code', 'is_public')
        }),
        (_('Files'), {
            'fields': ('source_file', 'html_file', 'opf_file', 'jpg_file', 'mobi_file', 'json_file', 'zip_file')
        }),
        (_('Status & Version'), {
            'fields': ('status', 'status_message', 'build_version')
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at', 'built_at')
        }),
    )
    actions = ['rebuild_dictionaries']
    
    def rebuild_dictionaries(self, request, queryset):
        """Admin action to rebuild selected dictionaries"""
        from .tasks import process_dictionary
        
        for dictionary in queryset:
            process_dictionary.delay(str(dictionary.id))
        
        self.message_user(request, _("Selected dictionaries are being rebuilt."))
    
    rebuild_dictionaries.short_description = _("Rebuild selected dictionaries")

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin for Task model"""
    list_display = ('title', 'task_type', 'status', 'email', 'created_at', 'assigned_to')
    list_filter = ('status', 'task_type')
    search_fields = ('title', 'description', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'title', 'description', 'task_type', 'status')
        }),
        (_('Przypisanie'), {
            'fields': ('created_by', 'assigned_to', 'related_dictionary')
        }),
        (_('Dane kontaktowe'), {
            'fields': ('email',)
        }),
        (_('Zawartość'), {
            'fields': ('content', 'source_file')
        }),
        (_('Daty'), {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )
    actions = ['mark_as_accepted', 'mark_as_rejected', 'mark_as_completed']
    
    def mark_as_accepted(self, request, queryset):
        """Admin action to mark selected tasks as accepted"""
        for task in queryset:
            task.mark_as_accepted(request.user)
        self.message_user(request, _("Wybrane zadania zostały oznaczone jako zaakceptowane."))
    
    mark_as_accepted.short_description = _("Oznacz jako zaakceptowane")
    
    def mark_as_rejected(self, request, queryset):
        """Admin action to mark selected tasks as rejected"""
        for task in queryset:
            task.mark_as_rejected()
        self.message_user(request, _("Wybrane zadania zostały oznaczone jako odrzucone."))
    
    mark_as_rejected.short_description = _("Oznacz jako odrzucone")
    
    def mark_as_completed(self, request, queryset):
        """Admin action to mark selected tasks as completed"""
        for task in queryset:
            task.mark_as_completed()
        self.message_user(request, _("Wybrane zadania zostały oznaczone jako zrealizowane."))
    
    mark_as_completed.short_description = _("Oznacz jako zrealizowane")


@admin.register(DictionarySuggestion)
class DictionarySuggestionAdmin(admin.ModelAdmin):
    """Admin for DictionarySuggestion model"""
    list_display = ('name', 'email', 'status', 'created_at', 'has_task')
    list_filter = ('status',)
    search_fields = ('name', 'description', 'email')
    readonly_fields = ('id', 'created_at', 'task')
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'description', 'email')
        }),
        (_('Content'), {
            'fields': ('content', 'source_file')
        }),
        (_('Status & Date'), {
            'fields': ('status', 'created_at')
        }),
        (_('Zadanie'), {
            'fields': ('task',)
        }),
    )
    actions = ['approve_suggestions', 'reject_suggestions', 'create_tasks']
    
    def has_task(self, obj):
        """Check if suggestion has a task"""
        return bool(obj.task)
    has_task.boolean = True
    has_task.short_description = _("Ma zadanie")
    
    def approve_suggestions(self, request, queryset):
        """Admin action to approve selected suggestions"""
        # In the future, we could convert these suggestions to actual dictionaries
        queryset.update(status='approved')
        self.message_user(request, _("Selected suggestions have been approved."))
    
    approve_suggestions.short_description = _("Approve selected suggestions")
    
    def reject_suggestions(self, request, queryset):
        """Admin action to reject selected suggestions"""
        queryset.update(status='rejected')
        self.message_user(request, _("Selected suggestions have been rejected."))
    
    reject_suggestions.short_description = _("Reject selected suggestions")
    
    def create_tasks(self, request, queryset):
        """Admin action to create tasks from selected suggestions"""
        task_count = 0
        for suggestion in queryset:
            if not suggestion.task:
                suggestion.create_task()
                task_count += 1
        
        if task_count:
            self.message_user(request, _("Utworzono {0} nowych zadań.").format(task_count))
        else:
            self.message_user(request, _("Nie utworzono żadnych nowych zadań. Wszystkie wybrane sugestie mają już zadania."))
    
    create_tasks.short_description = _("Utwórz zadania z wybranych sugestii")

@admin.register(SMTPConfiguration)
class SMTPConfigurationAdmin(admin.ModelAdmin):
    """Admin for SMTPConfiguration model"""
    list_display = ('host', 'port', 'encryption', 'from_email', 'from_name', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('Serwer SMTP'), {
            'fields': ('host', 'port', 'encryption', 'auto_tls')
        }),
        (_('Uwierzytelnianie'), {
            'fields': ('authentication', 'username', 'password')
        }),
        (_('Nadawca'), {
            'fields': ('from_email', 'from_name')
        }),
        (_('Daty'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def has_add_permission(self, request):
        """Only allow adding if no configuration exists"""
        return not SMTPConfiguration.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of the configuration"""
        return False

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """Admin for ContactMessage model"""
    list_display = ('name', 'email', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'email', 'is_read')
        }),
        (_('Wiadomość'), {
            'fields': ('message',)
        }),
        (_('Data'), {
            'fields': ('created_at',)
        }),
    )
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """Admin action to mark selected messages as read"""
        queryset.update(is_read=True)
        self.message_user(request, _("Zaznaczone wiadomości zostały oznaczone jako przeczytane."))
    
    mark_as_read.short_description = _("Oznacz jako przeczytane")
    
    def mark_as_unread(self, request, queryset):
        """Admin action to mark selected messages as unread"""
        queryset.update(is_read=False)
        self.message_user(request, _("Zaznaczone wiadomości zostały oznaczone jako nieprzeczytane."))
    
    mark_as_unread.short_description = _("Oznacz jako nieprzeczytane")

@admin.register(CaptchaConfiguration)
class CaptchaConfigurationAdmin(admin.ModelAdmin):
    """Admin for CaptchaConfiguration model"""
    list_display = ('provider', 'site_key', 'is_enabled', 'enable_login', 'enable_contact', 'enable_suggest', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('Dostawca'), {
            'fields': ('provider', 'site_key', 'secret_key')
        }),
        (_('Ustawienia'), {
            'fields': ('is_enabled', 'enable_login', 'enable_contact', 'enable_suggest')
        }),
        (_('Daty'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def has_add_permission(self, request):
        """Only allow adding if no configuration exists"""
        return not CaptchaConfiguration.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of the configuration"""
        return False
