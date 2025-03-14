# kindle_dict\src\dictionary\admin.py

"""
Admin configuration for the Dictionary app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Dictionary, DictionarySuggestion

@admin.register(Dictionary)
class DictionaryAdmin(admin.ModelAdmin):
    """Admin for Dictionary model"""
    list_display = ('name', 'creator_name', 'language_code', 'status', 'is_public', 'build_version', 'created_at', 'built_at')
    list_filter = ('status', 'is_public', 'language_code')
    search_fields = ('name', 'description', 'creator_name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'built_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'description', 'creator_name', 'language_code', 'is_public')
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