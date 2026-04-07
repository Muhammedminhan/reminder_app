from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0007_create_sendgriddomainauth_sqlite'),
    ]

    operations = [
        migrations.AddField(
            model_name='reminder',
            name='created_by',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reminders', to='app.user'),
        ),
    ]

