# Generated by Django 4.2.10 on 2025-03-22 06:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0011_convert_suggestions_to_tasks'),
    ]

    operations = [
        migrations.AddField(
            model_name='dictionarysuggestion',
            name='author_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Autor słownika'),
        ),
        migrations.AddField(
            model_name='task',
            name='author_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Autor słownika'),
        ),
        migrations.AddField(
            model_name='task',
            name='rejection_reason',
            field=models.TextField(blank=True, verbose_name='Powód odrzucenia'),
        ),
    ]
