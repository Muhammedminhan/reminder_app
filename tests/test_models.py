from django.test import TestCase
from app.models import Reminder, Company
from django.contrib.auth import get_user_model

User = get_user_model()

class ReminderModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.user = User.objects.create_user(
            username="testuser", password="pass", company=self.company
        )

    def test_reminder_str(self):
        r = Reminder(title="Pay invoice", receiver_email="a@b.com")
        self.assertEqual(str(r), "Pay invoice")

    def test_is_active_no_end_date(self):
        r = Reminder(title="No end", receiver_email="a@b.com")
        self.assertTrue(r.is_active())
