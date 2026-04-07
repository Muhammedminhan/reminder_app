from django import forms
from .models import Reminder

class ReminderForm(forms.ModelForm):
    class Meta:
        model = Reminder
        fields = ['title', 'description', 'sender_email', 'sender_name', 'receiver_email', 'interval_type', 'reminder_start_date',
                  'reminder_end_date', 'phone_no', 'send', 'completed', 'visible_to_department']  # removed 'company'
        widgets = {
            'interval_type': forms.Select(choices=Reminder.TASK_INTERVAL_CHOICES),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'reminder_start_date' in self.fields:
            self.fields['reminder_start_date'].label = 'Send Reminder At'
        if 'sender_name' in self.fields:
            self.fields['sender_name'].label = 'Sender Name'

    def save(self, commit=True):
        return super().save(commit=commit)
