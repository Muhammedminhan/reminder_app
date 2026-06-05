# NOTE: Migrations 0004, 0005, and 0006 were squashed/consolidated into
# 0007_create_sendgriddomainauth_sqlite.py during an early refactor when the
# project was migrated from SQLite to PostgreSQL. The operations they contained
# (SendGridDomainAuth table creation and field adjustments) are fully covered
# by 0007. This file exists solely to document the intentional gap so that
# migration history tools do not flag 0003 → 0007 as an error.
#
# DO NOT run makemigrations to fill this gap — 0007 is the canonical migration.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_relax_sendgriddomainauth_customer_id'),
    ]

    operations = [
        # Intentionally empty — see note above.
    ]
