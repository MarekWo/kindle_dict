from django import template

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Sprawdza, czy użytkownik należy do określonej grupy.
    Użycie: {% if user|has_group:"Dictionary Admin" %}
    """
    return user.groups.filter(name=group_name).exists()
