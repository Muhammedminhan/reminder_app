from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from app.utils import create_domain_mapping_gcp
from decouple import config
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up domain mapping for owner domain (notifyhub.fs.com)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            type=str,
            default='fs.com',
            help='Owner domain (default: fs.com)'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Owner email address'
        )

    def handle(self, *args, **options):
        owner_domain = options['domain']
        owner_email = options['email']
        
        if not owner_email:
            self.stdout.write(
                self.style.ERROR('Please provide --email argument')
            )
            return

        # Get or create owner user
        try:
            owner_user = User.objects.get(email=owner_email)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with email {owner_email} does not exist')
            )
            return

        brand_prefix = config('SUBDOMAIN_BRAND_PREFIX', default='notifyhub')
        owner_subdomain = f"{brand_prefix}.{owner_domain}"
        
        self.stdout.write(f'Setting up domain mapping for {owner_subdomain}...')
        
        # Create GCP domain mapping
        result = create_domain_mapping_gcp(owner_subdomain)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created domain mapping for {owner_subdomain}')
            )
            
            dns_records = result.get('dns_records', {})
            if dns_records:
                self.stdout.write('\nDNS Records to add:')
                for name, record in dns_records.items():
                    self.stdout.write(f'  {record.get("type")} {record.get("host")} -> {record.get("data")}')
            else:
                self.stdout.write(
                    self.style.WARNING('No DNS records returned. Check GCP console for records.')
                )
        else:
            self.stdout.write(
                self.style.ERROR(f'Failed to create domain mapping: {result["error"]}')
            )
