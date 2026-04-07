from django.db import migrations, models, connection


def add_missing_sendgrid_columns(apps, schema_editor):
    cursor = connection.cursor()
    vendor = connection.vendor
    existing_cols = []
    try:
        if vendor == 'sqlite':
            cursor.execute("PRAGMA table_info(app_sendgriddomainauth)")
            existing_cols = [r[1] for r in cursor.fetchall()]
        else:  # postgres / others using information_schema
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'app_sendgriddomainauth'
            """)
            existing_cols = [r[0] for r in cursor.fetchall()]
    except Exception:
        return  # Table maybe doesn't exist yet; ignore

    def safe_add(col_name, ddl):
        if col_name not in existing_cols:
            try:
                cursor.execute(ddl)
            except Exception:
                pass  # Ignore if race/exists

    # Only gcp_records_email_sent is missing per model state, but keep others idempotent
    safe_add('gcp_records_email_sent', "ALTER TABLE app_sendgriddomainauth ADD COLUMN gcp_records_email_sent boolean NOT NULL DEFAULT FALSE")
    safe_add('site_initial_email_sent', "ALTER TABLE app_sendgriddomainauth ADD COLUMN site_initial_email_sent boolean NOT NULL DEFAULT FALSE")
    safe_add('mapping_ready_email_sent', "ALTER TABLE app_sendgriddomainauth ADD COLUMN mapping_ready_email_sent boolean NOT NULL DEFAULT FALSE")


def noop_reverse(apps, schema_editor):
    # Columns are additive; we don't drop them on reverse
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0008_reminder_created_by'),
    ]

    operations = [
        migrations.RunPython(add_missing_sendgrid_columns, reverse_code=noop_reverse),
        # State already knows about site_initial_email_sent & mapping_ready_email_sent from 0007; add the new one.
        migrations.AddField(
            model_name='sendgriddomainauth',
            name='gcp_records_email_sent',
            field=models.BooleanField(default=False),
        ),
    ]
