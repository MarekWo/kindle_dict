# Generated manually

from django.db import migrations

def convert_suggestions_to_tasks(apps, schema_editor):
    """
    Convert existing dictionary suggestions to tasks.
    """
    DictionarySuggestion = apps.get_model('dictionary', 'DictionarySuggestion')
    Task = apps.get_model('dictionary', 'Task')
    
    # Get all suggestions without a task
    suggestions = DictionarySuggestion.objects.filter(task__isnull=True)
    
    for suggestion in suggestions:
        # Create a task for this suggestion
        task = Task(
            title=f"Sugestia słownika: {suggestion.name}",
            description=suggestion.description,
            task_type='dictionary_suggestion',
            content=suggestion.content,
            email=suggestion.email,
            status='new' if suggestion.status == 'pending' else (
                'rejected' if suggestion.status == 'rejected' else 'accepted'
            ),
            created_at=suggestion.created_at
        )
        task.save()
        
        # Link the suggestion to the task
        suggestion.task = task
        suggestion.save()

def reverse_convert_suggestions_to_tasks(apps, schema_editor):
    """
    Reverse the conversion of dictionary suggestions to tasks.
    """
    DictionarySuggestion = apps.get_model('dictionary', 'DictionarySuggestion')
    Task = apps.get_model('dictionary', 'Task')
    
    # Get all suggestions with a task
    suggestions = DictionarySuggestion.objects.filter(task__isnull=False)
    
    for suggestion in suggestions:
        # Delete the task
        if suggestion.task:
            suggestion.task.delete()
        
        # Unlink the suggestion from the task
        suggestion.task = None
        suggestion.save()

class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0010_task_dictionarysuggestion_task'),
    ]

    operations = [
        migrations.RunPython(convert_suggestions_to_tasks, reverse_convert_suggestions_to_tasks),
    ]
