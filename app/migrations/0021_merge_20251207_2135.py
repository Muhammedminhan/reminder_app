# Generated merge migration — resolves duplicate 0016 and 0017 branches.
#
# Branch A: 0015 → 0016_add_visible_to_department_field → 0017_add_permission_role_system
# Branch B: 0015 → 0016_soft_delete_fields → 0017_alter_user_managers_... → 0018 → 0019 → 0020
#
# Both branches are merged here so that 0022+ has a single unambiguous parent.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        # Leaf of Branch A
        ('app', '0017_add_permission_role_system'),
        # Leaf of Branch B (via 0018 → 0019 → 0020)
        ('app', '0020_reminder_slack_user_id'),
    ]

    operations = [
    ]
