from django.db import migrations
from django.contrib.auth.models import Group, Permission


def create_dictionary_edit_group(apps, schema_editor):
    # Tworzenie grupy Dictionary Edit
    dictionary_edit_group, created = Group.objects.get_or_create(name='Dictionary Edit')
    
    # Możemy dodać odpowiednie uprawnienia do grupy, jeśli są potrzebne
    # Na przykład:
    # permission = Permission.objects.get(codename='change_dictionary')
    # dictionary_edit_group.permissions.add(permission)


def remove_dictionary_edit_group(apps, schema_editor):
    # Usuwanie grupy Dictionary Edit
    Group.objects.filter(name='Dictionary Edit').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0005_create_dictionary_admin_group'),
    ]

    operations = [
        migrations.RunPython(create_dictionary_edit_group, remove_dictionary_edit_group),
    ]
