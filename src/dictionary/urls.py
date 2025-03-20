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
    
    # SMTP Configuration
    path('config/smtp/', views.SMTPConfigurationView.as_view(), name='smtp_config'),
    path('config/smtp/test/', views.test_smtp_email, name='test_smtp_email'),
    
    # Contact form
    path('contact/', views.ContactMessageCreateView.as_view(), name='contact'),
]
