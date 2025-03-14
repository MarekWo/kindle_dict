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
    path('<uuid:pk>/download/<str:file_type>/', views.dictionary_download, name='download'),
    
    # Dictionary suggestions
    path('suggest/', views.DictionarySuggestionCreateView.as_view(), name='suggest'),
]