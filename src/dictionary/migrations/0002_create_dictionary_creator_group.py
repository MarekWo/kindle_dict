from django.db import migrations
from django.contrib.auth.models import Group, Permission


def create_dictionary_creator_group(apps, schema_editor):
    # Tworzenie grupy Dictionary Creator
    dictionary_creator_group, created = Group.objects.get_or_create(name='Dictionary Creator')
    
    # Możemy dodać odpowiednie uprawnienia do grupy, jeśli są potrzebne
    # Na przykład:
    # permission = Permission.objects.get(codename='add_dictionary')
    # dictionary_creator_group.permissions.add(permission)


def remove_dictionary_creator_group(apps, schema_editor):
    # Usuwanie grupy Dictionary Creator
    Group.objects.filter(name='Dictionary Creator').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_dictionary_creator_group, remove_dictionary_creator_group),
    ]
