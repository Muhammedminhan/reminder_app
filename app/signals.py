# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import SendGridDomainAuth
# from .tasks import check_domain_verification
#
# @receiver(post_save, sender=SendGridDomainAuth)
# def trigger_sendgrid_verification(sender, instance, created, **kwargs):
#     if instance.domain_id:
#         try:
#             check_domain_verification.apply_async((str(instance.domain_id),), countdown=3600)
#         except Exception as e:
#             import logging
#             logging.warning(f"[SendGrid Verification] Could not schedule for {instance.domain}: {e}")
