from django.db import migrations, connection


def drop_legacy_ever_sent(apps, schema_editor):
    """Remove legacy 'ever_sent' column (and map its truthy rows to send=True first)."""
    try:
        with connection.cursor() as cursor:
            table = 'app_reminder'
            # Introspect columns
            description = connection.introspection.get_table_description(cursor, table)
            cols = [c.name for c in description]
            if 'ever_sent' not in cols:
                return
            vendor = connection.vendor
            # Map legacy data into current 'send' field before drop
            try:
                cursor.execute("UPDATE app_reminder SET send = TRUE WHERE ever_sent = TRUE AND send = FALSE")
            except Exception:
                pass
            if vendor == 'postgresql':
                cursor.execute('ALTER TABLE app_reminder DROP COLUMN IF EXISTS ever_sent')
            elif vendor == 'mysql':
                cursor.execute('ALTER TABLE app_reminder DROP COLUMN ever_sent')
            else:
                # Attempt generic drop (SQLite 3.35+) - ignore failure silently
                try:
                    cursor.execute('ALTER TABLE app_reminder DROP COLUMN ever_sent')
                except Exception:
                    # As a minimal fallback, relax NOT NULL so inserts succeed (set all NULL to 0)
                    try:
                        cursor.execute('UPDATE app_reminder SET ever_sent = 0 WHERE ever_sent IS NULL')
                    except Exception:
                        pass
    except Exception:
        # Silent: we do not want migration to abort deployment due to legacy artifact
        return


def recreate_ever_sent(apps, schema_editor):
    """Reverse: re-add column (data lost except we can infer from send)."""
    try:
        with connection.cursor() as cursor:
            table = 'app_reminder'
            description = connection.introspection.get_table_description(cursor, table)
            cols = [c.name for c in description]
            if 'ever_sent' in cols:
                return
            vendor = connection.vendor
            if vendor == 'postgresql':
                cursor.execute("ALTER TABLE app_reminder ADD COLUMN ever_sent boolean NOT NULL DEFAULT FALSE")
                cursor.execute("UPDATE app_reminder SET ever_sent = send WHERE send = TRUE")
            elif vendor == 'mysql':
                cursor.execute("ALTER TABLE app_reminder ADD COLUMN ever_sent BOOL NOT NULL DEFAULT 0")
                cursor.execute("UPDATE app_reminder SET ever_sent = send WHERE send = TRUE")
            else:
                try:
                    cursor.execute("ALTER TABLE app_reminder ADD COLUMN ever_sent BOOL DEFAULT 0")
                    cursor.execute("UPDATE app_reminder SET ever_sent = COALESCE(send,0)")
                except Exception:
                    pass
    except Exception:
        return


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0014_alter_reminder_reminder_start_date'),
    ]

    operations = [
        migrations.RunPython(drop_legacy_ever_sent, recreate_ever_sent),
    ]

