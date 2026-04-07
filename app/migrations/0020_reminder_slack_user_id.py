from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0019_user_slack_user_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='reminder',
            name='slack_user_id',
            field=models.CharField(max_length=64, null=True, blank=True, help_text='Slack member ID for direct notifications (e.g. U123456789).'),
        ),
    ]

