# kindle_dict\src\dictionary\urls.py

"""
URL patterns for the Dictionary app.
"""

from django.urls import path
from . import views

app_name = 'dictionary'

urlpatterns = [
    # Dictionary views
    path('', views.DictionaryListView.as_view(), name='list'),
    path('create/', views.DictionaryCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.DictionaryDetailView.as_view(), name='detail'),
    path('<uuid:pk>/update/', views.DictionaryUpdateView.as_view(), name='update'),
    path('<uuid:pk>/download/<str:file_type>/', views.dictionary_download, name='download'),
    path('<uuid:pk>/delete/', views.dictionary_delete, name='delete'),
    
    # Dictionary suggestions
    path('suggest/', views.DictionarySuggestionCreateView.as_view(), name='suggest'),
    
    # Tasks
    path('tasks/', views.TaskListView.as_view(), name='tasks'),
    path('tasks/<str:tab>/', views.TaskListView.as_view(), name='tasks'),
    path('tasks/detail/<uuid:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('tasks/update-status/<uuid:pk>/', views.task_update_status, name='task_update_status'),
    path('tasks/create-dictionary/<uuid:pk>/', views.task_create_dictionary, name='task_create_dictionary'),
    path('tasks/download-file/<uuid:pk>/', views.task_download_file, name='task_download_file'),
    
    # Configuration
    path('config/smtp/', views.SMTPConfigurationView.as_view(), name='smtp_config'),
    path('config/smtp/test/', views.test_smtp_email, name='test_smtp_email'),
    path('config/captcha/', views.CaptchaConfigurationView.as_view(), name='captcha_config'),
    
    # Contact form
    path('contact/', views.ContactMessageCreateView.as_view(), name='contact'),
    
    # Help pages
    path('help/suggest/', views.HelpSuggestView.as_view(), name='help_suggest'),
    path('help/prompt/', views.HelpPromptView.as_view(), name='help_prompt'),
]
