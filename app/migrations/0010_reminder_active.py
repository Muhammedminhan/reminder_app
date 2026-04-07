from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0009_safe_sendgriddomainauth_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='reminder',
            name='active',
            field=models.BooleanField(default=True, help_text='Uncheck to pause sending of this reminder and its future occurrences.'),
        ),
    ]

