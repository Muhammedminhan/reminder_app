from django.db import migrations, models
from django.conf import settings

def backfill_sender_receiver(apps, schema_editor):
    Reminder = apps.get_model('app', 'Reminder')
    DefaultFrom = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
    # Basic safe fallback domain
    fallback = DefaultFrom or 'no-reply@example.com'
    for r in Reminder.objects.all():
        changed = False
        if not r.sender_email:
            r.sender_email = fallback
            changed = True
        if not r.receiver_email:
            # If no receiver, fallback to sender to keep not-null constraint satisfied
            r.receiver_email = r.sender_email
            changed = True
        if not getattr(r, 'sender_name', None):
            company = getattr(r, 'company', None)
            if company and getattr(company, 'name', None):
                r.sender_name = f"Alerts | {company.name}"[:200]
            else:
                r.sender_name = 'Alerts'
            changed = True
        if not r.interval_type:
            r.interval_type = 'one_time'
            changed = True
        if changed:
            r.save(update_fields=['sender_email','receiver_email','sender_name','interval_type'])

def noop_reverse(apps, schema_editor):
    # Irreversible
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0011_alter_scheduledtask_task_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reminder',
            name='sender_name',
            field=models.CharField(blank=True, help_text="Friendly display name for the sender shown in inbox (default: 'Alerts | <Company Name>')", max_length=200, null=True),
        ),
        migrations.RunPython(backfill_sender_receiver, noop_reverse),
        migrations.AlterField(
            model_name='reminder',
            name='sender_email',
            field=models.CharField(help_text='Enter the sender email ID', max_length=500),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='receiver_email',
            field=models.TextField(help_text='Enter email IDs for reminders, separated by commas.', max_length=500),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='interval_type',
            field=models.CharField(blank=True, choices=[('one_time', 'One-Time Reminder'), ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('6 months', '6 Months'), ('yearly', 'Yearly')], default='one_time', max_length=10, null=True),
        ),
    ]

