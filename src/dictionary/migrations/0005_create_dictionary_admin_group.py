from django.db import migrations
from django.contrib.auth.models import Group, Permission


def create_dictionary_admin_group(apps, schema_editor):
    # Tworzenie grupy Dictionary Admin
    dictionary_admin_group, created = Group.objects.get_or_create(name='Dictionary Admin')
    
    # Możemy dodać odpowiednie uprawnienia do grupy, jeśli są potrzebne
    # Na przykład:
    # permission = Permission.objects.get(codename='add_dictionary')
    # dictionary_admin_group.permissions.add(permission)


def remove_dictionary_admin_group(apps, schema_editor):
    # Usuwanie grupy Dictionary Admin
    Group.objects.filter(name='Dictionary Admin').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0004_dictionary_notification_email'),
    ]

    operations = [
        migrations.RunPython(create_dictionary_admin_group, remove_dictionary_admin_group),
    ]
