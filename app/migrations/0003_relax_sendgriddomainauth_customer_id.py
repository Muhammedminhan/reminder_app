from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_remove_reminder_reminder_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sendgriddomainauth',
            name='customer_id',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]


