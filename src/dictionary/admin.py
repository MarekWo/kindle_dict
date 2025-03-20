# kindle_dict\src\dictionary\admin.py

"""
Admin configuration for the Dictionary app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from .models import Dictionary, DictionarySuggestion, SMTPConfiguration, ContactMessage

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

@admin.register(DictionarySuggestion)
class DictionarySuggestionAdmin(admin.ModelAdmin):
    """Admin for DictionarySuggestion model"""
    list_display = ('name', 'email', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'description', 'email')
    readonly_fields = ('id', 'created_at')
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
    )
    actions = ['approve_suggestions', 'reject_suggestions']
    
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
