from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from app.utils import create_domain_mapping_gcp, send_dns_instructions_email
from app.models import SendGridDomainAuth
from decouple import config
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up complete multi-tenant domain system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--owner-domain',
            type=str,
            default='fs.com',
            help='Owner domain (default: fs.com)'
        )
        parser.add_argument(
            '--owner-email',
            type=str,
            help='Owner email address'
        )
        parser.add_argument(
            '--test-domain',
            type=str,
            help='Test domain to set up (e.g., abc.com)'
        )
        parser.add_argument(
            '--test-email',
            type=str,
            help='Test user email address'
        )

    def handle(self, *args, **options):
        owner_domain = options['owner_domain']
        owner_email = options['owner_email']
        test_domain = options['test_domain']
        test_email = options['test_email']
        
        brand_prefix = config('SUBDOMAIN_BRAND_PREFIX', default='notifyhub')
        
        # Set up owner domain
        if owner_email:
            self.setup_owner_domain(owner_domain, owner_email, brand_prefix)
        
        # Set up test domain
        if test_domain and test_email:
            self.setup_test_domain(test_domain, test_email, brand_prefix)
        
        self.stdout.write(
            self.style.SUCCESS('\nMulti-tenant setup complete!')
        )
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Add the DNS records shown above to your DNS provider')
        self.stdout.write('2. Wait for DNS propagation (usually 5-15 minutes)')
        self.stdout.write('3. Test access via the subdomain URLs')
        self.stdout.write('4. Set up Cloud Scheduler jobs for automated verification')

    def setup_owner_domain(self, owner_domain, owner_email, brand_prefix):
        self.stdout.write(f'\n=== Setting up owner domain: {owner_domain} ===')
        
        # Get or create owner user
        try:
            owner_user = User.objects.get(email=owner_email)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with email {owner_email} does not exist')
            )
            return

        owner_subdomain = f"{brand_prefix}.{owner_domain}"
        
        self.stdout.write(f'Creating domain mapping for {owner_subdomain}...')
        
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
                
                # Send email with DNS instructions
                try:
                    send_dns_instructions_email(
                        owner_email, 
                        owner_subdomain, 
                        {},  # No SendGrid records for owner domain
                        dns_records
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'DNS instructions email sent to {owner_email}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Failed to send email: {e}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING('No DNS records returned. Check GCP console for records.')
                )
        else:
            self.stdout.write(
                self.style.ERROR(f'Failed to create domain mapping: {result["error"]}')
            )

    def setup_test_domain(self, test_domain, test_email, brand_prefix):
        self.stdout.write(f'\n=== Setting up test domain: {test_domain} ===')
        
        # Get or create test user
        try:
            test_user = User.objects.get(email=test_email)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with email {test_email} does not exist')
            )
            return

        # Check if SendGridDomainAuth already exists
        try:
            domain_auth = SendGridDomainAuth.objects.get(domain=test_domain, user=test_user)
            self.stdout.write(
                self.style.WARNING(f'SendGridDomainAuth already exists for {test_domain}')
            )
        except SendGridDomainAuth.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Please create SendGridDomainAuth for {test_domain} first via admin panel')
            )
            return

        test_subdomain = f"{brand_prefix}.{test_domain}"
        
        self.stdout.write(f'Creating domain mapping for {test_subdomain}...')
        
        # Create GCP domain mapping
        result = create_domain_mapping_gcp(test_subdomain)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created domain mapping for {test_subdomain}')
            )
            
            dns_records = result.get('dns_records', {})
            if dns_records:
                self.stdout.write('\nDNS Records to add:')
                for name, record in dns_records.items():
                    self.stdout.write(f'  {record.get("type")} {record.get("host")} -> {record.get("data")}')
                
                # Update the SendGridDomainAuth with GCP records
                try:
                    existing_records = domain_auth.dns_records or {}
                    combined_records = {**existing_records, **dns_records}
                    domain_auth.dns_records = combined_records
                    domain_auth.save()
                    self.stdout.write(
                        self.style.SUCCESS('Updated SendGridDomainAuth with GCP DNS records')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Failed to update SendGridDomainAuth: {e}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING('No DNS records returned. Check GCP console for records.')
                )
        else:
            self.stdout.write(
                self.style.ERROR(f'Failed to create domain mapping: {result["error"]}')
            )
