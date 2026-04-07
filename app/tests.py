from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import Group
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from .models import Company, User, SendGridDomainAuth, Reminder, Department
from .utils import process_reminder_tasks
from django.conf import settings
from app.tasks import check_and_notify_admin_for_email_threshold
from django.test import override_settings

class CompanyAdminDomainVerificationAddTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='Acme')
        self.company_admin_group, _ = Group.objects.get_or_create(name='Company Admin')
        self.superuser = User.objects.create_superuser(username='root', email='root@example.com', password='rootpass')
        self.superuser.company = self.company
        self.superuser.save()
        self.admin_user = User.objects.create_user(username='coadmin', email='coadmin@example.com', password='pass123', company=self.company, is_staff=True)
        self.admin_user.groups.add(self.company_admin_group)

    def _login_admin(self):
        self.client.logout()
        self.assertTrue(self.client.login(username='coadmin', password='pass123'))

    def _assert_redirect_blocked(self, add_url, expected_changelist):
        resp = self.client.get(add_url)
        self.assertEqual(resp.status_code, 302, f"Expected redirect when blocked for {add_url}")
        self.assertIn(expected_changelist, resp['Location'])

    def _assert_allowed(self, add_url):
        resp = self.client.get(add_url)
        self.assertEqual(resp.status_code, 200, f"Expected access allowed for {add_url}")
        self.assertContains(resp, '<form', status_code=200)

    def test_block_add_views_until_verified(self):
        self._login_admin()
        self._assert_redirect_blocked(reverse('admin:app_reminder_add'), reverse('admin:app_reminder_changelist'))
        self._assert_redirect_blocked(reverse('admin:app_department_add'), reverse('admin:app_department_changelist'))
        self._assert_redirect_blocked(reverse('admin:app_user_add'), reverse('admin:app_user_changelist'))

    def test_allow_after_verified_domain_owned_by_superuser(self):
        SendGridDomainAuth.objects.create(user=self.superuser, domain='notifyhub.example.com', is_verified=True)
        self._login_admin()
        self._assert_allowed(reverse('admin:app_reminder_add'))
        self._assert_allowed(reverse('admin:app_department_add'))
        self._assert_allowed(reverse('admin:app_user_add'))

    def test_allow_superuser_always(self):
        self.client.logout()
        self.assertTrue(self.client.login(username='root', password='rootpass'))
        resp = self.client.get(reverse('admin:app_reminder_add'))
        self.assertEqual(resp.status_code, 200)

class ReminderActiveFlagTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='AcmeCo')
        self.user = User.objects.create_user(username='ruser', password='pass', company=self.company, is_staff=True)

    @patch('app.utils._send_reminder_email', return_value=True)
    def test_active_reminder_processed_and_cloned(self, mock_send):
        r = Reminder.objects.create(
            title='Daily Task',
            receiver_email='a@example.com',
            interval_type='daily',
            reminder_start_date=timezone.now() - timedelta(minutes=1),
            company=self.company,
            created_by=self.user,
            active=True
        )
        stats = process_reminder_tasks()
        r.refresh_from_db()
        self.assertTrue(r.send)
        self.assertEqual(stats['sent'], 1)
        cloned = Reminder.objects.exclude(id=r.id).first()
        self.assertIsNotNone(cloned)
        self.assertEqual(cloned.created_by, self.user)
        self.assertTrue(cloned.active)

    @patch('app.utils._send_reminder_email', return_value=True)
    def test_inactive_reminder_not_processed(self, mock_send):
        r = Reminder.objects.create(
            title='Paused Task',
            receiver_email='b@example.com',
            interval_type='daily',
            reminder_start_date=timezone.now() - timedelta(minutes=1),
            company=self.company,
            created_by=self.user,
            active=False
        )
        stats = process_reminder_tasks()
        r.refresh_from_db()
        self.assertFalse(r.send)
        self.assertEqual(stats['sent'], 0)
        self.assertEqual(Reminder.objects.count(), 1)

class ActionSendNowOverrideTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='SendNowCo')
        self.superuser = User.objects.create_superuser(username='admin', email='admin@example.com', password='adminpass', company=self.company)
        self.client.login(username='admin', password='adminpass')

    @patch('app.utils._send_reminder_email', return_value=True)
    def test_send_now_active_unsent_creates_clone_once(self, mock_send):
        r = Reminder.objects.create(
            title='Override Daily',
            receiver_email='x@example.com',
            interval_type='daily',
            reminder_start_date=timezone.now() - timedelta(minutes=1),
            company=self.company,
            created_by=self.superuser,
            active=True,
            send=False
        )
        changelist = reverse('admin:app_reminder_changelist')
        post_data = {
            'action': 'send_now_override',
            '_selected_action': [str(r.id)],
        }
        resp = self.client.post(changelist, post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        r.refresh_from_db()
        self.assertTrue(r.send)
        # One clone created
        self.assertEqual(Reminder.objects.count(), 2)
        # Invoke again: should NOT create additional clone
        resp2 = self.client.post(changelist, post_data, follow=True)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(Reminder.objects.count(), 2, 'Second override should not schedule another clone for already sent reminder')

    @patch('app.utils._send_reminder_email', return_value=True)
    def test_send_now_inactive_skipped(self, mock_send):
        r = Reminder.objects.create(
            title='Inactive Override',
            receiver_email='y@example.com',
            interval_type='daily',
            reminder_start_date=timezone.now() - timedelta(minutes=1),
            company=self.company,
            created_by=self.superuser,
            active=False,
            send=False
        )
        changelist = reverse('admin:app_reminder_changelist')
        post_data = {'action': 'send_now_override', '_selected_action': [str(r.id)]}
        self.client.post(changelist, post_data, follow=True)
        r.refresh_from_db()
        self.assertFalse(r.send)
        self.assertEqual(Reminder.objects.count(), 1)

class CompanyAdminUserCreationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='CoOne')
        self.other_company = Company.objects.create(name='CoTwo')
        self.company_admin_group, _ = Group.objects.get_or_create(name='Company Admin')
        # Department for company admin and for assignment
        self.dept = Department.objects.create(name='HR', company=self.company)
        # Superuser (used for verified domain association)
        self.superuser = User.objects.create_superuser(username='rootz', email='rootz@example.com', password='rootpass', company=self.company)
        self.admin_user = User.objects.create_user(username='admin1', email='admin1@example.com', password='pass123', company=self.company, is_staff=True)
        self.admin_user.groups.add(self.company_admin_group)
        # Create verified domain linked to superuser (company-wide verification)
        SendGridDomainAuth.objects.create(user=self.superuser, domain='notifyhub.verified.example.com', is_verified=True)
        self.client.login(username='admin1', password='pass123')

    def test_add_user_form_hides_permission_fields(self):
        resp = self.client.get(reverse('admin:app_user_add'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # Visible
        self.assertIn('id_is_active', content)
        self.assertIn('id_department', content)
        # Hidden / not present
        self.assertNotIn('id_is_superuser', content)
        self.assertNotIn('id_is_staff', content)
        self.assertNotIn('id_user_permissions', content)
        self.assertIn('id_groups', content)

    def test_add_user_requires_department(self):
        add_url = reverse('admin:app_user_add')
        post_data = {
            'username': 'newuser1',
            'email': 'nu1@example.com',
            'password1': 'Str0ngPass!!',
            'password2': 'Str0ngPass!!',
            'is_active': 'on',
            # department omitted intentionally
        }
        resp = self.client.post(add_url, post_data)
        # Form re-render with error
        self.assertEqual(resp.status_code, 200)
        self.assertIn('This field is required', resp.content.decode())
        self.assertFalse(User.objects.filter(username='newuser1').exists())

    def test_new_user_is_staff_true_and_company_forced(self):
        add_url = reverse('admin:app_user_add')
        post_data = {
            'username': 'newuser2',
            'email': 'nu2@example.com',
            'password1': 'Str0ngPass!!',
            'password2': 'Str0ngPass!!',
            'department': str(self.dept.id),
            'is_active': 'on',
            'company': str(self.company.id),
        }
        resp = self.client.post(add_url, post_data, follow=True)
        if not User.objects.filter(username='newuser2').exists():
            try:
                adminform = resp.context.get('adminform') if hasattr(resp, 'context') and resp.context else None
                form = adminform.form if adminform else None
                if form:
                    print('DEBUG FORM ERRORS:', form.errors.as_json())
            except Exception:
                pass
        self.assertEqual(resp.status_code, 200)
        u = User.objects.get(username='newuser2')
        self.assertTrue(u.is_staff, 'New user should have is_staff True by default for company admin creation')
        self.assertFalse(u.is_superuser)
        self.assertEqual(u.company, self.company)
        self.assertEqual(u.department, self.dept)

    def test_superuser_still_can_create_without_department(self):
        superuser = User.objects.create_superuser(username='rootx', email='rootx@example.com', password='rootpass', company=self.company)
        self.client.logout()
        self.client.login(username='rootx', password='rootpass')
        add_url = reverse('admin:app_user_add')
        post_data = {
            'username': 'nouserdept',
            'email': 'nouserdept@example.com',
            'password1': 'Str0ngPass!!',
            'password2': 'Str0ngPass!!',
            'is_active': 'on',
            'company': str(self.company.id),  # Provide company so clean() passes for non-superuser user (new user defaults to non-superuser)
        }
        resp = self.client.post(add_url, post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(User.objects.filter(username='nouserdept').exists())

    def test_company_field_has_no_empty_option(self):
        resp = self.client.get(reverse('admin:app_user_add'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Ensure no empty <option value=""> appears for company select
        self.assertNotIn('<option value="">', html)
        # Ensure exactly one company option present (the admin's company)
        self.assertIn(f'>{self.company.name}</option>', html)

class CompanyAdminUserListExclusionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='ListCo')
        self.company_admin_group, _ = Group.objects.get_or_create(name='Company Admin')
        # Superuser with same company for verification & visibility check
        self.superuser = User.objects.create_superuser(username='rootlist', email='rootlist@example.com', password='rootpass', company=self.company)
        # Company admin
        self.admin_user = User.objects.create_user(username='adminlist', email='adminlist@example.com', password='pass123', company=self.company, is_staff=True)
        self.admin_user.groups.add(self.company_admin_group)
        # Another regular user in same company
        self.other_user = User.objects.create_user(username='otheruser', email='other@example.com', password='pass123', company=self.company, is_staff=True)
        # Verified domain (so add page logic elsewhere wouldn't block module access if reused)
        SendGridDomainAuth.objects.create(user=self.superuser, domain='notifyhub.list.example.com', is_verified=True)

    def test_company_admin_list_excludes_self(self):
        self.assertTrue(self.client.login(username='adminlist', password='pass123'))
        resp = self.client.get(reverse('admin:app_user_changelist'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Extract result list table segment only
        start = html.find('<table id="result_list"')
        end = html.find('</table>', start)
        table_html = html[start:end]
        # Username appears in header (Welcome, adminlist) so check only table rows
        self.assertNotIn('adminlist', table_html, 'Company admin own record should not be listed in result table')
        self.assertIn('otheruser', table_html)
        # Superuser should still be visible
        self.assertIn('rootlist', table_html)

    def test_superuser_sees_all_including_company_admin(self):
        self.assertTrue(self.client.login(username='rootlist', password='rootpass'))
        resp = self.client.get(reverse('admin:app_user_changelist'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('adminlist', html)
        self.assertIn('otheruser', html)

class RecurringIntervalSchedulingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='CycleCo')
        self.user = User.objects.create_user(username='cycleuser', password='pass', company=self.company, is_staff=True)

    @patch('app.utils._send_reminder_email', return_value=True)
    def test_monthly_clone_date(self, mock_send):
        base_start = timezone.make_aware(datetime(2025, 1, 31, 10, 0, 0))  # end-of-month edge
        r = Reminder.objects.create(
            title='Monthly Task',
            receiver_email='m@example.com',
            interval_type='monthly',
            reminder_start_date=base_start,
            company=self.company,
            created_by=self.user,
            active=True
        )
        stats = process_reminder_tasks()
        r.refresh_from_db()
        self.assertTrue(r.send)
        self.assertEqual(stats['sent'], 1)
        self.assertEqual(Reminder.objects.count(), 2)
        clone = Reminder.objects.exclude(id=r.id).get()
        expected = base_start + relativedelta(months=+1)
        self.assertEqual(clone.reminder_start_date, expected, f"Expected clone start {expected} got {clone.reminder_start_date}")
        self.assertEqual(clone.interval_type, 'monthly')
        self.assertFalse(clone.send)

    @patch('app.utils._send_reminder_email', return_value=True)
    def test_six_months_clone_date(self, mock_send):
        base_start = timezone.make_aware(datetime(2025, 2, 15, 9, 30, 0))
        r = Reminder.objects.create(
            title='Semi-Annual Task',
            receiver_email='s@example.com',
            interval_type='6 months',
            reminder_start_date=base_start,
            company=self.company,
            created_by=self.user,
            active=True
        )
        process_reminder_tasks()
        self.assertEqual(Reminder.objects.count(), 2)
        clone = Reminder.objects.exclude(id=r.id).get()
        expected = base_start + relativedelta(months=+6)
        self.assertEqual(clone.reminder_start_date, expected)
        self.assertEqual(clone.interval_type, '6 months')

    @patch('app.utils._send_reminder_email', return_value=True)
    def test_yearly_clone_date(self, mock_send):
        base_start = timezone.make_aware(datetime(2024, 2, 29, 8, 0, 0))  # leap day to ensure proper rollover
        r = Reminder.objects.create(
            title='Annual Task',
            receiver_email='y@example.com',
            interval_type='yearly',
            reminder_start_date=base_start,
            company=self.company,
            created_by=self.user,
            active=True
        )
        process_reminder_tasks()
        self.assertEqual(Reminder.objects.count(), 2)
        clone = Reminder.objects.exclude(id=r.id).get()
        expected = base_start + relativedelta(years=+1)
        self.assertEqual(clone.reminder_start_date, expected, 'Yearly clone should handle leap day via relativedelta')
        self.assertEqual(clone.interval_type, 'yearly')

class ReminderAdminNotificationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='NotifyHub')
        self.user = User.objects.create_user(username='adminuser', password='pass', company=self.company, is_staff=True)
        self.today = datetime.now().date()
        # Create reminders for today and next 7 days, each with 80 recipients
        for offset in range(8):
            date = self.today + timedelta(days=offset)
            Reminder.objects.create(
                title=f'Reminder {offset}',
                receiver_email=','.join([f'user{i}@example.com' for i in range(80)]),
                interval_type='one_time',
                reminder_start_date=datetime.combine(date, datetime.min.time()),
                company=self.company,
                created_by=self.user,
                active=True
            )

    @override_settings(ADMIN_EMAIL='admin@notifyhub.com', DEFAULT_FROM_EMAIL='noreply@notifyhub.com')
    @patch('app.tasks.send_mail')
    def test_admin_alert_sent_for_high_volume_days(self, mock_send_mail):
        from app.tasks import check_and_notify_admin_for_email_threshold
        check_and_notify_admin_for_email_threshold()
        self.assertTrue(mock_send_mail.called)
        args, kwargs = mock_send_mail.call_args
        message = args[1]
        for offset in range(8):
            date = self.today + timedelta(days=offset)
            self.assertIn(str(date), message)
