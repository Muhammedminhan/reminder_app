from django.db import migrations, models


def ensure_completed_column(apps, schema_editor):
    """Create 'completed' column if it does not exist (idempotent)."""
    connection = schema_editor.connection
    table = 'app_reminder'
    try:
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table)
            cols = [c.name for c in description]
    except Exception:
        return
    if 'completed' in cols:
        return
    Reminder = apps.get_model('app', 'Reminder')
    field = models.BooleanField(default=False, help_text='Mark as completed after acting on the reminder.')
    field.set_attributes_from_name('completed')
    try:
        schema_editor.add_field(Reminder, field)
    except Exception:
        pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0012_enforce_sender_fields'),
    ]

    operations = [
        migrations.RunPython(ensure_completed_column, noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='reminder',
                    name='completed',
                    field=models.BooleanField(default=False, help_text='Mark as completed after acting on the reminder.'),
                )
            ]
        )
    ]
