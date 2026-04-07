from django.db import migrations, models

def create_scheduledtask_table(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == 'postgresql':
        # Handled by previous migrations usually, but for safety:
        schema_editor.execute(r"""
            CREATE TABLE IF NOT EXISTS app_scheduledtask (
                id BIGSERIAL PRIMARY KEY,
                task_type VARCHAR(50) NOT NULL,
                task_data JSONB DEFAULT '{}'::jsonb NOT NULL,
                scheduled_at TIMESTAMPTZ NOT NULL,
                executed_at TIMESTAMPTZ NULL,
                is_completed BOOLEAN DEFAULT FALSE NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                company_id BIGINT NULL REFERENCES app_company(id) DEFERRABLE INITIALLY DEFERRED
            );
        """)
        schema_editor.execute(
            "CREATE INDEX IF NOT EXISTS app_schedul_task_ty_bc964d_idx ON app_scheduledtask (task_type, scheduled_at, is_completed);"
        )
    else:
        # For sqlite, create table via Django's schema editor if not present
        ScheduledTask = apps.get_model('app', 'ScheduledTask')
        # Check if table exists manually to avoid error if it somehow does
        table_name = ScheduledTask._meta.db_table
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            if not cursor.fetchone():
                schema_editor.create_model(ScheduledTask)

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0024_companyssosettings'),
    ]

    operations = [
        migrations.RunPython(create_scheduledtask_table, migrations.RunPython.noop),
    ]
