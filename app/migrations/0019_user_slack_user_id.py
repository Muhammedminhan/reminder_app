from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0018_company_domain'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='slack_user_id',
            field=models.CharField(blank=True, help_text="Slack member ID for direct notifications (e.g. U123456789).", max_length=64, null=True),
        ),
    ]
