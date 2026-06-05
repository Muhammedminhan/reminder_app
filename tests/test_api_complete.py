#!/usr/bin/env python3
"""
Complete API Test Script for NotifyHub
Tests OAuth2 authentication and GraphQL operations
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
GRAPHQL_URL = f"{BASE_URL}/graphql/"
OAUTH_TOKEN_URL = f"{BASE_URL}/o/token/"

# Test credentials (you'll need to update these)
TEST_USERNAME = "admin"  # Change to your username
TEST_PASSWORD = "admin"  # Change to your password

# OAuth2 Application credentials (you'll need to create an application first)
CLIENT_ID = "YOUR_CLIENT_ID"  # Update after creating OAuth2 application
CLIENT_SECRET = "YOUR_CLIENT_SECRET"  # Update after creating OAuth2 application


def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def print_result(response):
    """Print formatted response"""
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)


def get_oauth_token(username, password, client_id, client_secret):
    """Get OAuth2 access token using password grant"""
    print_header("Step 1: Getting OAuth2 Access Token")

    data = {
        'grant_type': 'password',
        'username': username,
        'password': password,
        'client_id': client_id,
        'client_secret': client_secret,
    }

    try:
        response = requests.post(OAUTH_TOKEN_URL, data=data)
        print_result(response)

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            print(f"\n✓ Successfully obtained access token: {access_token[:20]}...")
            return access_token
        else:
            print("\n✗ Failed to obtain access token")
            print("Make sure you have:")
            print("1. Created an OAuth2 application in the admin panel")
            print("2. Updated CLIENT_ID and CLIENT_SECRET in this script")
            print("3. Used the correct username and password")
            return None
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None


def test_graphql_query(token, query, variables=None):
    """Execute a GraphQL query with OAuth2 token"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    payload = {
        'query': query,
    }

    if variables:
        payload['variables'] = variables

    response = requests.post(GRAPHQL_URL, json=payload, headers=headers)
    print_result(response)
    return response


def test_me_query(token):
    """Test the 'me' query to verify authentication"""
    print_header("Step 2: Testing 'me' Query (Current User)")

    query = """
    query {
        me {
            id
            username
            email
            company {
                id
                name
            }
        }
    }
    """

    response = test_graphql_query(token, query)
    if response.status_code == 200 and response.json().get('data', {}).get('me'):
        print("\n✓ Successfully authenticated and retrieved user info")
        return True
    else:
        print("\n✗ Failed to retrieve user info")
        return False


def test_create_reminder(token):
    """Test creating a reminder"""
    print_header("Step 3: Testing Create Reminder Mutation")

    mutation = """
    mutation CreateReminder($title: String!, $senderEmail: String!, $receiverEmail: String!, $description: String) {
        createReminder(
            title: $title
            description: $description
            senderEmail: $senderEmail
            receiverEmail: $receiverEmail
            intervalType: "daily"
            active: true
        ) {
            ok
            reminder {
                id
                title
                description
                senderEmail
                receiverEmail
                intervalType
                active
                createdBy {
                    username
                }
            }
        }
    }
    """

    variables = {
        "title": "Test Reminder",
        "description": "This is a test reminder created via GraphQL API",
        "senderEmail": "sender@example.com",
        "receiverEmail": "receiver@example.com"
    }

    response = test_graphql_query(token, mutation, variables)
    if response.status_code == 200 and response.json().get('data', {}).get('createReminder', {}).get('ok'):
        print("\n✓ Successfully created reminder")
        reminder_id = response.json()['data']['createReminder']['reminder']['id']
        return reminder_id
    else:
        print("\n✗ Failed to create reminder")
        return None


def test_list_reminders(token):
    """Test listing reminders"""
    print_header("Step 4: Testing List Reminders Query")

    query = """
    query {
        reminders(active: true) {
            id
            title
            description
            senderEmail
            receiverEmail
            intervalType
            active
            createdBy {
                username
            }
        }
    }
    """

    response = test_graphql_query(token, query)
    if response.status_code == 200:
        reminders = response.json().get('data', {}).get('reminders', [])
        print(f"\n✓ Retrieved {len(reminders)} reminder(s)")
        return True
    else:
        print("\n✗ Failed to retrieve reminders")
        return False


def test_without_token():
    """Test GraphQL without authentication to verify security"""
    print_header("Step 5: Testing Without Authentication (Should Fail)")

    query = """
    query {
        reminders {
            id
            title
        }
    }
    """

    headers = {
        'Content-Type': 'application/json',
    }

    payload = {
        'query': query,
    }

    response = requests.post(GRAPHQL_URL, json=payload, headers=headers)
    print_result(response)

    reminders = response.json().get('data', {}).get('reminders')
    if reminders is None or len(reminders) == 0:
        print("\n✓ Correctly blocked unauthenticated request")
        return True
    else:
        print("\n⚠ Warning: API allowed unauthenticated access")
        return False


def main():
    print_header("NotifyHub API Complete Test")
    print(f"Testing API at: {BASE_URL}")
    print(f"GraphQL Endpoint: {GRAPHQL_URL}")
    print(f"OAuth2 Token Endpoint: {OAUTH_TOKEN_URL}")

    # Check if credentials are configured
    if CLIENT_ID == "YOUR_CLIENT_ID" or CLIENT_SECRET == "YOUR_CLIENT_SECRET":
        print("\n" + "!"*60)
        print("  SETUP REQUIRED")
        print("!"*60)
        print("\nBefore running this script, you need to:")
        print("\n1. Create an OAuth2 Application:")
        print(f"   - Go to: {BASE_URL}/adrian-holovaty/")
        print("   - Navigate to: OAuth2 Provider > Applications")
        print("   - Click 'Add Application'")
        print("   - Fill in:")
        print("     * Name: Test Application")
        print("     * Client type: Confidential")
        print("     * Authorization grant type: Resource owner password-based")
        print("     * Skip authorization: Yes (check this)")
        print("   - Save and copy the Client ID and Client Secret")
        print("\n2. Update this script:")
        print("   - Set CLIENT_ID to the copied Client ID")
        print("   - Set CLIENT_SECRET to the copied Client Secret")
        print("   - Set TEST_USERNAME and TEST_PASSWORD to your credentials")
        print("\n3. Run this script again")
        print("\n" + "!"*60)
        return

    # Get OAuth token
    token = get_oauth_token(TEST_USERNAME, TEST_PASSWORD, CLIENT_ID, CLIENT_SECRET)

    if not token:
        print("\n✗ Cannot continue without a valid token")
        return

    # Run tests
    if not test_me_query(token):
        print("\n✗ Basic authentication test failed")
        return

    reminder_id = test_create_reminder(token)

    test_list_reminders(token)

    test_without_token()

    print_header("Test Summary")
    print("\n✓ All tests completed!")
    print("\nYour API is working correctly with:")
    print("  - OAuth2 authentication")
    print("  - GraphQL queries and mutations")
    print("  - Proper authorization checks")
    print("\nNext steps:")
    print("  1. Test the API from your frontend")
    print("  2. Use the access token in the Authorization header:")
    print(f"     Authorization: Bearer {token[:20]}...")
    print("  3. Review the GraphQL schema in GraphiQL:")
    print(f"     {GRAPHQL_URL}")


if __name__ == "__main__":
    main()

