from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0015_drop_legacy_ever_sent'),
    ]

    operations = [
        migrations.AddField(
            model_name='reminder',
            name='is_deleted',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name='user',
            name='is_deleted',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]

