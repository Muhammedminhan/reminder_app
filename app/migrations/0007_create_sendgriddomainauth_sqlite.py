from django.db import migrations, models, connection
import django.db.models.deletion


def create_sendgrid_table(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == 'postgresql':
        schema_editor.execute(r"""
            CREATE TABLE IF NOT EXISTS app_sendgriddomainauth (
                id BIGSERIAL PRIMARY KEY,
                customer_id varchar(255) NULL,
                domain varchar(255) NOT NULL,
                domain_id bigint NULL,
                subdomain varchar(255) NOT NULL DEFAULT 'mail',
                is_verified boolean NOT NULL DEFAULT FALSE,
                dns_records jsonb NOT NULL DEFAULT '{}'::jsonb,
                created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_checked timestamp with time zone NULL,
                site_verification_method varchar(50) NOT NULL DEFAULT 'DNS_TXT',
                site_verification_token varchar(512) NULL,
                site_verified boolean NOT NULL DEFAULT FALSE,
                site_verified_at timestamp with time zone NULL,
                site_initial_email_sent boolean NOT NULL DEFAULT FALSE,
                mapping_ready_email_sent boolean NOT NULL DEFAULT FALSE,
                user_id bigint NOT NULL REFERENCES app_user(id) DEFERRABLE INITIALLY DEFERRED
            );
        """)
    else:
        # For sqlite (and other backends), create table via Django's schema editor using the model definition
        SendGridDomainAuth = apps.get_model('app', 'SendGridDomainAuth')
        try:
            schema_editor.create_model(SendGridDomainAuth)
        except Exception:
            # Ignore if already created
            pass


def drop_sendgrid_table(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == 'postgresql':
        schema_editor.execute("DROP TABLE IF EXISTS app_sendgriddomainauth;")
    else:
        SendGridDomainAuth = apps.get_model('app', 'SendGridDomainAuth')
        try:
            schema_editor.delete_model(SendGridDomainAuth)
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_relax_sendgriddomainauth_customer_id'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(create_sendgrid_table, reverse_code=drop_sendgrid_table),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='SendGridDomainAuth',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('customer_id', models.CharField(blank=True, max_length=255, null=True)),
                        ('domain', models.CharField(max_length=255)),
                        ('domain_id', models.BigIntegerField(blank=True, null=True)),
                        ('subdomain', models.CharField(default='mail', max_length=255)),
                        ('is_verified', models.BooleanField(default=False)),
                        ('dns_records', models.JSONField(blank=True, default=dict)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('last_checked', models.DateTimeField(blank=True, null=True)),
                        ('site_verification_method', models.CharField(blank=True, default='DNS_TXT', max_length=50)),
                        ('site_verification_token', models.CharField(blank=True, max_length=512, null=True)),
                        ('site_verified', models.BooleanField(default=False)),
                        ('site_verified_at', models.DateTimeField(blank=True, null=True)),
                        ('site_initial_email_sent', models.BooleanField(default=False)),
                        ('mapping_ready_email_sent', models.BooleanField(default=False)),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.user')),
                    ],
                ),
            ]
        )
    ]
