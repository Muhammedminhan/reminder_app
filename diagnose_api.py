#!/usr/bin/env python3
"""Quick API diagnostic: health endpoint, GraphQL schema load, create reminder mutation.
Run inside virtualenv: python diagnose_api.py
"""
import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reminder_app.settings')

django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from oauth2_provider.models import Application, AccessToken
from django.conf import settings
import json
from app.models import Company

client = Client()
report = {}

# 1. Health endpoint
try:
    resp = client.get('/health/')
    report['health_status_code'] = resp.status_code
    try:
        report['health_json'] = resp.json()
    except Exception:
        report['health_body'] = resp.content.decode()[:200]
except Exception as e:
    report['health_error'] = str(e)

# Ensure a company exists for non-superuser creation
company, company_created = Company.objects.get_or_create(name='DiagCo', defaults={'email': 'diag@co.test'})
report['company_created'] = company_created

# 2. Ensure a test user exists (assign company to satisfy validation)
User = get_user_model()
user = User.objects.filter(username='diaguser').first()
if not user:
    user = User(username='diaguser', email='diag@example.com')
    user.company = company
    # Make user superuser to simplify broader access (and bypass company enforcement if needed)
    user.is_superuser = True
    user.set_password('diagpass')
    user.save()
    report['user_created'] = True
else:
    report['user_created'] = False

# 3. OAuth2 application
app = Application.objects.filter(name='DiagApp', user=user).first()
if not app:
    app = Application.objects.create(
        name='DiagApp',
        user=user,
        client_type='confidential',
        authorization_grant_type='password'
    )
    report['oauth_app_created'] = True
else:
    report['oauth_app_created'] = False
report['oauth_client_id'] = app.client_id

# 4. Access token (create manually if none valid)
access_token = AccessToken.objects.filter(user=user, application=app).order_by('-expires').first()
if not access_token or access_token.is_expired():
    access_token = AccessToken.objects.create(
        user=user,
        token='diag-token-123',
        application=app,
        expires=timezone.now() + timedelta(hours=1),
        scope='read write'
    )
report['access_token'] = access_token.token

# Helper for GraphQL POST
GRAPHQL_PATH = '/graphql/'

def gql(query, variables=None, token=None):
    headers = {}
    if token:
        headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    payload = {'query': query}
    if variables:
        payload['variables'] = variables
    return client.post(GRAPHQL_PATH, data=json.dumps(payload), content_type='application/json', **headers)

# 5. me query (auth)
me_query = """
query { me { id username email } }
"""
me_resp = gql(me_query, token=access_token.token)
report['me_status_code'] = me_resp.status_code
try:
    report['me_json'] = me_resp.json()
except Exception:
    report['me_body'] = me_resp.content.decode()[:200]

# 6. createReminder mutation
mutation = """
mutation CreateReminder($title:String!,$senderEmail:String!,$receiverEmail:String!){
  createReminder(title:$title,senderEmail:$senderEmail,receiverEmail:$receiverEmail,description:"Diag reminder",intervalType:"daily",active:true,visibleToDepartment:true){
    ok
    reminder { id title senderEmail receiverEmail active visibleToDepartment createdBy { username } }
  }
}
"""
vars = {
    'title': 'Diagnostic Reminder',
    'senderEmail': 'sender@diag.com',
    'receiverEmail': 'receiver@diag.com'
}
rem_create_resp = gql(mutation, variables=vars, token=access_token.token)
report['create_status_code'] = rem_create_resp.status_code
try:
    report['create_json'] = rem_create_resp.json()
except Exception:
    report['create_body'] = rem_create_resp.content.decode()[:300]

# 7. list reminders (auth)
list_query = "query { reminders(active:true) { id title senderEmail receiverEmail active visibleToDepartment } }"
list_resp = gql(list_query, token=access_token.token)
report['list_status_code'] = list_resp.status_code
try:
    report['list_json'] = list_resp.json()
except Exception:
    report['list_body'] = list_resp.content.decode()[:300]

# 8. Unauthorized attempt
unauth_resp = gql(list_query, token=None)
report['unauth_status_code'] = unauth_resp.status_code
try:
    report['unauth_json'] = unauth_resp.json()
except Exception:
    report['unauth_body'] = unauth_resp.content.decode()[:300]

print("=== API DIAGNOSTIC REPORT ===")
for k, v in report.items():
    print(f"{k}: {v}")

# Simple success criteria summary
print("\n=== SUMMARY ===")
summary_lines = []
if report.get('health_status_code') == 200:
    line = "Health endpoint: OK"
else:
    line = "Health endpoint: FAIL"
print(line); summary_lines.append(line)

me_data = (report.get('me_json') or {}).get('data', {}).get('me')
if me_data:
    line = "Auth me query: OK"
else:
    line = f"Auth me query: FAIL {report.get('me_json')}"
print(line); summary_lines.append(line)

create_ok = (report.get('create_json') or {}).get('data', {}).get('createReminder', {}).get('ok')
if create_ok:
    line = "Create reminder mutation: OK"
else:
    line = f"Create reminder mutation: FAIL {report.get('create_json')}"
print(line); summary_lines.append(line)

list_data = (report.get('list_json') or {}).get('data', {}).get('reminders')
if isinstance(list_data, list):
    line = f"List reminders: OK (count={len(list_data)})"
else:
    line = f"List reminders: FAIL {report.get('list_json')}"
print(line); summary_lines.append(line)

unauth_data = (report.get('unauth_json') or {}).get('data')
unauth_errors = (report.get('unauth_json') or {}).get('errors')
if unauth_errors:
    line = "Unauthorized access: OK (error raised)"
elif unauth_data:
    line = "Unauthorized access: FAIL (data returned without auth)"
else:
    line = f"Unauthorized access: Indeterminate {report.get('unauth_json')}"
print(line); summary_lines.append(line)

# Persist to files for retrieval
import json as _json
with open('diag_report.json', 'w') as f:
    _json.dump(report, f, indent=2)
with open('diag_summary.txt', 'w') as f:
    for l in summary_lines:
        f.write(l + '\n')
