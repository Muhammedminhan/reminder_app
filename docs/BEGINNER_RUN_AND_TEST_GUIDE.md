# NotifyHub API: Beginner Run & Test Guide

## 1. Setup
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

## 2. Create Superuser
```
SUPERUSER_NAME=admin SUPERUSER_PASSWORD=admin SUPERUSER_EMAIL=admin@example.com python manage.py createsuperuser_auto
```
(or use `python manage.py createsuperuser` interactively.)

## 3. Start Server
```
python manage.py runserver
```
Visit: http://localhost:8000/health/ (should return JSON status). Admin panel is at: http://localhost:8000/adrian-holovaty/

## 4. Create OAuth2 Application (Password Grant)
In admin panel → Applications → Add:
- Name: Local Test
- Client type: Confidential
- Authorization grant type: Password
Save. Copy Client ID + Client Secret.

## 5. Get Access Token
```
curl -X POST http://localhost:8000/o/token/ \
  -d "grant_type=password" \
  -d "username=admin" \
  -d "password=admin" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```
Response contains `access_token`.

## 6. Use GraphQL
Endpoint: http://localhost:8000/graphql/
Always send header: `Authorization: Bearer <token>`

### Query current user
```
curl http://localhost:8000/graphql/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { me { id username email company { id name } } }"}'
```

### Create a reminder
GraphQL arguments use camelCase (e.g. `senderEmail`, `visibleToDepartment`). In schema they were defined snake_case.
```
curl http://localhost:8000/graphql/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation($title:String!,$senderEmail:String!,$receiverEmail:String!){ createReminder(title:$title,senderEmail:$senderEmail,receiverEmail:$receiverEmail,description:\"Test\",intervalType:\"daily\",active:true,visibleToDepartment:true){ ok reminder { id title senderEmail receiverEmail intervalType active } } }",
    "variables": {
      "title": "My First Reminder",
      "senderEmail": "sender@example.com",
      "receiverEmail": "receiver@example.com"
    }
  }'
```

### List reminders
```
curl http://localhost:8000/graphql/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"query { reminders(active:true) { id title senderEmail receiverEmail active createdBy { username } } }"}'
```

## 7. Common Errors
- `You do not have permission`: Missing/invalid Authorization header.
- `Headers are invalid JSON`: You placed headers inside the JSON body; they must be real HTTP headers.
- `Unknown argument 'captcha_token'`: Use `captchaToken` (camelCase) if the mutation expects that form.
- Empty results for lists: Ensure your user belongs to a company and created data.

## 8. Run Provided Test Script
Edit `test_api_complete.py` and set CLIENT_ID / CLIENT_SECRET / TEST_USERNAME / TEST_PASSWORD, then:
```
python test_api_complete.py
```

## 9. Push Changes
On branch `feature/visible-to-department`:
```
git add .
git commit -m "Add beginner run/test guide and requirements fixes"
git push origin feature/visible-to-department
```

## 10. Next Improvements
- Add GraphQL login mutation (optional; currently OAuth2 handles auth).
- Add caching for frequent queries.
- Add more automated tests for role/permission mutations.

## Field Name Mapping Reminder
Schema args (snake_case) => GraphQL (camelCase):
- `sender_email` => `senderEmail`
- `receiver_email` => `receiverEmail`
- `reminder_start_date` => `reminderStartDate`
- `reminder_end_date` => `reminderEndDate`
- `visible_to_department` => `visibleToDepartment`

## Troubleshooting Server Not Responding
- Confirm port 8000 is free.
- Re-run: `python manage.py runserver 0.0.0.0:8000`
- Check logs for import errors.
- Ensure virtualenv active: `source .venv/bin/activate`

## Permission System Quick Test
After creating roles/permissions:
1. Create permission via mutation.
2. Create role with that permission.
3. Assign role to user.
4. Query `myPermissions`.

You're good to start experimenting. Make small changes and run tests frequently.

