
from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.utils import timezone
from app.models import Reminder, User, Company

class SlackNotificationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.user1 = User.objects.create(username="u1", email="u1@example.com", company=self.company, slack_user_id="U1")
        self.user2 = User.objects.create(username="u2", email="u2@example.com", company=self.company, slack_user_id="U2")
        self.reminder = Reminder.objects.create(
            title="Test Reminder",
            created_by=self.user1,
            company=self.company,
            reminder_start_date=timezone.now(),
            send=True,
            completed=False
        )

    @patch('app.slack._slack_api_post')
    def test_notify_creator_only(self, mock_post):
        mock_post.return_value = {'ok': True, 'channel': {'id': 'D1'}}
        
        from app.utils import _notify_slack_pending_reminder
        _notify_slack_pending_reminder(self.reminder)
        
        # Should verify look up of creator -> send DM
        # calls: conversations.open (for U1), chat.postMessage
        self.assertTrue(mock_post.called)
        # Verify U1 was targeted
        call_args_list = mock_post.call_args_list
        # identifying open call for U1
        open_calls = [c for c in call_args_list if c[0][0] == 'conversations.open' and c[0][1].get('users') == 'U1']
        self.assertEqual(len(open_calls), 1)

    @patch('app.slack._slack_api_post')
    def test_notify_multiple_users_and_channels(self, mock_post):
        mock_post.return_value = {'ok': True, 'channel': {'id': 'D_mock'}}

        self.reminder.slack_users.add(self.user2)
        self.reminder.slack_channels = "#proj-alerts, #general"
        self.reminder.save()

        from app.utils import _notify_slack_pending_reminder
        _notify_slack_pending_reminder(self.reminder)

        # Expected:
        # 1. Creator (U1) notification
        # 2. User2 (U2) notification
        # 3. Channel #proj-alerts
        # 4. Channel #general

        # Check for U1 open
        u1_open = [c for c in mock_post.call_args_list if c[0][0] == 'conversations.open' and c[0][1].get('users') == 'U1']
        self.assertTrue(u1_open, "Should notify creator U1")
        
        # Check for U2 open
        u2_open = [c for c in mock_post.call_args_list if c[0][0] == 'conversations.open' and c[0][1].get('users') == 'U2']
        self.assertTrue(u2_open, "Should notify extra user U2")

        # Check for channels
        # chat.postMessage with channel='#proj-alerts'
        chan1 = [c for c in mock_post.call_args_list if c[0][0] == 'chat.postMessage' and c[0][1].get('channel') == '#proj-alerts']
        self.assertTrue(chan1, "Should notify #proj-alerts")

        chan2 = [c for c in mock_post.call_args_list if c[0][0] == 'chat.postMessage' and c[0][1].get('channel') == '#general']
        self.assertTrue(chan2, "Should notify #general")

