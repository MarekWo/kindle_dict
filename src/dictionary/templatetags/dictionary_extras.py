from django import template
from django.db.models import Count, Q

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Sprawdza, czy użytkownik należy do określonej grupy.
    Użycie: {% if user|has_group:"Dictionary Admin" %}
    """
    return user.groups.filter(name=group_name).exists()

@register.simple_tag
def get_new_tasks_count():
    """
    Zwraca liczbę nowych zadań.
    Użycie: {% get_new_tasks_count %}
    """
    from dictionary.models import Task
    return Task.objects.filter(status='new').count()

@register.filter(name='can_manage_tasks')
def can_manage_tasks(user):
    """
    Sprawdza, czy użytkownik może zarządzać zadaniami.
    Użycie: {% if user|can_manage_tasks %}
    """
    return (user.is_authenticated and 
            (user.is_superuser or 
             user.groups.filter(name__in=['Dictionary Admin', 'Dictionary Creator']).exists()))
